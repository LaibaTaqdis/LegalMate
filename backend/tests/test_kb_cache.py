"""The optional local copy of the law text (retrieval/kb_cache.py). No database, no network: the database is a pair of fakes."""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from retrieval.kb_cache import Source, cache_dir, enabled     # noqa: E402

ROWS = [("c1", "Punjab", ["Punjab"], "unverified", "h1", "Section 1", "A landlord may seek eviction."),
        ("c2", "Federal", ["Federal"], "repealed", "h2", "Section 2", "Repealed text.")]


class Db:
    """A pretend law table: `fingerprint` changes when the data changes, `streams` counts full downloads."""

    def __init__(self, rows=ROWS, fp="2-abc"):
        self.rows, self.fp, self.streams, self.fingerprints = list(rows), fp, 0, 0

    def fingerprint(self):
        self.fingerprints += 1
        return self.fp

    def stream(self):
        self.streams += 1
        yield from self.rows


def run(db, directory, use=True):
    src = Source(db.fingerprint, db.stream, directory, use)
    return list(src), src.status


def test_it_is_off_unless_asked_for(monkeypatch, tmp_path):
    monkeypatch.delenv("KB_CACHE", raising=False)
    assert enabled() is False
    monkeypatch.setenv("KB_CACHE", "on")
    assert enabled() is True
    for off in ("off", "0", "", "no"):
        monkeypatch.setenv("KB_CACHE", off)
        assert enabled() is False
    monkeypatch.delenv("KB_CACHE")
    db = Db()
    rows, status = run(db, tmp_path, use=None)                                  # the default: no fingerprint query, no file, the normal download
    assert rows == ROWS and status == "off" and db.fingerprints == 0 and db.streams == 1 and not list(tmp_path.iterdir())


def test_first_start_downloads_and_saves_then_the_next_reads_from_disk(tmp_path):
    db = Db()
    rows, status = run(db, tmp_path)
    assert rows == ROWS and status == "miss" and db.streams == 1
    saved = list(tmp_path.glob("kb_*.pkl"))
    assert len(saved) == 1 and pickle.loads(saved[0].read_bytes()) == ROWS
    rows, status = run(db, tmp_path)
    assert rows == ROWS and status == "hit" and db.streams == 1 and db.fingerprints == 2                # one tiny query, no second download


def test_a_changed_table_is_never_served_from_an_old_copy(tmp_path):
    db = Db()
    run(db, tmp_path)
    db.rows, db.fp = ROWS + [("c3", "ICT", ["ICT"], "unverified", "h3", "Section 3", "New law.")], "3-def"
    rows, status = run(db, tmp_path)
    assert len(rows) == 3 and status == "miss" and db.streams == 2
    assert [p.name for p in tmp_path.glob("kb_*.pkl")] == ["kb_3-def.pkl"]                                # the old copy was removed
    assert run(db, tmp_path)[1] == "hit"


def test_a_damaged_copy_is_replaced_not_trusted(tmp_path):
    db = Db()
    run(db, tmp_path)
    (tmp_path / "kb_2-abc.pkl").write_bytes(b"not a pickle")
    rows, status = run(db, tmp_path)
    assert rows == ROWS and status == "miss" and db.streams == 2
    assert run(db, tmp_path)[1] == "hit"


def test_if_the_fingerprint_fails_it_just_downloads(tmp_path):
    db = Db()
    db.fingerprint = lambda: (_ for _ in ()).throw(RuntimeError("database busy"))
    rows, status = run(db, tmp_path)
    assert rows == ROWS and status == "off" and db.streams == 1 and not list(tmp_path.iterdir())


def test_a_download_that_stops_half_way_saves_nothing(tmp_path):
    db = Db()

    def broken():
        yield ROWS[0]
        raise ConnectionError("connection dropped")

    src = Source(db.fingerprint, broken, tmp_path, True)
    try:
        list(src)
        raise AssertionError("the error should have reached the caller")
    except ConnectionError:
        pass
    assert not list(tmp_path.iterdir())                                                                  # no partial file to be mistaken for the whole


def test_an_unwritable_folder_does_not_stop_the_engine(tmp_path):
    blocker = tmp_path / "file_not_folder"
    blocker.write_text("x")
    rows, status = run(Db(), blocker / "sub")                                                            # cannot create a folder under a file
    assert rows == ROWS and status == "miss"


def test_the_default_folder_is_inside_the_ignored_data_folder(monkeypatch):
    monkeypatch.delenv("KB_CACHE_DIR", raising=False)
    assert cache_dir().parts[-3:] == ("backend", "data", "kb_cache") or cache_dir().parts[-2:] == ("data", "kb_cache")
    monkeypatch.setenv("KB_CACHE_DIR", "somewhere")
    assert cache_dir() == Path("somewhere")
