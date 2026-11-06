"""Conversations and messages in the database, and one chat turn: user message in, answer out, both stored.

`run_turn` is blocking (database + knowledge base + DeepSeek), so the router runs it on a worker thread. It does ALL the
persistence itself: if the browser disconnects half-way the answer is still saved and shows up when the chat is reopened.
"""
from __future__ import annotations

import logging
from typing import Callable

from psycopg.types.json import Jsonb

from .errors import ApiError, not_found
from .state import AppState
from .users_repo import engine_profile, iso

log = logging.getLogger("legalmate.chat")

TAG_ICON = {"Property Law": "home", "Family Law": "person", "Criminal Law": "doc", "Labour & Employment": "briefcase",
            "Contract Law": "file", "Consumer Rights": "message", "Constitutional Rights": "doc", "Civil Procedure": "file",
            "Cyber Law": "doc"}
# Starter cards of the chat screen: title and legal area are known without asking the model.
TOPICS = {"tenant-rights": ("Tenant rights in Pakistan", "Property Law"), "employment": ("Employment termination", "Labour & Employment"),
          "inheritance": ("Family inheritance", "Family Law"), "consumer": ("Consumer complaint", "Consumer Rights")}
CONV_COLS = "id, title, title_auto, tag, icon, preview, pinned, created_at, updated_at"
HISTORY_CHARS = 1200


def conv_out(r: dict) -> dict:
    return {"id": str(r["id"]), "title": r["title"], "tag": r["tag"], "icon": r["icon"], "preview": r["preview"],
            "pinned": r["pinned"], "updatedAt": iso(r["updated_at"])}


def msg_out(r: dict) -> dict:
    if r["role"] == "user":
        return {"id": str(r["id"]), "role": "user", "kind": "user", "content": r["content"],
                "attachmentIds": [str(a) for a in r["attachment_ids"]], "createdAt": iso(r["created_at"])}
    return {**(r["payload"] or {}), "id": str(r["id"]), "role": "assistant", "kind": r["kind"], "createdAt": iso(r["created_at"]),
            "feedback": r["feedback"]}


def get_conversation(state: AppState, user_id: str, conv_id: str) -> dict:
    row = state.db.one(f"select {CONV_COLS} from app.conversations where id = %s and user_id = %s", [conv_id, user_id])
    if row is None:
        raise not_found("That conversation")
    return row


def create_conversation(state: AppState, user_id: str, first_message: str, topic: str | None) -> dict:
    title, tag = TOPICS.get(topic or "", (None, "General"))
    if title is None:
        title = " ".join(first_message.split())[:48] or "New conversation"
    return state.db.one(
        f"insert into app.conversations (user_id, title, tag, icon, preview) values (%s, %s, %s, %s, %s) returning {CONV_COLS}",
        [user_id, title, tag, TAG_ICON.get(tag, "chat"), " ".join(first_message.split())[:60]])


def _history(state: AppState, conv_id: str) -> list[dict]:
    rows = state.db.all("select role, kind, content from app.messages where conversation_id = %s order by seq desc limit %s",
                        [conv_id, state.settings.history_messages])
    return [{"role": r["role"], "kind": r["kind"], "content": r["content"][:HISTORY_CHARS]} for r in reversed(rows)]


def _safe_meta(meta: dict) -> dict:
    """Diagnostics worth keeping (timings, verification results, what was retrieved with). Never the raw user text."""
    keep = ("analysis", "verify", "retrieval_seconds", "seconds", "llm_calls_this_turn", "pii_removed", "error")
    return {k: meta[k] for k in keep if k in meta}


def run_turn(state: AppState, user: dict, conv_id: str, text: str, language: str, on_status: Callable[[str], None]) -> dict:
    """Returns {"conversation": ..., "message": ...} for the browser, or raises ApiError (the router turns it into an `error` event)."""
    uid = str(user["id"])
    user_msg = None
    try:
        engine = state.engine.get()
        history = _history(state, conv_id)
        conv = get_conversation(state, uid, conv_id)
        user_msg = state.db.one("insert into app.messages (conversation_id, user_id, role, kind, content) values (%s, %s, 'user', 'user', %s) returning id",
                                [conv_id, uid, text])
        out = engine.respond(text, history=history, profile=engine_profile(user), language=language, on_status=on_status)
        msg, meta = out["message"], out.get("meta", {})

        if msg["kind"] == "info" and msg.get("reason") in ("error", "busy"):      # nothing useful was produced
            raise ApiError(503 if msg["reason"] == "error" else 429, "UNAVAILABLE" if msg["reason"] == "error" else "RATE_LIMITED", msg["text"])

        payload = {k: v for k, v in msg.items() if k not in ("createdAt", "feedback")}
        analysed = out.get("conversation") if conv["title_auto"] else None
        with state.db.tx() as c:
            row = c.execute(
                "insert into app.messages (conversation_id, user_id, role, kind, content, payload, meta) "
                "values (%s, %s, 'assistant', %s, %s, %s, %s) returning id, seq, role, kind, content, payload, attachment_ids, feedback, created_at",
                [conv_id, uid, msg["kind"], msg.get("content") or msg.get("text") or "", Jsonb(payload), Jsonb(_safe_meta(meta))]).fetchone()
            title, tag = (analysed["title"], analysed["tag"]) if analysed else (conv["title"], conv["tag"])
            new_conv = c.execute(
                f"update app.conversations set title = %s, tag = %s, icon = %s, title_auto = %s, preview = %s, updated_at = now() "
                f"where id = %s returning {CONV_COLS}",
                [title, tag, TAG_ICON.get(tag, conv["icon"]), conv["title_auto"] and not analysed, " ".join(text.split())[:60], conv_id]).fetchone()
        return {"conversation": conv_out(new_conv), "message": msg_out(row)}
    except Exception as e:
        if user_msg is not None:                                  # leave no half-turn behind: the question without an answer
            try:
                state.db.run("delete from app.messages where id = %s", [user_msg["id"]])
            except Exception:                                     # noqa: BLE001
                log.exception("could not remove the unanswered message")
        if isinstance(e, ApiError):
            raise
        log.exception("chat turn failed (conversation %s)", conv_id)
        raise ApiError(500, "INTERNAL", "LegalMate could not answer right now. Please try again.")
