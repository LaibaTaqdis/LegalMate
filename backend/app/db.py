"""Postgres access for the API (Supabase, session pooler): a small connection pool, tiny helpers and the migration runner."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

log = logging.getLogger("legalmate.db")
MIGRATIONS = Path(__file__).parent / "migrations"


class Database:
    def __init__(self, url: str, max_size: int = 5):
        # prepare_threshold=None: no server-side prepared statements, so it also works behind a transaction pooler.
        self.pool = ConnectionPool(url, min_size=1, max_size=max_size, open=False, timeout=15, max_idle=300,
                                   check=ConnectionPool.check_connection,
                                   kwargs={"row_factory": dict_row, "prepare_threshold": None})

    def open(self) -> None:
        self.pool.open(wait=True, timeout=30)

    def close(self) -> None:
        self.pool.close()

    @contextmanager
    def tx(self) -> Iterator[Connection]:
        """One transaction: commits on success, rolls back on any exception."""
        with self.pool.connection() as conn:
            yield conn

    def one(self, sql: str, params: Any = None) -> dict | None:
        with self.tx() as c:
            return c.execute(sql, params).fetchone()

    def all(self, sql: str, params: Any = None) -> list[dict]:
        with self.tx() as c:
            return c.execute(sql, params).fetchall()

    def run(self, sql: str, params: Any = None) -> int:
        with self.tx() as c:
            return c.execute(sql, params).rowcount

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
