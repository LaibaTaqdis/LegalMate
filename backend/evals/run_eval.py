"""Retrieval evaluation on the gold questions.

    python -m evals.run_eval                              # bge-small, writes reports/retrieval_eval.md
    python -m evals.run_eval --model BAAI/bge-base-en-v1.5

A question is a HIT at k if any of the top-k results is a relevant chunk (or an identical-text copy of one).
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import time
from dataclasses import replace

import numpy as np

from ingest.config import REPORTS_DIR
from retrieval.search import HybridSearcher, Params, QueryEmbedder

from .gold import GOLD
from .labels import Labeler, load_chunks

KS = (1, 3, 5, 10, 20)


def user_jur(g: dict) -> str | None:
    return None if g["jur"] == "Federal" else g["jur"]       # "Federal" = no province/ICT on the profile


def run(searcher: HybridSearcher, items: list[dict], rel_hashes: dict[str, set], p: Params, field: str,
        qvecs: dict[str, np.ndarray], use_juris: bool = True) -> list[dict]:
    out = []
    for g in items:
        text = g[field]
        hits = searcher.search(text, user_jur(g) if use_juris else None, k=20, p=p, qvec=qvecs.get(text))
        rank = next((r for r, h in enumerate(hits, start=1) if searcher.hashes[h.idx] in rel_hashes[g["id"]]), None)
        out.append({"id": g["id"], "cat": g["cat"], "lang": g["lang"], "rank": rank,
                    "top": [(h.idx, round(h.score, 4), round(h.cos, 3)) for h in hits[:3]],
                    "top_cos": hits[0].cos if hits else 0.0, "top_bm25": max((h.bm25 for h in hits), default=0.0),
                    "top_score": hits[0].score if hits else 0.0})
    return out


def metrics(res: list[dict]) -> dict:
    n = len(res)
    m = {f"hit@{k}": sum(1 for r in res if r["rank"] and r["rank"] <= k) / n for k in KS}
    m["mrr"] = sum(1 / r["rank"] for r in res if r["rank"]) / n
    m["n"] = n
    return m


def fmt(m: dict) -> str:
    return " | ".join(f"{m[f'hit@{k}']*100:5.1f}" for k in KS) + f" | {m['mrr']:.3f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    chunks = load_chunks()
    lab = Labeler(chunks)
    pos = [g for g in GOLD if not g["neg"]]
    neg = [g for g in GOLD if g["neg"]]
    rel_hashes = {g["id"]: {chunks[i]["chunk_hash"] for i in lab.relevant(g)} for g in pos}
    t0 = time.time()
    emb = QueryEmbedder(args.model)
    searcher = HybridSearcher(chunks, args.model, emb)
    print(f"index ready in {time.time() - t0:.0f}s ({len(chunks)} chunks, dim {searcher.emb.shape[1]})")

    texts_en = sorted({g["query_en"] for g in GOLD})
    raw_en = sorted({g["question"] for g in GOLD if g["lang"] == "en"})
    qv_pre = dict(zip(texts_en + raw_en, emb.embed(texts_en + raw_en, True)))
    qv_nopre = dict(zip(texts_en + raw_en, emb.embed(texts_en + raw_en, False)))

    configs = [
        ("keyword only (BM25)", Params(w_vec=0.0), "query_en", qv_pre, True),
        ("vector only, with bge query prefix", Params(w_lex=0.0), "query_en", qv_pre, True),
        ("vector only, no prefix", Params(w_lex=0.0, use_prefix=False), "query_en", qv_nopre, True),
        ("hybrid 1:1", Params(), "query_en", qv_pre, True),
        ("hybrid vector 2 : keyword 1", Params(w_vec=2.0, w_lex=1.0), "query_en", qv_pre, True),
        ("hybrid vector 1 : keyword 2", Params(w_vec=1.0, w_lex=2.0), "query_en", qv_pre, True),
        ("hybrid 1:1, no jurisdiction handling", Params(), "query_en", qv_pre, False),
        ("hybrid 1:1, no de-duplication", Params(dedupe=False), "query_en", qv_pre, True),
    ]
    results = {}
    lines = ["# Retrieval evaluation", "", f"Model: `{args.model}`  |  chunks: {len(chunks):,}  |  labelled questions: {len(pos)}  |  out-of-scope questions: {len(neg)}",
             "", "Hit rate (%) = share of questions with a relevant law section in the top k results; MRR = mean reciprocal rank.", "",
             "## Configurations (question rewritten to English by the analyser, `query_en`)", "",
             "| configuration | hit@1 | hit@3 | hit@5 | hit@10 | hit@20 | MRR |", "|---|---|---|---|---|---|---|"]
    for name, p, field, qv, juris in configs:
        res = run(searcher, pos, rel_hashes, p, field, qv, juris)
        results[name] = res
        lines.append(f"| {name} | " + fmt(metrics(res)).replace(" | ", " | ") + " |")
        print(f"{name:42} {fmt(metrics(res))}", flush=True)

    # weight / depth grid around the best simple hybrid
    lines += ["", "## Weight grid (vector : keyword), jurisdiction on", "", "| w_vec | w_lex | rrf_k | hit@1 | hit@5 | hit@10 | MRR |", "|---|---|---|---|---|---|---|"]
    best = (None, -1)
    for wv, wl, k in [(1, 1, 60), (1, 1, 20), (1, 1, 10), (3, 1, 60), (1, 0.5, 60), (1, 0.25, 60), (1, 1.5, 60), (1, 3, 60), (1, 1, 100)]:
        res = run(searcher, pos, rel_hashes, Params(w_vec=wv, w_lex=wl, rrf_k=k), "query_en", qv_pre, True)
        m = metrics(res)
        lines.append(f"| {wv} | {wl} | {k} | {m['hit@1']*100:.1f} | {m['hit@5']*100:.1f} | {m['hit@10']*100:.1f} | {m['mrr']:.3f} |")
        score = m["mrr"] + 0.5 * m["hit@5"]
        if score > best[1]:
            best = ((wv, wl, k), score)
    wv, wl, k = best[0]
    bp = Params(w_vec=wv, w_lex=wl, rrf_k=k)
    lines += ["", f"Best on this set: vector {wv} : keyword {wl}, rrf_k {k}.", ""]
    print("best weights:", best[0])

    res_best = run(searcher, pos, rel_hashes, bp, "query_en", qv_pre, True)
    mb = metrics(res_best)

    # harder variant: the raw English question without the analyser rewrite
    en_items = [g for g in pos if g["lang"] == "en"]
    res_raw = run(searcher, en_items, rel_hashes, bp, "question", qv_pre, True)
    res_rewr = [r for r in res_best if r["lang"] == "en"]
    lines += ["## Does the analyser rewrite matter? (English questions only)", "", "| input to retrieval | hit@1 | hit@3 | hit@5 | hit@10 | hit@20 | MRR |", "|---|---|---|---|---|---|---|",
              f"| rewritten query (`query_en`) | {fmt(metrics(res_rewr))} |", f"| raw user question | {fmt(metrics(res_raw))} |", ""]
    print("raw question:", fmt(metrics(res_raw)), "| rewritten:", fmt(metrics(res_rewr)))

    # by category
    lines += ["## By category (best configuration)", "", "| category | n | hit@1 | hit@3 | hit@5 | hit@10 | hit@20 | MRR |", "|---|---|---|---|---|---|---|---|"]
    for cat in sorted({r["cat"] for r in res_best}):
        sub = [r for r in res_best if r["cat"] == cat]
        lines.append(f"| {cat} | {len(sub)} | {fmt(metrics(sub))} |")
    ur = [r for r in res_best if r["lang"] != "en"]
    lines += ["", f"Roman-Urdu questions (retrieved via their English rewrite): {len(ur)} questions, " + fmt(metrics(ur)) if ur else "", ""]

    # abstention: how well do top scores separate real questions from out-of-scope ones?
    res_neg = run(searcher, neg, {g["id"]: set() for g in neg}, bp, "query_en", qv_pre, True)
    lines += ["## 'No source found' threshold", "",
              "Top-1 signals for real legal questions vs out-of-scope questions (higher = more confident a source exists).", "",
              "| signal | real questions: min / p10 / median | out-of-scope: max / median | gap (p10 real - max out-of-scope) |", "|---|---|---|---|"]
    for key, label in (("top_cos", "best cosine similarity"), ("top_bm25", "best keyword score"), ("top_score", "fused score")):
        a = sorted(r[key] for r in res_best)
        b = sorted(r[key] for r in res_neg)
        p10 = a[len(a) // 10]
        lines.append(f"| {label} | {a[0]:.3f} / {p10:.3f} / {statistics.median(a):.3f} | {b[-1]:.3f} / {statistics.median(b):.3f} | {p10 - b[-1]:+.3f} |")
    lines.append("")

    # failures
    fails = [r for r in res_best if r["rank"] is None or r["rank"] > 5]
    lines += [f"## Questions without a relevant result in the top 5 ({len(fails)} of {len(res_best)})", ""]
    gq = {g["id"]: g for g in GOLD}
    for r in sorted(fails, key=lambda r: (r["rank"] is None, r["cat"])):
        g = gq[r["id"]]
        exp = "; ".join(f"{s['act']} / {s['head'] or ', '.join(s['has'])}" for s in g["rel"])[:120]
        top = " || ".join(chunks[i]["header"][-55:] for i, _, _ in r["top"])
        lines += [f"- **{r['id']}** (rank {r['rank'] or '>20'}) _{g['question'][:80]}_", f"  - expected: {exp}", f"  - got: {top}"]
    lines.append("")

    out = REPORTS_DIR / (args.report or f"retrieval_eval_{args.model.split('/')[-1]}.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    (REPORTS_DIR / f"retrieval_eval_{args.model.split('/')[-1]}.json").write_text(json.dumps(
        {"best_params": {"w_vec": wv, "w_lex": wl, "rrf_k": k}, "best_metrics": mb,
         "per_question": [{"id": r["id"], "rank": r["rank"]} for r in res_best]}, indent=1), encoding="utf-8")
    print(f"\nwrote {out}")
    print("best:", fmt(mb))


if __name__ == "__main__":
    main()
