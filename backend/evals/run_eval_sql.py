"""Evaluate the production SQL path (hybrid_search in Postgres) on the gold questions.

    python -m evals.run_eval_sql --url postgresql://...        # default: DATABASE_URL

Same metrics as evals.run_eval, so the two can be compared: the SQL function must match the offline reference.
"""
from __future__ import annotations

import argparse
import os
import time

import psycopg

from retrieval.lexical import tokens
from retrieval.search import QueryEmbedder

from .gold import GOLD
from .labels import Labeler, load_chunks
from .run_eval import fmt, metrics, user_jur


def lex_query(q: str) -> str:
    return " | ".join(dict.fromkeys(tokens(q)))        # OR semantics, de-duplicated, only [a-z0-9] words


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--w-vec", type=float, default=1.0)
    ap.add_argument("--w-lex", type=float, default=1.0)
    ap.add_argument("--rrf-k", type=int, default=60)
    args = ap.parse_args()

    chunks = load_chunks()
    lab = Labeler(chunks)
    pos = [g for g in GOLD if not g["neg"]]
    hash_of = {c["chunk_id"]: c["chunk_hash"] for c in chunks}
    rel_hashes = {g["id"]: {chunks[i]["chunk_hash"] for i in lab.relevant(g)} for g in pos}
    emb = QueryEmbedder(args.model)
    qv = dict(zip([g["query_en"] for g in pos], emb.embed([g["query_en"] for g in pos], True)))

    res, times = [], []
    with psycopg.connect(args.url, autocommit=True) as conn:
        conn.execute("set hnsw.ef_search = 100")
        for g in pos:
            vec = "[" + ",".join(f"{x:.6f}" for x in qv[g["query_en"]]) + "]"
            t = time.time()
            rows = conn.execute("select chunk_id, score, cosine from hybrid_search(%s::vector, %s, %s, 20, 50, %s, %s, %s)",
                                [vec, lex_query(g["query_en"]), user_jur(g), args.w_vec, args.w_lex, args.rrf_k]).fetchall()
            times.append(time.time() - t)
            rank = next((r for r, row in enumerate(rows, start=1) if hash_of[row[0]] in rel_hashes[g["id"]]), None)
            res.append({"id": g["id"], "rank": rank})
    print(f"SQL hybrid_search (vector {args.w_vec} : keyword {args.w_lex}, rrf_k {args.rrf_k}):")
    print("   hit@1 | hit@3 | hit@5 | hit@10 | hit@20 | MRR")
    print("  ", fmt(metrics(res)))
    times.sort()
    print(f"   query time (search only, excludes query embedding): median {times[len(times)//2]*1000:.0f} ms, p95 {times[int(len(times)*.95)]*1000:.0f} ms, max {times[-1]*1000:.0f} ms")


if __name__ == "__main__":
    main()
