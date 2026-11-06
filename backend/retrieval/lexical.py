"""Keyword search (BM25 + Porter stemming) over chunks using SQLite FTS5.

Why not Postgres full-text search? Measured on the gold questions, Postgres `ts_rank_cd` has no IDF/BM25 weighting and
retrieves much worse (keyword-only hit@10 75% vs 90% with BM25) and is ~4x slower. Supabase's free tier has no BM25
extension, so keyword ranking runs in the app from a small local index built from the database (about 20 MB, a few seconds).

Keys are opaque (row index offline, chunk_id in production); the index stores them as rowids via a side list.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from typing import Hashable, Iterable

_STOP = set("a an the of to in on for and or is are was were be been i my me we our you your he she it they them his her its their "
            "can could should would will shall may might must do does did how what when where which who whom whose why if than then "
            "that this these those with without by from at as not no any some there here about into over under after before".split())


def tokens(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", q.lower()) if t not in _STOP and len(t) > 1]


class LexicalIndex:
    def __init__(self, rows: Iterable[tuple[Hashable, str, str]], path: str = ":memory:"):
        """rows = (key, header, body). `path` may be a file to keep the index between runs."""
        self.keys: list[Hashable] = []
        # A server answers from several threads: one connection, used by one thread at a time (see the lock in search()).
        self.db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self.db.execute("DROP TABLE IF EXISTS f")
        self.db.execute("CREATE VIRTUAL TABLE f USING fts5(header, body, tokenize='porter unicode61')")
        batch = []
        for key, header, body in rows:
            self.keys.append(key)
            batch.append((len(self.keys) - 1, header, body))
            if len(batch) >= 2000:
                self.db.executemany("INSERT INTO f(rowid, header, body) VALUES (?,?,?)", batch)
                batch = []
        if batch:
            self.db.executemany("INSERT INTO f(rowid, header, body) VALUES (?,?,?)", batch)
        self.db.commit()

    def __len__(self) -> int:
        return len(self.keys)

    def search(self, query: str, k: int = 50, header_weight: float = 2.0) -> list[tuple[Hashable, float]]:
        ts = tokens(query)
        if not ts:
            return []
        match = " OR ".join(f'"{t}"' for t in ts)
        # bm25() is lower-is-better; weights are per column (header, body)
        with self._lock:
            rows = self.db.execute(
                f"SELECT rowid, bm25(f, {header_weight}, 1.0) AS s FROM f WHERE f MATCH ? ORDER BY s LIMIT ?", (match, k)).fetchall()
        return [(self.keys[int(r)], -float(s)) for r, s in rows]
