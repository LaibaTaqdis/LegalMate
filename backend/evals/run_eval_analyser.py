"""Measure the REAL analyser (DeepSeek) on the gold questions, then evaluate retrieval from the queries it wrote.

    python -m evals.run_eval_analyser --plan          # how many live calls it would take. NO calls.
    python -m evals.run_eval_analyser --cap 120       # run (cached afterwards: re-running and re-analysing is free)

One analyser call per question (about 114). Everything after that (retrieval variants, metrics) is free and recomputed
from the cached analyser outputs, so different retrieval designs can be compared without spending again.
"""
from __future__ import annotations

import argparse
import collections
import json
import time
from dataclasses import replace

from chat.engine import ChatEngine, norm_jurisdiction
from chat.llm import DeepSeek
from chat.settings import get_settings
from ingest.config import REPORTS_DIR
from retrieval.kb import KnowledgeBase

from .gold import GOLD
from .labels import Labeler, load_chunks
from .run_eval import fmt, metrics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--cap", type=int, default=120)
    args = ap.parse_args()
    s = get_settings()
    if args.plan:
        cached = sum(1 for _ in s.cache_dir.glob("*.json")) if s.cache_dir.exists() else 0
        print(f"{len(GOLD)} questions -> up to {len(GOLD)} analyser calls (~$0.0006 each = ~${len(GOLD) * 0.0006:.3f}); {cached} responses already cached on disk")
        return
    llm = DeepSeek(replace(s, max_calls_per_run=args.cap))
    kb = KnowledgeBase(s.database_url)
    eng = ChatEngine(kb, llm)
    chunks = load_chunks()
    lab = Labeler(chunks)
    hash_of = {c["chunk_id"]: c["chunk_hash"] for c in chunks}

    rows = []
    t0 = time.time()
    for g in GOLD:
        profile = {"province": g["jur"]} if g["jur"] in ("Punjab", "ICT") else None
        a = eng.analyse(g["question"], [], profile, "en", False)
        rows.append((g, a))
    print(f"analysed {len(rows)} questions in {time.time() - t0:.0f}s | {llm.summary()}")
    (REPORTS_DIR / "analyser_gold.json").write_text(json.dumps(
        [{"id": g["id"], "question": g["question"], "analysis": {k: a[k] for k in ("intent", "language", "jurisdiction", "emergency", "needs_clarification", "search_queries", "tag", "title")}} for g, a in rows],
        ensure_ascii=False, indent=1), encoding="utf-8")

    pos = [(g, a) for g, a in rows if not g["neg"]]
    neg = [(g, a) for g, a in rows if g["neg"]]
    rel_hashes = {g["id"]: {chunks[i]["chunk_hash"] for i in lab.relevant(g)} for g, _ in pos}
    out = ["# Analyser + retrieval evaluation (real DeepSeek analyser on the gold questions)", "",
           f"{len(pos)} legal questions, {len(neg)} out-of-scope. {llm.summary()}", ""]

    # behaviour of the analyser itself
    intents = collections.Counter(a["intent"] for _, a in pos)
    clar = [g["id"] for g, a in pos if a["needs_clarification"]]
    oos = sum(1 for _, a in neg if a["intent"] in ("out_of_scope", "unclear", "greeting"))
    out += ["## Analyser behaviour", "", f"- intents on real legal questions: {dict(intents)}",
            f"- asked a clarifying question on {len(clar)} of {len(pos)} real questions ({100 * len(clar) / len(pos):.0f}%): {clar}",
            f"- out-of-scope questions correctly declined: {oos} of {len(neg)}"]
    for g, a in neg:
        out.append(f"  - {g['id']} `{g['question'][:60]}` -> {a['intent']}")
    wrong_jur = [(g["id"], g["jur"], a["jurisdiction"]) for g, a in pos if g["jur"] in ("Punjab", "ICT") and norm_jurisdiction(a["jurisdiction"]) not in (g["jur"], None)]
    out += [f"- jurisdiction contradicting the profile: {wrong_jur or 'none'}", ""]

    # retrieval variants, all computed from the SAME cached analyser output (free)
    def hit(g, qs, n_pass, per_section):
        e2 = ChatEngine(kb, llm, n_passages=n_pass, per_section_cap=per_section)
        jur = norm_jurisdiction(g["jur"]) if g["jur"] in ("Punjab", "ICT") else None
        ps = e2.retrieve(qs, jur)
        return next((r for r, p in enumerate(ps, 1) if p["chunk_hash"] in rel_hashes[g["id"]]), None)

    variants = {
        "my hand-written query_en (reference)": lambda g, a: [g["query_en"]],
        "analyser: plain query only": lambda g, a: a["search_queries"][:1],
        "analyser: statutory query only": lambda g, a: a["search_queries"][1:2],
        "analyser: section-heading query only": lambda g, a: a["search_queries"][2:3],
        "analyser: all queries merged (production)": lambda g, a: a["search_queries"],
    }
    out += ["## Retrieval from the analyser's queries (the passages the answer step actually sees)", "",
            "| queries used | hit@1 | hit@3 | hit@5 | hit@8 | hit@20 | MRR |", "|---|---|---|---|---|---|---|"]
    best_rows = {}
    for name, fn in variants.items():
        res = []
        for g, a in pos:
            res.append({"id": g["id"], "rank": hit(g, fn(g, a), 20, 2), "cat": g["cat"]})
        m = {f"hit@{k}": sum(1 for r in res if r["rank"] and r["rank"] <= k) / len(res) for k in (1, 3, 5, 8, 20)}
        m["mrr"] = sum(1 / r["rank"] for r in res if r["rank"]) / len(res)
        out.append(f"| {name} | " + " | ".join(f"{m[f'hit@{k}'] * 100:.1f}" for k in (1, 3, 5, 8, 20)) + f" | {m['mrr']:.3f} |")
        print(f"{name:46} " + " | ".join(f"{m[f'hit@{k}'] * 100:5.1f}" for k in (1, 3, 5, 8, 20)) + f" | {m['mrr']:.3f}", flush=True)
        best_rows[name] = res
    prod = best_rows["analyser: all queries merged (production)"]
    out += ["", "## Real questions with no relevant passage in the top 8 (production queries)", ""]
    qa = {g["id"]: (g, a) for g, a in rows}
    for r in prod:
        if r["rank"] is None or r["rank"] > 8:
            g, a = qa[r["id"]]
            out += [f"- **{r['id']}** (rank {r['rank'] or '>20'}) _{g['question'][:70]}_", f"  - queries: {a['search_queries']}"]
    (REPORTS_DIR / "analyser_eval.md").write_text("\n".join(out), encoding="utf-8")
    print("\nwrote reports/analyser_eval.md |", llm.summary())


if __name__ == "__main__":
    main()
