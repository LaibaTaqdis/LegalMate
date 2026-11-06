"""Load the knowledge base into Postgres (Supabase or a local test server).

    python -m db.load --schema-only                 # create tables + functions only
    python -m db.load                               # schema + REPLACE all documents/chunks/embeddings + build indexes
    python -m db.load --upsert                      # keep existing rows, update by id (leaves dead rows: disk grows)
    python -m db.load --url postgresql://...        # default: DATABASE_URL from backend/.env

A normal load empties the knowledge-base tables first (they are fully regenerable and nothing else references them);
upserting instead roughly doubles the on-disk size until a VACUUM FULL, which matters on a 500 MB free database.

Needs: data/processed/chunks.jsonl, data/interim/manifest.json, data/index/<model>/embeddings.npy
Use the Supabase *pooler* connection string (IPv4). The load is idempotent (upserts by id).
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import psycopg

from ingest.config import DATA_DIR, INTERIM_DIR, PROCESSED_DIR

SCHEMA = Path(__file__).with_name("schema.sql")
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
BATCH = 500

DOC_COLS = ["doc_id", "title", "year", "doc_type", "jurisdiction", "applies_to", "tier", "is_amendment", "legal_status",
            "status_scope", "status_note", "source_urls", "amends", "amended_by", "n_pages", "source_path"]
CHUNK_COLS = ["chunk_id", "doc_id", "ordinal", "act_title", "year", "doc_type", "jurisdiction", "applies_to", "tier",
              "legal_status", "status_scope", "status_note", "unit_type", "section_no", "section_nums", "section_label",
              "heading", "part", "chapter", "order_name", "schedule", "page_start", "page_end", "part_index", "parts_total",
              "header", "body", "amendment_notes", "chunk_hash", "embedding"]


def doc_row(d: dict) -> list:
    return [d["doc_id"], d["title"], d["year"], d["doc_type"], d["jurisdiction"], d["applies_to"], d["tier"], d["is_amendment"],
            d["legal_status"], d.get("status_scope"), d.get("status_note", ""), d["source_urls"], d["amends"], d["amended_by"],
            d["n_pages"], d["paths"][0]]


def chunk_row(c: dict, vec: np.ndarray) -> list:
    return [c["chunk_id"], c["doc_id"], c["ordinal"], c["act_title"], c["year"], c["doc_type"], c["jurisdiction"], c["applies_to"],
            c["tier"], c["legal_status"], c.get("status_scope"), c.get("status_note", ""), c["unit_type"], c["section_no"],
            c.get("section_nums", []), c["section_label"], c["heading"], c["part"], c["chapter"], c["order"], c["schedule"],
            c["page_start"], c["page_end"], c["part_index"], c["parts_total"], c["header"], c["text"],
            c["amendment_notes"], c["chunk_hash"], "[" + ",".join(f"{x:.6f}" for x in vec) + "]"]


def upsert_sql(table: str, cols: list[str], key: str, vec_col: str | None = None) -> str:
    ph = ", ".join("%s::vector" if c == vec_col else "%s" for c in cols)
    sets = ", ".join(f"{c} = excluded.{c}" for c in cols if c != key)
    return f"insert into {table} ({', '.join(cols)}) values ({ph}) on conflict ({key}) do update set {sets}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--schema-only", action="store_true")
    ap.add_argument("--upsert", action="store_true", help="update rows in place instead of replacing everything")
    ap.add_argument("--skip-indexes", action="store_true")
    args = ap.parse_args()

    url = args.url or os.environ.get("DATABASE_URL")
    if not url:
        env = Path(__file__).resolve().parent.parent / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
    if not url:
        raise SystemExit("No database URL: pass --url or set DATABASE_URL in backend/.env (Supabase pooler connection string).")

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        print("schema applied")
        if args.schema_only:
            return
        if not args.upsert:
            conn.execute("truncate law_chunks, law_documents cascade")
            print("knowledge-base tables emptied (replace mode)")

        manifest = json.loads((INTERIM_DIR / "manifest.json").read_text(encoding="utf-8"))["docs"]
        chunks = [json.loads(l) for l in open(PROCESSED_DIR / "chunks.jsonl", encoding="utf-8")]
        emb = np.load(DATA_DIR / "index" / args.model.replace("/", "__") / "embeddings.npy")
        assert emb.shape[0] == len(chunks), f"embeddings ({emb.shape[0]}) and chunks ({len(chunks)}) are out of sync"
        assert emb.shape[1] == 384, "schema.sql declares vector(384); update it for other models"
        live_docs = {c["doc_id"] for c in chunks}
        docs = [d for d in manifest if not d["duplicate_of"] and d["doc_id"] in live_docs]

        t0 = time.time()
        with conn.cursor() as cur:
            cur.executemany(upsert_sql("law_documents", DOC_COLS, "doc_id"), [doc_row(d) for d in docs])
            print(f"{len(docs)} documents loaded")
            sql = upsert_sql("law_chunks", CHUNK_COLS, "chunk_id", "embedding")
            for i in range(0, len(chunks), BATCH):
                cur.executemany(sql, [chunk_row(c, emb[i + j]) for j, c in enumerate(chunks[i:i + BATCH])])
                if (i // BATCH) % 10 == 0:
                    print(f"  chunks {min(i + BATCH, len(chunks))}/{len(chunks)}  ({time.time() - t0:.0f}s)", flush=True)
        print(f"{len(chunks)} chunks loaded in {time.time() - t0:.0f}s")

        if not args.skip_indexes:
            t1 = time.time()
            conn.execute("create index if not exists law_chunks_fts_idx on law_chunks using gin (fts)")
            conn.execute("create index if not exists law_chunks_embedding_idx on law_chunks using hnsw (embedding vector_cosine_ops) "
                         "with (m = 16, ef_construction = 64)")
            conn.execute("analyze law_chunks")
            print(f"indexes built in {time.time() - t1:.0f}s")

        n_docs = conn.execute("select count(*) from law_documents").fetchone()[0]
        n_chunks = conn.execute("select count(*) from law_chunks").fetchone()[0]
        size = conn.execute("select pg_size_pretty(pg_total_relation_size('law_chunks')), pg_size_pretty(pg_database_size(current_database()))").fetchone()
        print(f"database now has {n_docs} documents, {n_chunks} chunks | law_chunks incl. indexes: {size[0]} | whole database: {size[1]}")


if __name__ == "__main__":
    main()
