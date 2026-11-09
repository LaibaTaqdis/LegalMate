"""Legal Vault part B: the user's own files. Local Postgres, in-memory storage, fake model: no Supabase, zero DeepSeek calls.

    python -m pytest tests/test_vault_files.py -q
"""
from __future__ import annotations

import io
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import DocSettings
from app.main import create_app
from tests.conftest import FakeEngine, MemoryStorage, make_settings, signup
from tests.test_documents import CONTRACT, docx, pdf, text_png

A = "/api/v1"


@pytest.fixture(scope="module")
def storage():
    return MemoryStorage()


@pytest.fixture(scope="module")
def client(pg_url, storage):
    with TestClient(create_app(make_settings(pg_url), engine=FakeEngine(), storage=storage)) as c:
        yield c


def up(client, h, data=None, name="lease.pdf", **form):
    data = pdf() if data is None else data
    return client.post(f"{A}/vault/files", files={"file": (name, data, "application/octet-stream")}, data=form, headers=h)


def files(client, h, **params):
    return client.get(f"{A}/vault/files", params=params, headers=h).json()


# ---------------------------------------------------------------------------------------------- upload
def test_upload_keeps_the_original_in_private_storage_and_text_in_the_database(client, storage):
    j, h = signup(client)
    original = pdf(CONTRACT)
    r = up(client, h, original, "../../My Tenancy Agreement.pdf", category="Contracts")
    assert r.status_code == 201, r.text
    f = r.json()
    assert f["name"] == "My Tenancy Agreement.pdf" and f["fileType"] == "pdf" and f["category"] == "Contracts" and f["sizeBytes"] == len(original)
    assert f["textStatus"] == "ready" and f["hasText"] is True and f["folderId"] is None and f["favourite"] is False and f["trashedAt"] is None

    row = client.app.state.ctx.db.one("select storage_path, text from app.vault_files where id = %s", [f["id"]])
    assert row["storage_path"].startswith(j["user"]["id"] + "/") and row["storage_path"].endswith(".pdf")        # a name WE made, not theirs
    assert "Tenancy" not in row["storage_path"] and "monthly rent" in row["text"]
    data, content_type = storage.objects[row["storage_path"]]
    assert data == original and content_type == "application/pdf"                                                # the original, byte for byte
    assert client.get(f"{A}/vault/files/{f['id']}", headers=h).json()["id"] == f["id"]


def test_word_files_are_kept_and_read_too(client):
    _, h = signup(client)
    f = up(client, h, docx(), "deposit.docx").json()
    assert f["fileType"] == "docx" and f["hasText"] and f["category"] == "Other"
    assert files(client, h, q="90,000")["total"] == 1                                                            # found by what is inside


def test_the_type_is_decided_by_content_and_bad_uploads_are_refused_clearly(client, storage):
    _, h = signup(client)
    before = len(storage.objects)
    assert up(client, h, b"<html><script>alert(1)</script></html>", "photo.png").status_code == 415
    assert up(client, h, b"MZ\x90\x00" + b"\x00" * 600, "invoice.pdf").status_code == 415
    assert up(client, h, b"", "empty.pdf").status_code == 400
    assert up(client, h, b"\x89PNG\r\n\x1a\n" + b"junk" * 50, "broken.png").json()["error"]["code"] == "UNREADABLE"
    assert up(client, h, pdf(), "a.pdf", category="Secrets").status_code == 400
    assert up(client, h, pdf(), "a.pdf", folderId="not-a-uuid").status_code == 400
    assert up(client, h, pdf(), "a.pdf", folderId="9b2f2a0e-0000-4000-8000-000000000000").status_code == 404
    assert len(storage.objects) == before                                                                        # nothing was stored for any of them
    assert client.post(f"{A}/vault/files", headers=h).status_code == 400
    assert client.post(f"{A}/vault/files", files={"file": ("a.pdf", pdf())}).status_code == 401


def test_a_file_over_the_size_limit_is_refused(pg_url):
    st = MemoryStorage()
    with TestClient(create_app(make_settings(pg_url, docs=replace(DocSettings(), max_upload_mb=1)), engine=FakeEngine(), storage=st)) as c:
        _, h = signup(c)
        r = up(c, h, b"%PDF-1.4\n" + b"0" * (1024 * 1024 + 10), "big.pdf")
        assert r.status_code == 413 and "1 MB" in r.json()["error"]["message"] and not st.objects


def test_a_photo_is_stored_at_once_and_read_in_the_background_so_it_can_be_found(client):
    _, h = signup(client)
    f = up(client, h, text_png(), "rent photo.png", category="Notices").json()
    assert f["fileType"] == "png" and f["textStatus"] in ("pending", "ready")
    end = time.time() + 90
    while time.time() < end and client.get(f"{A}/vault/files/{f['id']}", headers=h).json()["textStatus"] == "pending":
        time.sleep(0.5)
    got = client.get(f"{A}/vault/files/{f['id']}", headers=h).json()
    assert got["textStatus"] == "ready" and got["hasText"] is True
    assert files(client, h, q="monthly rent")["items"][0]["id"] == f["id"]
    assert "monthly rent" in client.get(f"{A}/vault/files/{f['id']}/text", headers=h).json()["text"]


def test_files_say_so_when_storage_is_not_set_up(pg_url):
    with TestClient(create_app(make_settings(pg_url), engine=FakeEngine())) as c:                                # no Supabase settings, no storage
        _, h = signup(c)
        r = up(c, h)
        assert r.status_code == 503 and "storage" in r.json()["error"]["message"].lower()
        assert c.get(f"{A}/vault/stats", headers=h).json()["filesEnabled"] is False


def test_when_storage_fails_nothing_is_left_behind(pg_url):
    st = MemoryStorage()
    with TestClient(create_app(make_settings(pg_url), engine=FakeEngine(), storage=st)) as c:
        _, h = signup(c)
        st.fail_upload = True
        assert up(c, h).status_code == 503
        assert files(c, h)["total"] == 0
        st.fail_upload = False
        assert up(c, h).status_code == 201


# ---------------------------------------------------------------------------------------------- limits
def test_the_quota_counts_everything_including_the_trash_until_it_is_emptied(pg_url):
    st = MemoryStorage()
    one = pdf(CONTRACT)
    cfg = replace(DocSettings(), vault_quota_mb=1, max_upload_mb=1)
    pad = b"\n%" + b"x" * (400 * 1024)                                                                            # makes each file about 400 KB
    big = one + pad
    with TestClient(create_app(make_settings(pg_url, docs=cfg), engine=FakeEngine(), storage=st)) as c:
        _, h = signup(c)
        a, b = up(c, h, big, "a.pdf").json(), up(c, h, big, "b.pdf").json()
        r = up(c, h, big, "c.pdf")
        assert r.status_code == 422 and r.json()["error"]["code"] == "QUOTA_EXCEEDED" and "not enough space" in r.json()["error"]["message"].lower()
        used = files(c, h)["storage"]
        assert used["quotaBytes"] == 1024 * 1024 and used["usedBytes"] == len(big) * 2
        c.delete(f"{A}/vault/files/{a['id']}", headers=h)                                                         # in the Trash it still takes room
        assert up(c, h, big, "c.pdf").status_code == 422
        assert c.delete(f"{A}/vault/files-trash", headers=h).json() == {"deleted": 1}
        assert up(c, h, big, "c.pdf").status_code == 201 and b["id"]


def test_the_number_of_files_and_folders_is_limited(pg_url):
    st = MemoryStorage()
    cfg = replace(DocSettings(), vault_max_files=2, vault_max_folders=2, vault_uploads_per_hour=3)
    with TestClient(create_app(make_settings(pg_url, docs=cfg), engine=FakeEngine(), storage=st)) as c:
        _, h = signup(c)
        assert up(c, h).status_code == 201 and up(c, h).status_code == 201
        r = up(c, h)
        assert r.status_code == 422 and "2 files" in r.json()["error"]["message"]
        assert up(c, h).status_code == 429                                                                       # the per-hour limit (3) counts every attempt
        assert c.post(f"{A}/vault/folders", json={"name": "One"}, headers=h).status_code == 201
        assert c.post(f"{A}/vault/folders", json={"name": "Two"}, headers=h).status_code == 201
        assert c.post(f"{A}/vault/folders", json={"name": "Three"}, headers=h).status_code == 422


# ---------------------------------------------------------------------------------------------- listing
def test_list_filters_search_sort_and_pages(client):
    _, h = signup(client)
    ids = {n: up(client, h, pdf(CONTRACT + [f"Special unique phrase {n}"]), f"{n}.pdf", category=c).json()["id"]
           for n, c in (("alpha", "Contracts"), ("bravo", "Notices"), ("charlie", "Contracts"), ("delta", "Family"))}
    client.put(f"{A}/vault/files/{ids['bravo']}/favourite", json={"favourite": True}, headers=h)
    client.delete(f"{A}/vault/files/{ids['delta']}", headers=h)

    out = files(client, h)
    assert out["total"] == 3 and out["counts"]["all"] == 3 and out["counts"]["Contracts"] == 2 and out["counts"]["Notices"] == 1
    assert out["counts"]["Family"] == 0 and out["counts"]["favourites"] == 1 and out["counts"]["trash"] == 1
    assert {i["name"] for i in files(client, h, category="Contracts")["items"]} == {"alpha.pdf", "charlie.pdf"}
    assert [i["name"] for i in files(client, h, category="favourites")["items"]] == ["bravo.pdf"]
    assert [i["name"] for i in files(client, h, category="trash")["items"]] == ["delta.pdf"]
    assert [i["name"] for i in files(client, h, q="BRAVO")["items"]] == ["bravo.pdf"]                              # name, any case
    assert [i["name"] for i in files(client, h, q="unique phrase charlie")["items"]] == ["charlie.pdf"]            # contents
    assert files(client, h, q="50%_")["total"] == 0                                                              # LIKE characters are literal
    assert [i["name"] for i in files(client, h, sort="name_asc")["items"]] == ["alpha.pdf", "bravo.pdf", "charlie.pdf"]
    assert [i["name"] for i in files(client, h, sort="name_desc")["items"]] == ["charlie.pdf", "bravo.pdf", "alpha.pdf"]
    p1, p2 = files(client, h, pageSize=2, page=1), files(client, h, pageSize=2, page=2)
    assert len(p1["items"]) == 2 and len(p2["items"]) == 1 and p1["total"] == 3
    assert client.get(f"{A}/vault/files?category=Secrets", headers=h).status_code == 400
    assert client.get(f"{A}/vault/files?sort=sideways", headers=h).status_code == 400
    st = client.get(f"{A}/vault/stats", headers=h).json()
    assert st["filesEnabled"] is True and st["files"]["all"] == 3 and st["storage"]["usedBytes"] > 0 and "counts" in st       # part A's counts are still there


# ---------------------------------------------------------------------------------------------- links
def test_a_link_is_short_lived_and_only_for_the_owner(client, storage):
    _, a = signup(client)
    _, b = signup(client)
    f = up(client, a, pdf(), "Lease agreement.pdf").json()
    r = client.get(f"{A}/vault/files/{f['id']}/link", headers=a).json()
    assert r["url"].startswith("https://storage.test/sign/") and r["expiresIn"] == 300 and "download=" not in r["url"]
    d = client.get(f"{A}/vault/files/{f['id']}/link?download=true", headers=a).json()
    assert "download=Lease agreement.pdf" in d["url"]
    assert client.get(f"{A}/vault/files/{f['id']}/link", headers=b).status_code == 404                            # no link for someone else's file
    storage.fail_sign = True
    try:
        assert client.get(f"{A}/vault/files/{f['id']}/link", headers=a).status_code == 503
    finally:
        storage.fail_sign = False
    acts = [x["action"] for x in client.get(f"{A}/vault/files/{f['id']}/activity", headers=a).json()["items"]]
    assert acts.count("downloaded") == 1 and acts[-1] == "uploaded"


def test_a_renamed_file_still_downloads_with_the_right_extension(client):
    _, h = signup(client)
    f = up(client, h, pdf(), "x.pdf").json()
    client.patch(f"{A}/vault/files/{f['id']}", json={"name": "Final lease"}, headers=h)
    assert "download=Final lease.pdf" in client.get(f"{A}/vault/files/{f['id']}/link?download=true", headers=h).json()["url"]


# ---------------------------------------------------------------------------------------------- changing
def test_rename_move_and_categorise(client):
    _, h = signup(client)
    folder = client.post(f"{A}/vault/folders", json={"name": "Property", "color": "#fbbf24"}, headers=h).json()
    f = up(client, h, pdf(), "scan001.pdf").json()
    r = client.patch(f"{A}/vault/files/{f['id']}", json={"name": "  Sale deed  ", "folderId": folder["id"], "category": "Property"}, headers=h)
    assert r.status_code == 200 and r.json()["name"] == "Sale deed" and r.json()["folderId"] == folder["id"] and r.json()["folderName"] == "Property"
    assert r.json()["category"] == "Property"
    assert files(client, h, folderId=folder["id"])["total"] == 1
    assert client.get(f"{A}/vault/folders", headers=h).json()["items"][0]["fileCount"] == 1
    assert client.patch(f"{A}/vault/files/{f['id']}", json={"folderId": None}, headers=h).json()["folderId"] is None       # out of the folder
    assert client.patch(f"{A}/vault/files/{f['id']}", json={"category": "Other"}, headers=h).json()["name"] == "Sale deed"  # only what is sent changes
    assert client.patch(f"{A}/vault/files/{f['id']}", json={"name": "  "}, headers=h).status_code == 400
    assert client.patch(f"{A}/vault/files/{f['id']}", json={"name": None}, headers=h).status_code == 400
    assert client.patch(f"{A}/vault/files/{f['id']}", json={"category": "Secrets"}, headers=h).status_code == 400
    assert client.patch(f"{A}/vault/files/{f['id']}", json={"folderId": "9b2f2a0e-0000-4000-8000-000000000000"}, headers=h).status_code == 404
    assert client.patch(f"{A}/vault/files/{f['id']}", json={"name": "a/b\\c.pdf"}, headers=h).json()["name"] == "c.pdf"    # no path tricks
    acts = [a["action"] for a in client.get(f"{A}/vault/files/{f['id']}/activity", headers=h).json()["items"]]
    assert {"renamed", "moved", "categorised", "uploaded"} <= set(acts)


def test_notes_and_favourites(client):
    _, h = signup(client)
    f = up(client, h).json()
    n = client.post(f"{A}/vault/files/{f['id']}/notes", json={"text": "Original is with my brother."}, headers=h)
    assert n.status_code == 201
    assert [x["text"] for x in client.get(f"{A}/vault/files/{f['id']}/notes", headers=h).json()["items"]] == ["Original is with my brother."]
    assert client.get(f"{A}/vault/files/{f['id']}", headers=h).json()["noteCount"] == 1
    assert client.post(f"{A}/vault/files/{f['id']}/notes", json={"text": "x" * 2001}, headers=h).status_code == 400
    assert client.delete(f"{A}/vault/files/{f['id']}/notes/{n.json()['id']}", headers=h).status_code == 204
    assert client.delete(f"{A}/vault/files/{f['id']}/notes/{n.json()['id']}", headers=h).status_code == 404
    assert client.put(f"{A}/vault/files/{f['id']}/favourite", json={"favourite": True}, headers=h).status_code == 204
    assert client.get(f"{A}/vault/files/{f['id']}", headers=h).json()["favourite"] is True


# ---------------------------------------------------------------------------------------------- trash
def test_trash_restore_and_delete_forever_remove_the_stored_original(client, storage):
    _, h = signup(client)
    db = client.app.state.ctx.db
    f = up(client, h).json()
    path = db.one("select storage_path from app.vault_files where id = %s", [f["id"]])["storage_path"]
    assert client.delete(f"{A}/vault/files/{f['id']}?permanent=true", headers=h).status_code == 422             # not in the Trash yet
    assert client.delete(f"{A}/vault/files/{f['id']}", headers=h).status_code == 204
    assert client.delete(f"{A}/vault/files/{f['id']}", headers=h).status_code == 204                             # already there: fine
    assert path in storage.objects                                                                               # still kept while in the Trash
    assert client.get(f"{A}/vault/files/{f['id']}/link", headers=h).status_code == 200
    assert client.patch(f"{A}/vault/files/{f['id']}", json={"name": "x"}, headers=h).status_code == 404
    assert client.post(f"{A}/vault/files/{f['id']}/notes", json={"text": "x"}, headers=h).status_code == 422
    assert client.post(f"{A}/vault/files/{f['id']}/restore", headers=h).status_code == 204
    assert files(client, h)["total"] == 1
    client.delete(f"{A}/vault/files/{f['id']}", headers=h)
    assert client.delete(f"{A}/vault/files/{f['id']}?permanent=true", headers=h).status_code == 204
    assert path not in storage.objects and client.get(f"{A}/vault/files/{f['id']}", headers=h).status_code == 404   # gone from storage AND the database


def test_a_failed_delete_keeps_the_file_so_it_can_be_tried_again(pg_url):
    st = MemoryStorage()
    with TestClient(create_app(make_settings(pg_url), engine=FakeEngine(), storage=st)) as c:
        _, h = signup(c)
        f = up(c, h).json()
        c.delete(f"{A}/vault/files/{f['id']}", headers=h)
        st.fail_delete = True
        assert c.delete(f"{A}/vault/files/{f['id']}?permanent=true", headers=h).status_code == 503
        assert c.delete(f"{A}/vault/files-trash", headers=h).status_code == 503
        assert c.get(f"{A}/vault/files/{f['id']}", headers=h).status_code == 200 and len(st.objects) == 1
        st.fail_delete = False
        assert c.delete(f"{A}/vault/files-trash", headers=h).json() == {"deleted": 1} and not st.objects


def test_the_trash_empties_itself_after_the_set_number_of_days(client, storage):
    from app.docs_service import purge_expired
    _, h = signup(client)
    db = client.app.state.ctx.db
    old, recent = up(client, h, name="old.pdf").json()["id"], up(client, h, name="recent.pdf").json()["id"]
    paths = {i: db.one("select storage_path from app.vault_files where id = %s", [i])["storage_path"] for i in (old, recent)}
    for i in (old, recent):
        client.delete(f"{A}/vault/files/{i}", headers=h)
    db.run("update app.vault_files set trashed_at = now() - interval '31 days' where id = %s", [old])
    db.run("update app.vault_files set trashed_at = now() - interval '29 days' where id = %s", [recent])
    assert purge_expired(db, client.app.state.ctx.settings.docs, storage)["vault_files"] >= 1
    assert paths[old] not in storage.objects and paths[recent] in storage.objects
    assert client.get(f"{A}/vault/files/{old}", headers=h).status_code == 404 and client.get(f"{A}/vault/files/{recent}", headers=h).status_code == 200


# ---------------------------------------------------------------------------------------------- folders
def test_folders(client):
    _, h = signup(client)
    f1 = client.post(f"{A}/vault/folders", json={"name": "  Tax  "}, headers=h)
    assert f1.status_code == 201 and f1.json()["name"] == "Tax" and f1.json()["color"] == "#0ea5e9" and f1.json()["fileCount"] == 0
    assert client.post(f"{A}/vault/folders", json={"name": "TAX"}, headers=h).status_code == 409                 # names are unique, any case
    assert client.post(f"{A}/vault/folders", json={}, headers=h).status_code == 400
    assert client.post(f"{A}/vault/folders", json={"name": "x" * 61}, headers=h).status_code == 400
    assert client.post(f"{A}/vault/folders", json={"name": "Bad", "color": "red"}, headers=h).status_code == 400
    fid = f1.json()["id"]
    up(client, h, folderId=fid)
    r = client.patch(f"{A}/vault/folders/{fid}", json={"name": "Taxes", "color": "#112233"}, headers=h)
    assert r.status_code == 200 and r.json() == {"id": fid, "name": "Taxes", "color": "#112233", "fileCount": 1}
    other = client.post(f"{A}/vault/folders", json={"name": "Family"}, headers=h).json()["id"]
    assert client.patch(f"{A}/vault/folders/{other}", json={"name": "taxes"}, headers=h).status_code == 409
    assert [x["name"] for x in client.get(f"{A}/vault/folders", headers=h).json()["items"]] == ["Family", "Taxes"]
    assert client.delete(f"{A}/vault/folders/{fid}", headers=h).status_code == 204
    kept = files(client, h)
    assert kept["total"] == 1 and kept["items"][0]["folderId"] is None                                           # the file survives its folder
    assert client.delete(f"{A}/vault/folders/{fid}", headers=h).status_code == 404


# ---------------------------------------------------------------------------------------------- privacy
def test_one_users_files_are_invisible_to_another(client, storage):
    _, a = signup(client)
    _, b = signup(client)
    f = up(client, a, name="secret.pdf").json()["id"]
    folder = client.post(f"{A}/vault/folders", json={"name": "Mine"}, headers=a).json()["id"]
    assert files(client, b)["total"] == 0 and client.get(f"{A}/vault/folders", headers=b).json()["items"] == []
    for method, path, body in (("get", f"/vault/files/{f}", None), ("get", f"/vault/files/{f}/link", None), ("get", f"/vault/files/{f}/text", None),
                               ("patch", f"/vault/files/{f}", {"name": "mine"}), ("put", f"/vault/files/{f}/favourite", {"favourite": True}),
                               ("delete", f"/vault/files/{f}", None), ("post", f"/vault/files/{f}/restore", None), ("get", f"/vault/files/{f}/notes", None),
                               ("post", f"/vault/files/{f}/notes", {"text": "hi"}), ("get", f"/vault/files/{f}/activity", None),
                               ("patch", f"/vault/folders/{folder}", {"name": "x"}), ("delete", f"/vault/folders/{folder}", None)):
        r = client.request(method, A + path, headers=b, **({"json": body} if body else {}))
        assert r.status_code == 404, (method, path, r.status_code)
    assert up(client, b, folderId=folder).status_code == 404                                                     # cannot file into someone else's folder
    assert client.delete(f"{A}/vault/files-trash", headers=b).json() == {"deleted": 0}
    assert client.get(f"{A}/vault/files/{f}", headers=a).json()["name"] == "secret.pdf" and len(storage.objects) >= 1
    assert client.get(f"{A}/vault/files").status_code == 401
