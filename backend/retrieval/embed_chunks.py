"""Phase 2 - embed every chunk with a fastembed (ONNX, CPU) model.

    python -m retrieval.embed_chunks                       # BAAI/bge-small-en-v1.5 (default, 384-d)
    python -m retrieval.embed_chunks --model BAAI/bge-base-en-v1.5

Output: data/index/<model>/embeddings.npy (float32, L2-normalised, row i = chunk i of chunks.jsonl)
        data/index/<model>/meta.json
Chunks are embedded sorted by length (less padding = ~1.5x faster) and checkpointed, so an interrupted run resumes.
This is a one-time job for whoever builds the index; teammates only embed single queries at runtime.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from ingest.config import DATA_DIR, PROCESSED_DIR

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
CHECKPOINT_EVERY = 1000


def slug(model: str) -> str:
    return model.replace("/", "__")


def index_dir(model: str):
    d = DATA_DIR / "index" / slug(model)
    d.mkdir(parents=True, exist_ok=True)
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--batch-size", type=int, default=32)
    args = ap.parse_args()

    from fastembed import TextEmbedding

    texts = [json.loads(l)["embed_text"] for l in open(PROCESSED_DIR / "chunks.jsonl", encoding="utf-8")]
    n = len(texts)
    order = np.argsort([len(t) for t in texts], kind="stable")          # short -> long
    out_dir = index_dir(args.model)
    ck_path, ck_meta = out_dir / "partial.npy", out_dir / "partial.json"

    model = TextEmbedding(model_name=args.model)
    dim = len(next(iter(model.embed(["probe"]))))
    emb = np.zeros((n, dim), dtype=np.float32)
    done = 0
    if ck_path.exists() and ck_meta.exists():
        meta = json.loads(ck_meta.read_text())
        if meta.get("n") == n and meta.get("dim") == dim:
            emb, done = np.load(ck_path), meta["done"]
            print(f"resuming from {done}/{n}")
    t0 = time.time()
    start = done
    while done < n:
        idx = order[done:done + CHECKPOINT_EVERY]
        vecs = np.array(list(model.embed([texts[i] for i in idx], batch_size=args.batch_size)), dtype=np.float32)
        emb[idx] = vecs
        done += len(idx)
        np.save(ck_path, emb)
        ck_meta.write_text(json.dumps({"n": n, "dim": dim, "done": done}))
        rate = (done - start) / (time.time() - t0)
        print(f"{done}/{n}  {rate:.1f} chunks/s  eta {(n - done) / max(rate, 1e-9) / 60:.1f} min", flush=True)

    emb /= np.maximum(np.linalg.norm(emb, axis=1, keepdims=True), 1e-9)   # make sure rows are unit length
    np.save(out_dir / "embeddings.npy", emb)
    (out_dir / "meta.json").write_text(json.dumps({"model": args.model, "dim": dim, "n": n, "seconds": round(time.time() - t0)}))
    ck_path.unlink(missing_ok=True)
    ck_meta.unlink(missing_ok=True)
    print(f"done: {emb.shape} -> {out_dir / 'embeddings.npy'}")


if __name__ == "__main__":
    main()
