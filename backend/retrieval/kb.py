"""Production retrieval: pgvector (in Postgres) + BM25 (local SQLite FTS5 built from the same table) + shared fusion.

    kb = KnowledgeBase(DATABASE_URL)                 # connects, streams all chunks once to build the local keyword index
    hits = kb.search("tenant not paying rent landlord eviction", jur="Punjab", k=8)

Startup cost (about 20 MB read from Postgres, a few seconds) is paid once per process; each search is then
~5 ms vector query + ~5 ms BM25 + one small fetch, plus the query embedding (~30-80 ms on CPU).
"""
from __future__ import annotations

import threading
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
        self._url, self._ef = database_url, int(ef_search)
        self._conn_lock = threading.Lock()
        self.conn = self._connect()
        self.embedder = embedder or QueryEmbedder(model)
        t0 = time.time()
        self.meta: dict[str, tuple] = {}              # chunk_id -> (jurisdiction, applies_to set, repealed, text hash)

        def rows():
            with self.conn.transaction():                              # server-side cursors need a transaction
                with self.conn.cursor(name="kb_stream") as cur:        # streams in batches: constant memory
                    cur.itersize = 2000
                    cur.execute("select chunk_id, jurisdiction, applies_to, legal_status, chunk_hash, header, body, unit_type from law_chunks order by chunk_id")
                    for cid, jur, applies, status, h, header, body, utype in cur:
                        if utype == "toc":          # a table of contents that is not law: never retrievable
                            continue
                        self.meta[cid] = (jur, set(applies or []) | {jur}, status == "repealed", h)
                        yield cid, header, body

        self.lex = LexicalIndex(rows())
        self.docs = self.conn.execute("select doc_id, title, jurisdiction, is_amendment from law_documents").fetchall()   # for Act-name routing
        self._qcache: dict[tuple, np.ndarray] = {}
        self.startup_seconds = time.time() - t0

    # ------------------------------------------------------------------ connection (Supabase's pooler drops idle connections)
    def _connect(self):
        conn = psycopg.connect(self._url, autocommit=True)
        conn.execute(f"set hnsw.ef_search = {self._ef}")
        return conn

    def _run(self, sql: str, params=None):
        """conn.execute with one automatic reconnect if the server closed the connection while idle."""
        try:
            return self.conn.execute(sql, params)
        except (psycopg.OperationalError, psycopg.InterfaceError):
            with self._conn_lock:
                if self.conn.closed or self._broken():
                    try:
                        self.conn.close()
                    except Exception:
                        pass
                    self.conn = self._connect()
            return self.conn.execute(sql, params)

    def _broken(self) -> bool:
        try:
            self.conn.execute("select 1")
            return False
        except Exception:
            return True

    # ------------------------------------------------------------------ retrieval
    def embed_query(self, text: str, use_prefix: bool = True) -> np.ndarray:
        """Query embedding with a small cache (the same query is embedded once per turn, however many searches use it)."""
        key = (text, use_prefix)
        if key not in self._qcache:
            if len(self._qcache) > 512:
                self._qcache.clear()
            self._qcache[key] = self.embedder.embed([text], use_prefix)[0]
        return self._qcache[key]

    def search_in_docs(self, query: str, doc_ids: list[str], k: int = 5) -> list[dict]:
        """Best chunks of specific laws (vector search restricted to them). Used when a query names an Act we hold."""
        qv = self.embed_query(query)
        v = "[" + ",".join(f"{x:.6f}" for x in qv) + "]"
        rows = self._run(
            "select chunk_id, 1 - (embedding <=> %s::vector) from law_chunks where doc_id = any(%s) and unit_type <> 'toc' "
            "order by embedding <=> %s::vector limit %s", [v, doc_ids, v, k]).fetchall()
        from .search import Hit
        hits = [Hit(r[0], 1.0 / (60 + i), float(r[1]), sources=("act",)) for i, r in enumerate(rows, 1)]
        return self._fetch(hits, qv)

    def _vector(self, qv: np.ndarray, depth: int) -> list[tuple[str, float]]:
        v = "[" + ",".join(f"{x:.6f}" for x in qv) + "]"
        rows = self._run(
            "select chunk_id, 1 - (embedding <=> %s::vector) from law_chunks order by embedding <=> %s::vector limit %s",
            [v, v, depth]).fetchall()
        return [(r[0], float(r[1])) for r in rows if r[0] in self.meta]      # drops toc chunks (not in meta)

    def search(self, query: str, jur: str | None = None, k: int = 10, p: Params | None = None,
               qvec: np.ndarray | None = None, timings: dict | None = None) -> list[dict]:
        p = p or Params()
        t = time.time()
        qv = None
        if p.w_vec > 0:
            qv = qvec if qvec is not None else self.embed_query(query, p.use_prefix)
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
        # ONE round trip: chunk rows + cosine to the query + document-level facts (amendments, source links)
        cols = ", ".join("c." + c.strip() for c in ROW_COLS.split(","))
        v = "[" + ",".join(f"{x:.6f}" for x in qv) + "]" if qv is not None else None
        cos_sql = "1 - (c.embedding <=> %s::vector)" if v else "null::float8"
        sql = (f"select {cols}, {cos_sql} as cosine, d.is_amendment, d.source_urls, d.n_pages, "
               "coalesce((select array_agg(x.title order by x.year) from law_documents x where x.doc_id = any (d.amended_by)), '{}') as amended_by_titles "
               "from law_chunks c join law_documents d on d.doc_id = c.doc_id where c.chunk_id = any(%s)")
        cur = self._run(sql, ([v] if v else []) + [ids])
        names = [d.name for d in cur.description]
        by_id = {r[0]: dict(zip(names, r)) for r in cur.fetchall()}
        out = []
        for h in hits:
            row = by_id[h.key]
            row.update(score=h.score, cosine=float(row["cosine"] if row["cosine"] is not None else h.cos), bm25=h.bm25, sources=list(h.sources))
            out.append(row)
        return out

    def lookup_section(self, act_like: str, section: str, limit: int = 5) -> list[dict]:
        """Exact lookup when the user names a section: ("Penal Code", "379"), ("Constitution", "10")."""
        cols = ", ".join("c." + c.strip() for c in ROW_COLS.split(","))
        cur = self._run(
            f"select {cols} from law_chunks c join law_documents d on d.doc_id = c.doc_id "
            "where c.act_title ilike %s and c.section_nums @> array[%s] "
            # base laws before the amending instruments that merely mention the same section number
            "order by d.is_amendment, (c.act_title ilike %s) desc, length(c.act_title), "
            "case c.tier when 'curated' then 0 when 'publisher' then 1 else 2 end, c.ordinal limit %s",
            [f"%{act_like}%", section, f"{act_like}%", limit])
        names = [d.name for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    def get_section(self, act_title: str, section: str, jurisdictions: list[str]) -> dict | None:
        """The stored text of one section of one Act, by EXACT title (not a search). `jurisdictions` is the order of preference, for example
        ["Punjab", "Federal"]: an Act that exists in both copies returns the first jurisdiction that has it. None if the Act or section is not
        in the database. Includes the document facts the UI warns about (repealed, amended later, source link)."""
        cols = ", ".join("c." + c.strip() for c in ROW_COLS.split(","))
        cur = self._run(
            f"select {cols}, d.is_amendment, d.source_urls, "
            "coalesce((select array_agg(x.title order by x.year) from law_documents x where x.doc_id = any (d.amended_by)), '{}') as amended_by_titles "
            "from law_chunks c join law_documents d on d.doc_id = c.doc_id "
            "where c.act_title = %s and c.section_nums @> array[%s] and c.unit_type <> 'toc' and c.jurisdiction = any(%s) "
            "order by array_position(%s::text[], c.jurisdiction), c.ordinal limit 1",
            [act_title, section, jurisdictions, jurisdictions])
        row = cur.fetchone()
        return dict(zip([d.name for d in cur.description], row)) if row else None

    def close(self) -> None:
        self.conn.close()
