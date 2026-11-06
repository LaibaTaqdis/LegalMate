"""Throw-away local Postgres (with pgvector) for development and tests: no Docker, no Supabase quota.

    python -m db.local_pg            # starts the server, prints its URL, keeps running until Ctrl+C
    python -m db.load --url <that url>

Data lives in backend/data/pgdata (gitignored). Needs `pip install pgserver`.
"""
from __future__ import annotations

import time

import pgserver

from ingest.config import DATA_DIR


def main() -> None:
    srv = pgserver.get_server(DATA_DIR / "pgdata", cleanup_mode=None)
    print("local Postgres ready:", srv.get_uri(), flush=True)
    print("Ctrl+C to stop (data is kept).")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
