"""Security self-check: which tables are NOT protected by Row Level Security?

    python -m app.migrations_check            (against DATABASE_URL in backend/.env)

Supabase exposes the `public` schema through a REST API that anyone holding the (public) anon key can call. A table without RLS
there can be read or changed by anyone. Our tables live in the unexposed `app` schema AND have RLS on; this proves it.
"""
from __future__ import annotations

from .db import Database

SQL = """
select n.nspname || '.' || c.relname as name
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where c.relkind = 'r' and not c.relrowsecurity
  and (n.nspname = 'app' or (n.nspname = 'public' and c.relname in ('law_documents', 'law_chunks')))
order by 1
"""


def tables_without_rls(db: Database) -> list[str]:
    return [r["name"] for r in db.all(SQL) if r["name"] != "app.schema_migrations"]


def main() -> int:
    from .config import get_app_settings
    s = get_app_settings()
    db = Database(s.database_url, max_size=1)
    db.open()
    try:
        bad = tables_without_rls(db)
    finally:
        db.close()
    if bad:
        print("NOT protected by Row Level Security:", ", ".join(bad))
        return 1
    print("OK: every app table and the law tables have Row Level Security enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
