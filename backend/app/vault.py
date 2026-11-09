"""Legal Vault, part A: what the user saves from the app (a chat answer, a document analysis, later a case brief).

An item is a SNAPSHOT: it is readable after the chat or the analysis it came from is deleted or has expired. Saving the same thing twice
is one item. Deleting moves an item to the Trash, which empties itself after VAULT_TRASH_DAYS. Everything here is scoped to one user:
an id that is not theirs is simply "not found".
"""
from __future__ import annotations

import logging
from typing import Literal

from psycopg.types.json import Jsonb

from .config import DocSettings
from .db import Database
from .errors import ApiError, not_found
from .users_repo import iso

log = logging.getLogger("legalmate.vault")

KINDS = ("answer", "analysis", "brief", "calculation")
SORTS = {"updated_desc": "i.updated_at desc", "updated_asc": "i.updated_at asc", "name_asc": "lower(i.title) asc, i.updated_at desc",
         "name_desc": "lower(i.title) desc, i.updated_at desc"}
LIST_COLS = ("i.id, i.kind, i.title, i.summary, i.meta, i.source_id, i.favourite, i.trashed_at, i.created_at, i.updated_at, "
             "(select count(*) from app.vault_notes n where n.item_id = i.id) as note_count")
ITEM_COLS = LIST_COLS + ", i.content"


def _like(q: str) -> str:
    return "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def item_out(r: dict, *, content: bool = False) -> dict:
    meta = r.get("meta") or {}
    out = {"id": str(r["id"]), "kind": r["kind"], "title": r["title"], "summary": r["summary"], "tag": meta.get("tag"), "risk": meta.get("risk"),
           "language": meta.get("language"), "confidence": meta.get("confidence"), "conversationId": meta.get("conversationId"),
           "sourceId": str(r["source_id"]) if r.get("source_id") else None, "favourite": r["favourite"], "noteCount": int(r.get("note_count") or 0),
           "savedAt": iso(r["created_at"]), "updatedAt": iso(r["updated_at"]), "trashedAt": iso(r["trashed_at"])}
    if content:
        out["content"] = r["content"]
    return out


def _log(db: Database, user_id: str, item_id: str, action: str) -> None:
    db.run("insert into app.vault_activity (item_id, user_id, action) values (%s, %s, %s)", [item_id, user_id, action])


def _check_room(db: Database, user_id: str, cfg: DocSettings) -> None:
    if cfg.vault_max_items > 0:
        n = db.one("select count(*) as n from app.vault_items where user_id = %s", [user_id])["n"]
        if n >= cfg.vault_max_items:
            raise ApiError(422, "QUOTA_EXCEEDED", f"Your Vault holds {n} items, which is the limit. Delete some items to save more.")


def _store(db: Database, cfg: DocSettings, user_id: str, kind: str, source_id: str, *, title: str, summary: str, content: dict, meta: dict) -> dict:
    """Inserts the item, or (already saved) returns the existing one and takes it out of the Trash. -> {"id", "alreadySaved"}"""
    existing = db.one("select id, trashed_at from app.vault_items where user_id = %s and kind = %s and source_id = %s", [user_id, kind, source_id])
    if existing:
        if existing["trashed_at"] is not None:
            db.run("update app.vault_items set trashed_at = null, updated_at = now() where id = %s", [existing["id"]])
            _log(db, user_id, str(existing["id"]), "restored")
        return {"id": str(existing["id"]), "alreadySaved": existing["trashed_at"] is None}
    _check_room(db, user_id, cfg)
    row = db.one("insert into app.vault_items (user_id, kind, title, summary, content, meta, source_id) values (%s, %s, %s, %s, %s, %s, %s) "
                 "on conflict (user_id, kind, source_id) where source_id is not null do nothing returning id",
                 [user_id, kind, title[:160], summary[:240], Jsonb(content), Jsonb(meta), source_id])
    if row is None:                                                                   # saved at the same moment from another tab
        row = db.one("select id from app.vault_items where user_id = %s and kind = %s and source_id = %s", [user_id, kind, source_id])
        return {"id": str(row["id"]), "alreadySaved": True}
    _log(db, user_id, str(row["id"]), "saved")
    return {"id": str(row["id"]), "alreadySaved": False}


# ------------------------------------------------------------------------------------------------ saving
def save_answer(db: Database, cfg: DocSettings, user_id: str, message_id: str) -> dict:
    msg = db.one("select m.id, m.conversation_id, m.seq, m.kind, m.payload, m.content, c.title as conv_title, c.tag as conv_tag "
                 "from app.messages m join app.conversations c on c.id = m.conversation_id "
                 "where m.id = %s and m.user_id = %s and m.role = 'assistant'", [message_id, user_id])
    if msg is None:
        raise not_found("That answer")
    if msg["kind"] != "answer" or not msg["payload"]:
        raise ApiError(422, "UNPROCESSABLE", "Only an answer with sources can be saved to the Vault.")
    q = db.one("select content from app.messages where conversation_id = %s and seq < %s and role = 'user' order by seq desc limit 1", [msg["conversation_id"], msg["seq"]])
    question = (q or {}).get("content") or ""
    payload = {k: v for k, v in msg["payload"].items() if k not in ("feedback", "id")}
    first_line = " ".join(question.split())
    title = first_line[:100] or msg["conv_title"] or "Saved answer"
    summary = " ".join((msg["content"] or "").split())[:240]
    conf = (payload.get("confidence") or {}).get("score") if isinstance(payload.get("confidence"), dict) else None
    meta = {"tag": msg["conv_tag"], "language": payload.get("language"), "conversationId": str(msg["conversation_id"]), "confidence": conf,
            "sources": len(payload.get("sources") or [])}
    return _store(db, cfg, user_id, "answer", str(msg["id"]), title=title, summary=summary, content={"question": question, "answer": payload}, meta=meta)


def save_analysis(db: Database, cfg: DocSettings, user_id: str, analysis_id: str) -> dict:
    row = db.one("select id, status, result from app.analyses where id = %s and user_id = %s", [analysis_id, user_id])
    if row is None:
        raise not_found("That analysis")
    if row["status"] != "completed" or not row["result"]:
        raise ApiError(422, "UNPROCESSABLE", "The analysis is not finished yet. Please save it when it is complete.")
    res = row["result"]
    doc = res.get("document") or {}
    name = doc.get("name") or "Document analysis"
    meta = {"tag": doc.get("documentType"), "risk": (res.get("overallRisk") or {}).get("level"), "language": None,
            "clauses": (res.get("counts") or {}).get("clauses")}
    summary = " ".join(str(res.get("summary") or "").split())
    return _store(db, cfg, user_id, "analysis", str(row["id"]), title=name, summary=summary, content={"id": str(row["id"]), "status": "completed", **res}, meta=meta)


def save_calculation(db: Database, cfg: DocSettings, user_id: str, kind: str, name: str, inputs: dict, result: dict) -> dict:
    """A calculation is saved as it was (inputs and result); each save is its own item, so the same calculation can be kept with different numbers."""
    _check_room(db, user_id, cfg)
    headline = result.get("text") or (f"PKR {round(result['total']):,}" if result.get("total") is not None else "")
    title = f"{name}: {headline}".strip(": ")
    summary = "; ".join(f"{r['label']}: {r['value']}" for r in (result.get("rows") or [])[:3])
    meta = {"tag": name, "risk": None, "language": "en", "calcType": kind, "confidence": result.get("confidence")}
    row = db.one("insert into app.vault_items (user_id, kind, title, summary, content, meta) values (%s, 'calculation', %s, %s, %s, %s) returning id",
                 [user_id, title[:160], summary[:240], Jsonb({"type": kind, "inputs": inputs, "result": result}), Jsonb(meta)])
    _log(db, user_id, str(row["id"]), "saved")
    return {"id": str(row["id"]), "alreadySaved": False}


# ------------------------------------------------------------------------------------------------ reading
Category = Literal["all", "answer", "analysis", "brief", "calculation", "favourites", "trash"]


def list_items(db: Database, cfg: DocSettings, user_id: str, *, category: str = "all", q: str = "", sort: str = "updated_desc", page: int = 1,
               page_size: int | None = None) -> dict:
    size = page_size or cfg.vault_page_size
    where, params = ["i.user_id = %s"], [user_id]
    where.append("i.trashed_at is not null" if category == "trash" else "i.trashed_at is null")
    if category in KINDS:
        where.append("i.kind = %s")
        params.append(category)
    elif category == "favourites":
        where.append("i.favourite")
    if q.strip():
        where.append("(i.title ilike %s or i.summary ilike %s or i.content->>'question' ilike %s)")
        params += [_like(q)] * 3
    cond = " and ".join(where)
    rows, (total,), (c,) = db.batch([
        (f"select {LIST_COLS} from app.vault_items i where {cond} order by {SORTS.get(sort, SORTS['updated_desc'])} limit %s offset %s", [*params, size, (page - 1) * size]),
        (f"select count(*) as n from app.vault_items i where {cond}", params),
        (COUNTS_SQL, [user_id])])
    return {"items": [item_out(r) for r in rows], "total": total["n"], "page": page, "pageSize": size, "counts": counts_out(c)}


COUNTS_SQL = ("select count(*) filter (where trashed_at is null) as every, count(*) filter (where trashed_at is null and kind = 'answer') as answers, "
              "count(*) filter (where trashed_at is null and kind = 'analysis') as analyses, count(*) filter (where trashed_at is null and kind = 'brief') as briefs, count(*) filter (where trashed_at is null and kind = 'calculation') as calcs, "
              "count(*) filter (where trashed_at is null and favourite) as favourites, count(*) filter (where trashed_at is not null) as trash "
              "from app.vault_items where user_id = %s")


def counts_out(c: dict) -> dict:
    return {"all": c["every"], "answer": c["answers"], "analysis": c["analyses"], "brief": c["briefs"], "calculation": c["calcs"], "favourites": c["favourites"], "trash": c["trash"]}


def stats(db: Database, user_id: str) -> dict:
    return {"counts": counts_out(db.one(COUNTS_SQL, [user_id]))}


def get_item(db: Database, user_id: str, item_id: str) -> dict:
    r = db.one(f"select {ITEM_COLS} from app.vault_items i where i.id = %s and i.user_id = %s", [item_id, user_id])
    if r is None:
        raise not_found("That saved item")
    return item_out(r, content=True)


def _live(db: Database, user_id: str, item_id: str) -> dict:
    r = db.one("select id, trashed_at from app.vault_items where id = %s and user_id = %s", [item_id, user_id])
    if r is None:
        raise not_found("That saved item")
    return r


# ------------------------------------------------------------------------------------------------ changing
def rename(db: Database, user_id: str, item_id: str, title: str) -> dict:
    row = db.one("update app.vault_items set title = %s, updated_at = now() where id = %s and user_id = %s and trashed_at is null returning id", [title, item_id, user_id])
    if row is None:
        raise not_found("That saved item")
    _log(db, user_id, item_id, "renamed")
    return get_item(db, user_id, item_id)


def set_favourite(db: Database, user_id: str, item_id: str, favourite: bool) -> None:
    if db.run("update app.vault_items set favourite = %s, updated_at = now() where id = %s and user_id = %s and trashed_at is null", [favourite, item_id, user_id]) == 0:
        raise not_found("That saved item")
    _log(db, user_id, item_id, "favourited" if favourite else "unfavourited")


def trash(db: Database, user_id: str, item_id: str) -> None:
    if db.run("update app.vault_items set trashed_at = now() where id = %s and user_id = %s and trashed_at is null", [item_id, user_id]) == 0:
        _live(db, user_id, item_id)                                                      # 404 if it is not theirs; already in the Trash is fine
        return
    _log(db, user_id, item_id, "trashed")


def restore(db: Database, user_id: str, item_id: str) -> None:
    if db.run("update app.vault_items set trashed_at = null, updated_at = now() where id = %s and user_id = %s and trashed_at is not null", [item_id, user_id]) == 0:
        _live(db, user_id, item_id)
        return
    _log(db, user_id, item_id, "restored")


def delete_forever(db: Database, user_id: str, item_id: str) -> None:
    r = _live(db, user_id, item_id)
    if r["trashed_at"] is None:
        raise ApiError(422, "UNPROCESSABLE", "Move the item to the Trash first. Items in the Trash can be deleted for good.")
    db.run("delete from app.vault_items where id = %s and user_id = %s", [item_id, user_id])


def empty_trash(db: Database, user_id: str) -> int:
    return db.run("delete from app.vault_items where user_id = %s and trashed_at is not null", [user_id])


# ------------------------------------------------------------------------------------------------ notes and activity
def list_notes(db: Database, user_id: str, item_id: str) -> list[dict]:
    _live(db, user_id, item_id)
    return [{"id": str(n["id"]), "text": n["text"], "createdAt": iso(n["created_at"])}
            for n in db.all("select id, text, created_at from app.vault_notes where item_id = %s and user_id = %s order by created_at desc", [item_id, user_id])]


def add_note(db: Database, cfg: DocSettings, user_id: str, item_id: str, text: str) -> dict:
    r = _live(db, user_id, item_id)
    if r["trashed_at"] is not None:
        raise ApiError(422, "UNPROCESSABLE", "Restore the item from the Trash before adding a note.")
    n = db.one("select count(*) as n from app.vault_notes where item_id = %s", [item_id])["n"]
    if n >= cfg.vault_max_notes:
        raise ApiError(422, "QUOTA_EXCEEDED", f"An item can have up to {cfg.vault_max_notes} notes.")
    row = db.one("insert into app.vault_notes (item_id, user_id, text) values (%s, %s, %s) returning id, text, created_at", [item_id, user_id, text])
    db.run("update app.vault_items set updated_at = now() where id = %s", [item_id])
    _log(db, user_id, item_id, "noted")
    return {"id": str(row["id"]), "text": row["text"], "createdAt": iso(row["created_at"])}


def delete_note(db: Database, user_id: str, item_id: str, note_id: str) -> None:
    if db.run("delete from app.vault_notes where id = %s and item_id = %s and user_id = %s", [note_id, item_id, user_id]) == 0:
        raise not_found("That note")


def list_activity(db: Database, user_id: str, item_id: str) -> list[dict]:
    _live(db, user_id, item_id)
    return [{"action": a["action"], "createdAt": iso(a["created_at"])}
            for a in db.all("select action, created_at from app.vault_activity where item_id = %s and user_id = %s order by created_at desc, id desc limit 100", [item_id, user_id])]
