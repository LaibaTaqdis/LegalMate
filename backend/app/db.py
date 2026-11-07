"""Postgres access for the API (Supabase, session pooler): a small connection pool, tiny helpers and the migration runner."""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

log = logging.getLogger("legalmate.db")
MIGRATIONS = Path(__file__).parent / "migrations"


FRESH_SECONDS = 20          # a connection used this recently is trusted without a health check (each check costs a full round trip)


def _check(conn: Connection) -> None:
    """Pool health check, skipped for a connection that was used a moment ago. Supabase's pooler only drops connections that sat idle."""
    if time.monotonic() - getattr(conn, "_lm_used", 0.0) < FRESH_SECONDS:
        return
    conn.execute("select 1")


class Database:
    """Single statements (`one`, `all`, `run`) run in autocommit mode: one network round trip each, and a single statement is atomic
    anyway. `tx()` opens a real transaction for work that must succeed or fail together. Measured against Supabase (96 ms per round
    trip): a pooled query with a transaction and a health check cost 353 ms; now about 100 ms."""

    def __init__(self, url: str, max_size: int = 5):
        # prepare_threshold=None: no server-side prepared statements, so it also works behind a transaction pooler.
        self.pool = ConnectionPool(url, min_size=1, max_size=max_size, open=False, timeout=15, max_idle=300, check=_check,
                                   kwargs={"row_factory": dict_row, "prepare_threshold": None, "autocommit": True})

    def open(self) -> None:
        self.pool.open(wait=True, timeout=30)

    def close(self) -> None:
        self.pool.close()

    @contextmanager
    def conn(self) -> Iterator[Connection]:
        """A pooled connection in autocommit mode (no transaction)."""
        with self.pool.connection() as conn:
            try:
                yield conn
            finally:
                conn._lm_used = time.monotonic()

    @contextmanager
    def tx(self) -> Iterator[Connection]:
        """One transaction: commits on success, rolls back on any exception."""
        with self.conn() as c:
            with c.transaction():
                yield c

    def one(self, sql: str, params: Any = None) -> dict | None:
        with self.conn() as c:
            return c.execute(sql, params).fetchone()

    def all(self, sql: str, params: Any = None) -> list[dict]:
        with self.conn() as c:
            return c.execute(sql, params).fetchall()

    def run(self, sql: str, params: Any = None) -> int:
        with self.conn() as c:
            return c.execute(sql, params).rowcount

    def batch(self, statements: list[tuple[str, Any]]) -> list[list[dict]]:
        """Several independent SELECTs sent together in one round trip (libpq pipeline). Returns each statement's rows."""
        with self.conn() as c:
            with c.pipeline():
                cursors = [c.execute(sql, params) for sql, params in statements]
            return [cur.fetchall() for cur in cursors]

    def ping(self) -> bool:
        try:
            return self.one("select 1 as ok")["ok"] == 1
        except Exception:
            return False


def migrate(db: Database) -> list[str]:
    """Apply app/migrations/*.sql that have not run yet (in file-name order). Safe to run on every start-up and from two processes at once."""
    applied: list[str] = []
    with db.tx() as c:
        c.execute("select pg_advisory_xact_lock(727401)")          # one migrator at a time
        c.execute("create schema if not exists app")
        c.execute("create table if not exists app.schema_migrations (name text primary key, applied_at timestamptz not null default now())")
        done = {r["name"] for r in c.execute("select name from app.schema_migrations").fetchall()}
        for f in sorted(MIGRATIONS.glob("*.sql")):
            if f.name in done:
                continue
            c.execute(f.read_text(encoding="utf-8"))
            c.execute("insert into app.schema_migrations (name) values (%s)", [f.name])
            applied.append(f.name)
            log.info("applied migration %s", f.name)
    return applied
