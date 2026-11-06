"""Production retrieval: pgvector (in Postgres) + BM25 (local SQLite FTS5 built from the same table) + shared fusion.

    kb = KnowledgeBase(DATABASE_URL)                 # connects, streams all chunks once to build the local keyword index
    hits = kb.search("tenant not paying rent landlord eviction", jur="Punjab", k=8)

Startup cost (about 20 MB read from Postgres, a few seconds) is paid once per process; each search is then
~5 ms vector query + ~5 ms BM25 + one small fetch, plus the query embedding (~30-80 ms on CPU).
"""
from __future__ import annotations

import time

import numpy as np
import psycopg

from .lexical import LexicalIndex
from .search import Params, QueryEmbedder, fuse, jurisdiction_factor

ROW_COLS = ("chunk_id, doc_id, act_title, year, jurisdiction, applies_to, tier, legal_status, status_scope, status_note, unit_type, "
            "section_no, section_nums, section_label, heading, header, body, page_start, page_end, amendment_notes, chunk_hash")


class KnowledgeBase:
    def __init__(self, database_url: str, model: str = "BAAI/bge-small-en-v1.5", embedder: QueryEmbedder | None = None,
                 ef_search: int = 100):
        self.conn = psycopg.connect(database_url, autocommit=True)
        self.conn.execute(f"set hnsw.ef_search = {int(ef_search)}")
        self.embedder = embedder or QueryEmbedder(model)
        t0 = time.time()
        self.meta: dict[str, tuple] = {}              # chunk_id -> (jurisdiction, applies_to set, repealed, text hash)

        def rows():
            with self.conn.transaction():                              # server-side cursors need a transaction
                with self.conn.cursor(name="kb_stream") as cur:        # streams in batches: constant memory
                    cur.itersize = 2000
                    cur.execute("select chunk_id, jurisdiction, applies_to, legal_status, chunk_hash, header, body from law_chunks order by chunk_id")
                    for cid, jur, applies, status, h, header, body in cur:
                        self.meta[cid] = (jur, set(applies or []) | {jur}, status == "repealed", h)
                        yield cid, header, body

        self.lex = LexicalIndex(rows())
        self.startup_seconds = time.time() - t0

    # ------------------------------------------------------------------ retrieval
    def _vector(self, qv: np.ndarray, depth: int) -> list[tuple[str, float]]:
        v = "[" + ",".join(f"{x:.6f}" for x in qv) + "]"
        rows = self.conn.execute(
            "select chunk_id, 1 - (embedding <=> %s::vector) from law_chunks order by embedding <=> %s::vector limit %s",
            [v, v, depth]).fetchall()
        return [(r[0], float(r[1])) for r in rows]

    def search(self, query: str, jur: str | None = None, k: int = 10, p: Params | None = None,
               qvec: np.ndarray | None = None, timings: dict | None = None) -> list[dict]:
        p = p or Params()
        t = time.time()
        qv = None
        if p.w_vec > 0:
            qv = qvec if qvec is not None else self.embedder.embed([query], p.use_prefix)[0]
        t_embed = time.time()
        vec = self._vector(qv, p.depth) if qv is not None else []
        t_vec = time.time()
        lex = self.lex.search(query, p.depth) if p.w_lex > 0 else []
        t_lex = time.time()
        hits = fuse(vec, lex, p,
                    lambda cid: jurisdiction_factor(self.meta[cid][0], self.meta[cid][1], self.meta[cid][2], jur, p),
                    lambda cid: self.meta[cid][3], k)
        out = self._fetch(hits, qv)
        if timings is not None:
            timings.update(embed=t_embed - t, vector=t_vec - t_embed, keyword=t_lex - t_vec, fetch=time.time() - t_lex)
        return out

    def _fetch(self, hits, qv: np.ndarray | None) -> list[dict]:
        if not hits:
            return []
        ids = [h.key for h in hits]
        cos = {}
        if qv is not None:
            v = "[" + ",".join(f"{x:.6f}" for x in qv) + "]"
            cos = dict(self.conn.execute("select chunk_id, 1 - (embedding <=> %s::vector) from law_chunks where chunk_id = any(%s)", [v, ids]).fetchall())
        cur = self.conn.execute(f"select {ROW_COLS} from law_chunks where chunk_id = any(%s)", [ids])
        names = [d.name for d in cur.description]
        by_id = {r[0]: dict(zip(names, r)) for r in cur.fetchall()}
        out = []
        for h in hits:
            row = by_id[h.key]
            row.update(score=h.score, cosine=float(cos.get(h.key, h.cos)), bm25=h.bm25, sources=list(h.sources))
            out.append(row)
        return out

    def lookup_section(self, act_like: str, section: str, limit: int = 5) -> list[dict]:
        """Exact lookup when the user names a section: ("Penal Code", "379"), ("Constitution", "10")."""
        cols = ", ".join("c." + c.strip() for c in ROW_COLS.split(","))
        cur = self.conn.execute(
            f"select {cols} from law_chunks c join law_documents d on d.doc_id = c.doc_id "
            "where c.act_title ilike %s and c.section_nums @> array[%s] "
            # base laws before the amending instruments that merely mention the same section number
            "order by d.is_amendment, (c.act_title ilike %s) desc, length(c.act_title), "
            "case c.tier when 'curated' then 0 when 'publisher' then 1 else 2 end, c.ordinal limit %s",
            [f"%{act_like}%", section, f"{act_like}%", limit])
        names = [d.name for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()
