"""Legal Vault, part B: the user's own files (contracts, notices, court papers, photos), kept as originals in private storage.

Rows in `app.vault_files` describe a file (name, folder, category, size, the text read from it for search); the bytes live in the private
Supabase bucket under a name WE generate. A user only ever gets a short-lived signed link, made after the file was proven to be theirs.
Everything is scoped to one user: an id that is not theirs is simply "not found". Independent of part A (saved answers and analyses).
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import replace

from .config import DocSettings
from .db import Database
from .errors import ApiError, not_found
from .extract import ExtractError, check_image, extract, sniff
from .storage import StorageError
from .users_repo import iso

log = logging.getLogger("legalmate.vault.files")

CATEGORIES = ("Contracts", "Notices", "Court Documents", "Property", "Personal", "Family", "Other")
CONTENT_TYPES = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 "jpg": "image/jpeg", "png": "image/png"}
SORTS = {"updated_desc": "f.updated_at desc", "updated_asc": "f.updated_at asc", "name_asc": "lower(f.name) asc, f.updated_at desc",
         "name_desc": "lower(f.name) desc, f.updated_at desc", "size_desc": "f.size_bytes desc, f.updated_at desc"}
COLS = ("f.id, f.name, f.file_type, f.size_bytes, f.pages, f.category, f.folder_id, fo.name as folder_name, f.favourite, f.text_status, f.trashed_at, "
        "f.created_at, f.updated_at, (f.text <> '') as has_text, (select count(*) from app.vault_file_notes n where n.file_id = f.id) as note_count")
FROM = "from app.vault_files f left join app.vault_folders fo on fo.id = f.folder_id"
TEXT_PREVIEW_CHARS = 60_000
_CTRL = re.compile(r"[\x00-\x1f\x7f/\\]")
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def file_out(r: dict) -> dict:
    return {"id": str(r["id"]), "name": r["name"], "fileType": r["file_type"], "category": r["category"], "folderId": str(r["folder_id"]) if r["folder_id"] else None,
            "folderName": r.get("folder_name"), "sizeBytes": int(r["size_bytes"]), "pages": r["pages"], "favourite": r["favourite"], "noteCount": int(r.get("note_count") or 0),
            "textStatus": r["text_status"], "hasText": bool(r.get("has_text")), "uploadedAt": iso(r["created_at"]), "updatedAt": iso(r["updated_at"]),
            "trashedAt": iso(r["trashed_at"])}


def clean_name(raw: str | None, fallback: str = "file") -> str:
    name = _CTRL.sub("_", (raw or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]).strip()
    return (name or fallback)[:160]


def download_name(name: str, file_type: str) -> str:
    return name if name.lower().endswith("." + file_type) or (file_type == "jpg" and name.lower().endswith(".jpeg")) else f"{name}.{file_type}"


def _storage(state):
    if state.storage is None:
        raise ApiError(503, "UNAVAILABLE", "File storage is not available on this server right now. Please try again later.")
    return state.storage


def _log(db: Database, user_id: str, file_id: str, action: str) -> None:
    db.run("insert into app.vault_file_activity (file_id, user_id, action) values (%s, %s, %s)", [file_id, user_id, action])


def usage(db: Database, user_id: str) -> tuple[int, int]:
    r = db.one("select coalesce(sum(size_bytes), 0) as used, count(*) as n from app.vault_files where user_id = %s", [user_id])
    return int(r["used"]), int(r["n"])


def _row(db: Database, user_id: str, file_id: str, cols: str = "id, name, file_type, storage_path, trashed_at, text_status") -> dict:
    r = db.one(f"select {cols} from app.vault_files where id = %s and user_id = %s", [file_id, user_id])
    if r is None:
        raise not_found("That file")
    return r


def _folder(db: Database, user_id: str, folder_id: str) -> dict:
    f = db.one("select id, name, color from app.vault_folders where id = %s and user_id = %s", [folder_id, user_id])
    if f is None:
        raise not_found("That folder")
    return f


# ------------------------------------------------------------------------------------------------ upload
def upload(state, user_id: str, data: bytes, filename: str | None, folder_id: str | None, category: str | None) -> dict:
    cfg, db = state.settings.docs, state.db
    storage = _storage(state)
    if not data:
        raise ApiError(400, "VALIDATION_ERROR", "The file is empty.", {"field": "file"})
    if len(data) > cfg.max_upload_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", f"This file is larger than {cfg.max_upload_mb} MB.")
    category = category or "Other"
    if category not in CATEGORIES:
        raise ApiError(400, "VALIDATION_ERROR", f"category: choose one of {', '.join(CATEGORIES)}.", {"field": "category"})
    try:
        kind = sniff(data)
        if kind in ("jpg", "png"):
            check_image(data, cfg)
    except ExtractError as e:
        raise ApiError(e.status, e.code, e.message)
    if folder_id:
        _folder(db, user_id, folder_id)
    used, n = usage(db, user_id)
    quota = cfg.vault_quota_mb * 1024 * 1024
    if used + len(data) > quota:
        raise ApiError(422, "QUOTA_EXCEEDED", f"There is not enough space in your Vault: {used / 1048576:.1f} MB of {cfg.vault_quota_mb} MB is used and this file is "
                                              f"{len(data) / 1048576:.1f} MB. Delete some files and empty the Trash to make room.")
    if cfg.vault_max_files > 0 and n >= cfg.vault_max_files:
        raise ApiError(422, "QUOTA_EXCEEDED", f"Your Vault holds {n} files, which is the limit. Delete some files to add more.")

    text, pages, status = "", 1, "none"
    if kind in ("pdf", "docx"):                                       # text for search, without OCR (a scan is read afterwards, in the background)
        try:
            res = extract(data, replace(cfg, ocr_enabled=False, max_pages=10_000, max_text_chars=cfg.max_text_chars))
            text, pages, status = res.text, res.pages, "ready"
        except ExtractError as e:
            if e.code == "NO_TEXT" and kind == "pdf" and cfg.ocr_enabled:
                status = "pending"
    elif cfg.ocr_enabled:
        status = "pending"

    path = f"{user_id}/{uuid.uuid4().hex}.{kind}"
    try:
        storage.upload(path, data, CONTENT_TYPES[kind])
    except StorageError:
        log.exception("could not store a vault file")
        raise ApiError(503, "UNAVAILABLE", "The file could not be stored right now. Please try again.")
    try:
        row = db.one("insert into app.vault_files (user_id, folder_id, name, file_type, size_bytes, pages, category, storage_path, text, text_status) "
                     "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
                     [user_id, folder_id or None, clean_name(filename), kind, len(data), pages, category, path, text, status])
    except Exception:
        try:
            storage.delete([path])                                    # no orphan object when the row could not be written
        except StorageError:
            log.warning("could not remove the object of a failed upload: %s", path)
        raise
    fid = str(row["id"])
    _log(db, user_id, fid, "uploaded")
    if status == "pending":
        try:
            state.vault_executor.submit(read_text, state, fid, data)
        except Exception:                                             # noqa: BLE001 - the file is stored; only its search text is missing
            db.run("update app.vault_files set text_status = 'none' where id = %s", [fid])
    return get_file(db, user_id, fid)


def read_text(state, file_id: str, data: bytes) -> None:
    """Background: reads a photo or a scanned PDF (OCR) so it can be found by its contents. Never raises."""
    db = state.db
    try:
        res = extract(data, state.settings.docs)
        db.run("update app.vault_files set text = %s, text_status = 'ready', pages = %s where id = %s and text_status = 'pending'", [res.text, res.pages, file_id])
    except ExtractError:
        db.run("update app.vault_files set text_status = 'none' where id = %s and text_status = 'pending'", [file_id])
    except Exception:                                                  # noqa: BLE001
        log.exception("could not read vault file %s", file_id)
        try:
            db.run("update app.vault_files set text_status = 'none' where id = %s and text_status = 'pending'", [file_id])
        except Exception:                                              # noqa: BLE001
            pass


# ------------------------------------------------------------------------------------------------ reading
def counts_sql() -> str:
    cats = ", ".join(f"count(*) filter (where trashed_at is null and category = '{c}') as c{i}" for i, c in enumerate(CATEGORIES))
    return ("select count(*) filter (where trashed_at is null) as every, count(*) filter (where trashed_at is null and favourite) as favourites, "
            f"count(*) filter (where trashed_at is not null) as trash, {cats} from app.vault_files where user_id = %s")


def counts_out(c: dict) -> dict:
    out = {"all": c["every"], "favourites": c["favourites"], "trash": c["trash"]}
    out.update({cat: c[f"c{i}"] for i, cat in enumerate(CATEGORIES)})
    return out


def storage_out(cfg: DocSettings, used: int) -> dict:
    return {"usedBytes": used, "quotaBytes": cfg.vault_quota_mb * 1024 * 1024}


def stats(db: Database, cfg: DocSettings, user_id: str) -> dict:
    used, _ = usage(db, user_id)
    return {"storage": storage_out(cfg, used), "files": counts_out(db.one(counts_sql(), [user_id]))}


def list_files(db: Database, cfg: DocSettings, user_id: str, *, category: str = "all", folder_id: str | None = None, q: str = "",
               sort: str = "updated_desc", page: int = 1, page_size: int = 24) -> dict:
    where, params = ["f.user_id = %s"], [user_id]
    where.append("f.trashed_at is not null" if category == "trash" else "f.trashed_at is null")
    if category in CATEGORIES:
        where.append("f.category = %s")
        params.append(category)
    elif category == "favourites":
        where.append("f.favourite")
    if folder_id:
        where.append("f.folder_id = %s")
        params.append(folder_id)
    if q.strip():
        like = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where.append("(f.name ilike %s or f.text ilike %s)")
        params += [like, like]
    cond = " and ".join(where)
    rows, (total,), (c,), (u,) = db.batch([
        (f"select {COLS} {FROM} where {cond} order by {SORTS.get(sort, SORTS['updated_desc'])} limit %s offset %s", [*params, page_size, (page - 1) * page_size]),
        (f"select count(*) as n {FROM} where {cond}", params),
        (counts_sql(), [user_id]),
        ("select coalesce(sum(size_bytes), 0) as used from app.vault_files where user_id = %s", [user_id])])
    return {"items": [file_out(r) for r in rows], "total": total["n"], "page": page, "pageSize": page_size, "counts": counts_out(c),
            "storage": storage_out(cfg, int(u["used"]))}


def get_file(db: Database, user_id: str, file_id: str) -> dict:
    r = db.one(f"select {COLS} {FROM} where f.id = %s and f.user_id = %s", [file_id, user_id])
    if r is None:
        raise not_found("That file")
    return file_out(r)


def link(state, user_id: str, file_id: str, download: bool) -> dict:
    cfg = state.settings.docs
    r = _row(state.db, user_id, file_id)
    try:
        url = _storage(state).signed_url(r["storage_path"], cfg.vault_link_seconds, download_name(r["name"], r["file_type"]) if download else None)
    except StorageError:
        log.exception("could not make a link for vault file %s", file_id)
        raise ApiError(503, "UNAVAILABLE", "The file could not be opened right now. Please try again.")
    if download:
        _log(state.db, user_id, file_id, "downloaded")
    return {"url": url, "expiresIn": cfg.vault_link_seconds}


def read_file_text(db: Database, user_id: str, file_id: str) -> dict:
    r = _row(db, user_id, file_id, "text, text_status")
    text = r["text"] or ""
    return {"text": text[:TEXT_PREVIEW_CHARS], "truncated": len(text) > TEXT_PREVIEW_CHARS, "status": r["text_status"]}


# ------------------------------------------------------------------------------------------------ changing
def patch(db: Database, user_id: str, file_id: str, changes: dict) -> dict:
    """changes: any of name, folderId (None = no folder), category; only the keys present are applied."""
    r = _row(db, user_id, file_id)
    if r["trashed_at"] is not None:
        raise not_found("That file")
    sets, params, actions = [], [], []
    if "name" in changes:
        name = clean_name(changes["name"], fallback="")
        if not name:
            raise ApiError(400, "VALIDATION_ERROR", "name: please enter a name.", {"field": "name"})
        sets.append("name = %s"), params.append(name), actions.append("renamed")
    if "folderId" in changes:
        fid = changes["folderId"]
        if fid:
            _folder(db, user_id, fid)
        sets.append("folder_id = %s"), params.append(fid or None), actions.append("moved")
    if "category" in changes:
        if changes["category"] not in CATEGORIES:
            raise ApiError(400, "VALIDATION_ERROR", f"category: choose one of {', '.join(CATEGORIES)}.", {"field": "category"})
        sets.append("category = %s"), params.append(changes["category"]), actions.append("categorised")
    if sets:
        db.run(f"update app.vault_files set {', '.join(sets)}, updated_at = now() where id = %s and user_id = %s", [*params, file_id, user_id])
        for a in actions:
            _log(db, user_id, file_id, a)
    return get_file(db, user_id, file_id)


def set_favourite(db: Database, user_id: str, file_id: str, favourite: bool) -> None:
    if db.run("update app.vault_files set favourite = %s, updated_at = now() where id = %s and user_id = %s and trashed_at is null", [favourite, file_id, user_id]) == 0:
        raise not_found("That file")
    _log(db, user_id, file_id, "favourited" if favourite else "unfavourited")


def trash(db: Database, user_id: str, file_id: str) -> None:
    if db.run("update app.vault_files set trashed_at = now() where id = %s and user_id = %s and trashed_at is null", [file_id, user_id]) == 0:
        _row(db, user_id, file_id)
        return
    _log(db, user_id, file_id, "trashed")


def restore(db: Database, user_id: str, file_id: str) -> None:
    if db.run("update app.vault_files set trashed_at = null, updated_at = now() where id = %s and user_id = %s and trashed_at is not null", [file_id, user_id]) == 0:
        _row(db, user_id, file_id)
        return
    _log(db, user_id, file_id, "restored")


def _remove(state, rows: list[dict]) -> None:
    """Deletes the stored objects, then the rows. If storage refuses, the rows stay so the user can try again (no orphan, no lost file)."""
    try:
        for i in range(0, len(rows), 100):
            _storage(state).delete([r["storage_path"] for r in rows[i:i + 100]])
    except StorageError:
        log.exception("could not delete vault objects")
        raise ApiError(503, "UNAVAILABLE", "The file could not be deleted right now. Please try again.")
    state.db.run("delete from app.vault_files where id = any(%s::uuid[])", [[str(r["id"]) for r in rows]])


def delete_forever(state, user_id: str, file_id: str) -> None:
    r = _row(state.db, user_id, file_id)
    if r["trashed_at"] is None:
        raise ApiError(422, "UNPROCESSABLE", "Move the file to the Trash first. Files in the Trash can be deleted for good.")
    _remove(state, [r])


def empty_trash(state, user_id: str) -> int:
    rows = state.db.all("select id, storage_path from app.vault_files where user_id = %s and trashed_at is not null", [user_id])
    if rows:
        _remove(state, rows)
    return len(rows)


def purge_trash(db: Database, storage, cfg: DocSettings) -> int:
    """Files that have been in the Trash for VAULT_TRASH_DAYS: the stored object first, then the row. Best effort; what fails is tried again later."""
    if storage is None:
        return 0
    rows = db.all("select id, storage_path from app.vault_files where trashed_at is not null and trashed_at < now() - make_interval(days => %s) limit 200", [cfg.vault_trash_days])
    done = 0
    for i in range(0, len(rows), 50):
        batch = rows[i:i + 50]
        try:
            storage.delete([r["storage_path"] for r in batch])
        except StorageError:
            log.warning("could not purge %d vault object(s); will retry", len(batch), exc_info=True)
            continue
        done += db.run("delete from app.vault_files where id = any(%s::uuid[])", [[str(r["id"]) for r in batch]])
    return done


# ------------------------------------------------------------------------------------------------ notes and activity
def list_notes(db: Database, user_id: str, file_id: str) -> list[dict]:
    _row(db, user_id, file_id)
    return [{"id": str(n["id"]), "text": n["text"], "createdAt": iso(n["created_at"])}
            for n in db.all("select id, text, created_at from app.vault_file_notes where file_id = %s and user_id = %s order by created_at desc", [file_id, user_id])]


def add_note(db: Database, cfg: DocSettings, user_id: str, file_id: str, text: str) -> dict:
    r = _row(db, user_id, file_id)
    if r["trashed_at"] is not None:
        raise ApiError(422, "UNPROCESSABLE", "Restore the file from the Trash before adding a note.")
    if db.one("select count(*) as n from app.vault_file_notes where file_id = %s", [file_id])["n"] >= cfg.vault_max_notes:
        raise ApiError(422, "QUOTA_EXCEEDED", f"A file can have up to {cfg.vault_max_notes} notes.")
    row = db.one("insert into app.vault_file_notes (file_id, user_id, text) values (%s, %s, %s) returning id, text, created_at", [file_id, user_id, text])
    db.run("update app.vault_files set updated_at = now() where id = %s", [file_id])
    _log(db, user_id, file_id, "noted")
    return {"id": str(row["id"]), "text": row["text"], "createdAt": iso(row["created_at"])}


def delete_note(db: Database, user_id: str, file_id: str, note_id: str) -> None:
    if db.run("delete from app.vault_file_notes where id = %s and file_id = %s and user_id = %s", [note_id, file_id, user_id]) == 0:
        raise not_found("That note")


def list_activity(db: Database, user_id: str, file_id: str) -> list[dict]:
    _row(db, user_id, file_id)
    return [{"action": a["action"], "createdAt": iso(a["created_at"])}
            for a in db.all("select action, created_at from app.vault_file_activity where file_id = %s and user_id = %s order by created_at desc, id desc limit 100", [file_id, user_id])]


# ------------------------------------------------------------------------------------------------ folders
def list_folders(db: Database, user_id: str) -> list[dict]:
    rows = db.all("select fo.id, fo.name, fo.color, count(f.id) filter (where f.trashed_at is null) as n from app.vault_folders fo "
                  "left join app.vault_files f on f.folder_id = fo.id where fo.user_id = %s group by fo.id order by lower(fo.name)", [user_id])
    return [{"id": str(r["id"]), "name": r["name"], "color": r["color"], "fileCount": int(r["n"])} for r in rows]


def _folder_name(name: str) -> str:
    name = " ".join(_CTRL.sub(" ", name or "").split())
    if not name or len(name) > 60:
        raise ApiError(400, "VALIDATION_ERROR", "name: a folder name is 1 to 60 characters.", {"field": "name"})
    return name


def _color(color: str | None) -> str:
    if color and not _COLOR.match(color):
        raise ApiError(400, "VALIDATION_ERROR", "color: use a colour like #0ea5e9.", {"field": "color"})
    return color or "#0ea5e9"


def _name_taken() -> ApiError:
    return ApiError(409, "CONFLICT", "You already have a folder with that name.")


def create_folder(db: Database, cfg: DocSettings, user_id: str, name: str, color: str | None) -> dict:
    name, color = _folder_name(name), _color(color)
    if db.one("select count(*) as n from app.vault_folders where user_id = %s", [user_id])["n"] >= cfg.vault_max_folders:
        raise ApiError(422, "QUOTA_EXCEEDED", f"You can have up to {cfg.vault_max_folders} folders.")
    try:
        r = db.one("insert into app.vault_folders (user_id, name, color) values (%s, %s, %s) returning id", [user_id, name, color])
    except Exception as e:                                                     # the unique index on (user, lower(name))
        if "vault_folders_name_idx" in str(e):
            raise _name_taken()
        raise
    return {"id": str(r["id"]), "name": name, "color": color, "fileCount": 0}


def update_folder(db: Database, user_id: str, folder_id: str, name: str | None, color: str | None) -> dict:
    cur = _folder(db, user_id, folder_id)
    new_name, new_color = _folder_name(name) if name is not None else cur["name"], _color(color) if color is not None else cur["color"]
    try:
        db.run("update app.vault_folders set name = %s, color = %s where id = %s and user_id = %s", [new_name, new_color, folder_id, user_id])
    except Exception as e:
        if "vault_folders_name_idx" in str(e):
            raise _name_taken()
        raise
    return next(f for f in list_folders(db, user_id) if f["id"] == folder_id)


def delete_folder(db: Database, user_id: str, folder_id: str) -> None:
    _folder(db, user_id, folder_id)
    db.run("delete from app.vault_folders where id = %s and user_id = %s", [folder_id, user_id])                      # its files stay (folder_id becomes null)
