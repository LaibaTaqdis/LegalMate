"""Evaluate the production retrieval path (pgvector + local BM25) on the gold questions, and time it.

    python -m evals.run_eval_kb --url postgresql://...        # default: DATABASE_URL
"""
from __future__ import annotations

import argparse
import os
import time

from retrieval.kb import KnowledgeBase
from retrieval.search import Params, QueryEmbedder

from .gold import GOLD
from .labels import Labeler, load_chunks
from .run_eval import fmt, metrics, user_jur


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    args = ap.parse_args()

    chunks = load_chunks()
    lab = Labeler(chunks)
    pos = [g for g in GOLD if not g["neg"]]
    hash_of = {c["chunk_id"]: c["chunk_hash"] for c in chunks}
    rel_hashes = {g["id"]: {chunks[i]["chunk_hash"] for i in lab.relevant(g)} for g in pos}
    emb = QueryEmbedder(args.model)
    kb = KnowledgeBase(args.url, args.model, emb)
    print(f"KnowledgeBase ready: {len(kb.lex)} chunks indexed, startup {kb.startup_seconds:.1f}s")

    res, parts = [], {"embed": [], "vector": [], "keyword": [], "fetch": [], "total": []}
    for g in pos:
        t = {}
        t0 = time.time()
        hits = kb.search(g["query_en"], user_jur(g), k=20, p=Params(), timings=t)
        parts["total"].append(time.time() - t0)
        for key in ("embed", "vector", "keyword", "fetch"):
            parts[key].append(t[key])
        rank = next((r for r, h in enumerate(hits, start=1) if hash_of[h["chunk_id"]] in rel_hashes[g["id"]]), None)
        res.append({"id": g["id"], "rank": rank})
    print("reference (offline, hybrid 1:1):  hit@1 62.0 | 78.7 | 86.1 | 94.4 | 97.2 | MRR 0.724")
    print("production KnowledgeBase:         hit@1 | hit@3 | hit@5 | hit@10 | hit@20 | MRR")
    print("                                 ", fmt(metrics(res)))
    for key, v in parts.items():
        v.sort()
        print(f"  {key:8} median {v[len(v)//2]*1000:6.1f} ms   p95 {v[int(len(v)*.95)]*1000:6.1f} ms")
    for act, sec in (("Penal Code", "379"), ("Constitution", "10"), ("Rented Premises", "15")):
        r = kb.lookup_section(act, sec, 1)
        print(f"  lookup_section({act!r}, {sec!r}) -> {r[0]['header'][-70:] if r else 'NOT FOUND'}")


if __name__ == "__main__":
    main()
