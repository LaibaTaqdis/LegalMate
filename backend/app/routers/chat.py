"""Chat: conversations, the streaming message endpoint (SSE), feedback."""
from __future__ import annotations

import json
import queue
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse

from .. import chat_service as cs
from .. import docs_service
from ..deps import current_user, get_state
from ..errors import ApiError, not_found
from ..schemas import ConversationCreate, ConversationPatch, FeedbackIn, MessageIn, PinIn, SourceReportIn
from ..state import AppState

router = APIRouter(prefix="/chat", tags=["chat"])
_DONE = object()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------------------------- conversations
@router.get("/conversations")
def list_conversations(user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    rows = state.db.all(f"select {cs.CONV_COLS} from app.conversations where user_id = %s order by updated_at desc limit 200", [user["id"]])
    return {"items": [cs.conv_out(r) for r in rows]}


@router.post("/conversations", status_code=201)
def create_conversation(body: ConversationCreate, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Creates the (empty) conversation. The first message is then sent with POST .../messages, which also names the conversation."""
    state.limiter.check(f"newconv:{user['id']}", 30, 3600, "You are starting conversations very quickly. Please slow down.")
    return {"conversation": cs.conv_out(cs.create_conversation(state, str(user["id"]), body.firstMessage, body.topic))}


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    conv = cs.get_conversation(state, str(user["id"]), str(conv_id))
    rows = state.db.all("select id, role, kind, content, payload, attachment_ids, feedback, created_at from app.messages "
                        "where conversation_id = %s order by seq limit 500", [conv["id"]])
    names = cs.attachment_names(state, rows)
    return {"conversation": cs.conv_out(conv), "messages": [cs.msg_out(r, names) for r in rows]}


@router.patch("/conversations/{conv_id}")
def rename_conversation(conv_id: UUID, body: ConversationPatch, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    row = state.db.one(f"update app.conversations set title = %s, title_auto = false where id = %s and user_id = %s returning {cs.CONV_COLS}",
                       [body.title, str(conv_id), user["id"]])
    if row is None:
        raise not_found("That conversation")
    return cs.conv_out(row)


@router.delete("/conversations/{conv_id}", status_code=204)
def delete_conversation(conv_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    if state.db.run("delete from app.conversations where id = %s and user_id = %s", [str(conv_id), user["id"]]) == 0:
        raise not_found("That conversation")
    return Response(status_code=204)


@router.put("/conversations/{conv_id}/pin", status_code=204)
def pin_conversation(conv_id: UUID, body: PinIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    if state.db.run("update app.conversations set pinned = %s where id = %s and user_id = %s", [body.pinned, str(conv_id), user["id"]]) == 0:
        raise not_found("That conversation")
    return Response(status_code=204)


# ---------------------------------------------------------------------------------------------- the message stream
@router.post("/conversations/{conv_id}/messages")
def send_message(conv_id: UUID, body: MessageIn, request: Request, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Server-Sent Events: `status` ... `conversation` (renamed/updated) then `answer` (the full assistant message) or `error`."""
    uid, s = str(user["id"]), state.settings
    cs.get_conversation(state, uid, str(conv_id))                                  # 404 before anything is streamed
    text = body.content.strip()
    if not text:
        raise ApiError(400, "VALIDATION_ERROR", "Please type a question.", {"field": "content"})
    attachment_ids = docs_service.parse_ids(body.attachmentIds, "attachment")
    if len(attachment_ids) > s.docs.attachments_per_message:
        raise ApiError(422, "UNPROCESSABLE", f"You can attach up to {s.docs.attachments_per_message} files to one question.")
    docs = docs_service.load_owned(state.db, uid, attachment_ids) if attachment_ids else []      # 404 if missing, expired or not theirs

    # ---- limits (cheapest first). Per-day is counted from the database, so it survives restarts.
    state.limiter.check(f"chat:burst:{uid}", 6, 60, "You are sending messages very quickly. Please wait a moment.")
    if s.max_msgs_per_hour > 0:                                                     # per-user limits are optional (0 = off)
        state.limiter.check(f"chat:hour:{uid}", s.max_msgs_per_hour, 3600, f"You have reached the limit of {s.max_msgs_per_hour} questions per hour. Please try again later.")
    if s.max_msgs_per_day > 0:
        today = state.db.one("select count(*) as n from app.messages where user_id = %s and role = 'user' and created_at > now() - interval '24 hours'", [uid])["n"]
        if today >= s.max_msgs_per_day:
            raise ApiError(429, "RATE_LIMITED", f"You have reached today's limit of {s.max_msgs_per_day} questions. Please come back tomorrow.")
    with state.inflight_lock:
        if uid in state.inflight:
            raise ApiError(429, "RATE_LIMITED", "LegalMate is still answering your previous question. Please wait for it to finish.")
        state.inflight.add(uid)

    language = body.language or "auto"          # the interface language does not decide the answer language: what the user writes does
    events: queue.Queue = queue.Queue()

    def status(stage: str) -> None:
        if stage != "understanding":                                               # the stream already opened with "thinking"
            events.put(("status", {"state": stage}))

    def work() -> None:
        try:
            result = cs.run_turn(state, user, str(conv_id), text, language, status, docs=docs)
            events.put(("conversation", result["conversation"]))
            events.put(("answer", result["message"]))
        except ApiError as e:
            events.put(("error", {"code": e.code, "message": e.message}))
        except Exception:                                                          # noqa: BLE001 - run_turn already logged details
            events.put(("error", {"code": "INTERNAL", "message": "LegalMate could not answer right now. Please try again."}))
        finally:
            with state.inflight_lock:
                state.inflight.discard(uid)
            events.put(_DONE)

    try:
        state.executor.submit(work)
    except Exception:
        with state.inflight_lock:
            state.inflight.discard(uid)
        raise ApiError(503, "UNAVAILABLE", "LegalMate is busy right now. Please try again in a moment.")

    def stream():
        yield _sse("status", {"state": "thinking"})
        while True:
            try:
                item = events.get(timeout=10)
            except queue.Empty:
                yield ": keep-alive\n\n"                                           # keeps proxies from closing a quiet connection
                continue
            if item is _DONE:
                return
            yield _sse(*item)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


# ---------------------------------------------------------------------------------------------- feedback
@router.post("/messages/{message_id}/feedback", status_code=204)
def feedback(message_id: UUID, body: FeedbackIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    if state.db.run("update app.messages set feedback = %s, feedback_comment = %s where id = %s and user_id = %s and role = 'assistant'",
                    [body.vote, body.comment, str(message_id), user["id"]]) == 0:
        raise not_found("That message")
    return Response(status_code=204)


@router.post("/messages/{message_id}/save")
def save_to_vault(message_id: UUID, _: dict = Depends(current_user)):
    raise ApiError(501, "NOT_IMPLEMENTED", "The Legal Vault is not available yet, so answers cannot be saved there.")


@router.post("/sources/report", status_code=204)
def report_source(body: SourceReportIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    try:
        mid = str(UUID(body.messageId))
    except ValueError:
        raise ApiError(400, "VALIDATION_ERROR", "messageId: not a valid message id.", {"field": "messageId"})
    if state.db.one("select 1 as ok from app.messages where id = %s and user_id = %s", [mid, user["id"]]) is None:
        raise not_found("That message")
    state.limiter.check(f"report:{user['id']}", 20, 3600)
    state.db.run("insert into app.source_reports (user_id, message_id, source_id, reason) values (%s, %s, %s, %s)", [user["id"], mid, body.sourceId, body.reason])
    return Response(status_code=204)
