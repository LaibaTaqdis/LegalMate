"""Optional local copy of the law text the keyword index is built from, so a start does not download ~22 MB from Supabase every time.

OFF by default. It runs only when KB_CACHE=on (the project owner asked for it for the assistant's own test runs; developers and teammates
keep the normal behaviour). How it works: a tiny query returns a fingerprint of the table (a row count and an md5 over each chunk's id,
hash, legal status, jurisdiction and scope, computed inside Postgres: nothing is downloaded for it). If a file for that fingerprint exists
in KB_CACHE_DIR (default backend/data/kb_cache, which git ignores) it is read from disk; otherwise the rows are streamed as before and
the file is written. Any change to the law text, a status or a scope changes the fingerprint, so a stale copy is never used.
The file is written and read only by this process on this machine (pickle, never from anywhere else).
"""
from __future__ import annotations

import logging
import os
import pickle
import tempfile
from pathlib import Path
from typing import Callable, Iterator

log = logging.getLogger("legalmate.kbcache")

# What identifies the rows we keep: if any of this changes in the database, the local copy is out of date.
FINGERPRINT_SQL = (
    "select count(*), md5(string_agg(chunk_id || ':' || coalesce(chunk_hash, '') || ':' || coalesce(legal_status, '') || ':' || coalesce(jurisdiction, '') "
    "|| ':' || coalesce(applies_to::text, '') || ':' || coalesce(unit_type, ''), '|' order by chunk_id)) from law_chunks")


def enabled() -> bool:
    return os.environ.get("KB_CACHE", "off").strip().lower() in ("on", "1", "true", "yes")


def cache_dir() -> Path:
    return Path(os.environ.get("KB_CACHE_DIR") or Path(__file__).resolve().parent.parent / "data" / "kb_cache")


class Source:
    """Iterates the rows (from the local copy or the database) and says afterwards which one it was in `.status`: 'hit', 'miss' or 'off'."""

    def __init__(self, fingerprint: Callable[[], str], stream: Callable[[], Iterator[tuple]], directory: Path | None = None, use: bool | None = None):
        self._fingerprint, self._stream = fingerprint, stream
        self._dir = directory or cache_dir()
        self._use = enabled() if use is None else use
        self.status = "off"

    def __iter__(self) -> Iterator[tuple]:
        if not self._use:
            yield from self._stream()
            return
        try:
            fp = self._fingerprint()
        except Exception:                                                             # noqa: BLE001 - no fingerprint: just do it the normal way
            log.warning("could not fingerprint the law table; not using the local copy", exc_info=True)
            self.status = "off"
            yield from self._stream()
            return
        path = self._dir / f"kb_{fp}.pkl"
        if path.exists():
            try:
                with path.open("rb") as f:
                    rows = pickle.load(f)
                self.status = "hit"
                yield from rows
                return
            except Exception:                                                         # noqa: BLE001 - damaged file: fetch again and replace it
                log.warning("local law copy %s could not be read; fetching again", path, exc_info=True)
        self.status = "miss"
        rows: list[tuple] = []
        for row in self._stream():
            rows.append(row)
            yield row
        self._write(path, rows)                                                       # only reached when the whole stream was read

    def _write(self, path: Path, rows: list[tuple]) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self._dir, suffix=".tmp")
            with os.fdopen(fd, "wb") as f:
                pickle.dump(rows, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, path)                                                     # never a half-written file under the real name
            for old in self._dir.glob("kb_*.pkl"):                                    # keep only the current copy
                if old != path:
                    old.unlink(missing_ok=True)
            log.info("saved the law text locally (%d rows, %.1f MB): %s", len(rows), path.stat().st_size / 1e6, path)
        except Exception:                                                             # noqa: BLE001 - a full disk must not stop the engine
            log.warning("could not save the local law copy", exc_info=True)
