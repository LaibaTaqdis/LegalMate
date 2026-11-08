"""Stored documents: ownership-checked loading, expiry clean-up, and choosing which part of a long document to show the assistant."""
from __future__ import annotations

import logging
import re
import time
from uuid import UUID

from .config import DocSettings
from .db import Database
from .errors import ApiError

log = logging.getLogger("legalmate.docs")


def purge_expired(db: Database, cfg: DocSettings) -> dict:
    """Deletes documents and analyses past their retention, and marks analyses that were running when the server stopped as failed."""
    out = {}
    out["documents"] = db.run("delete from app.documents where expires_at is not null and expires_at < now()")
    out["unread_photos"] = db.run("delete from app.documents where status = 'pending' and created_at < now() - make_interval(hours => %s)", [cfg.pending_hours])
    out["analyses"] = db.run("delete from app.analyses where expires_at is not null and expires_at < now()")
    out["stale"] = db.run(
        "update app.analyses set status = 'failed', error = 'The analysis was interrupted. Please start it again.', finished_at = now() "
        "where status in ('queued', 'processing') and created_at < now() - make_interval(mins => %s)", [cfg.analysis_stale_minutes])
    if any(out.values()):
        log.info("clean-up: %s", out)
    return out


_last_purge = 0.0
PURGE_EVERY_SECONDS = 60


def purge_if_due(db: Database, cfg: DocSettings) -> None:
    """`purge_expired`, but at most once a minute per server: it is four database round trips, and an upload should not pay for them every time."""
    global _last_purge
    now = time.monotonic()
    if now - _last_purge < PURGE_EVERY_SECONDS:
        return
    _last_purge = now
    purge_expired(db, cfg)


def parse_ids(ids: list[str], what: str = "document") -> list[str]:
    seen, out = set(), []
    for raw in ids:
        try:
            u = str(UUID(str(raw)))
        except ValueError:
            raise ApiError(400, "VALIDATION_ERROR", f"That {what} id is not valid.", {"field": "documentIds"})
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def load_owned(db: Database, user_id: str, ids: list[str], *, with_text: bool = True) -> list[dict]:
    """The user's documents in the order asked for. Anything missing, expired or not theirs is one clear 404 (never revealed which)."""
    if not ids:
        return []
    cols = "id, name, file_type, size_bytes, pages, purpose, status, char_count, ocr_pages, ocr_conf, truncated, created_at" + (", text" if with_text else "")
    rows = {str(r["id"]): r for r in db.all(f"select {cols} from app.documents where user_id = %s and id = any(%s::uuid[])", [user_id, ids])}
    missing = [i for i in ids if i not in rows]
    if missing:
        raise ApiError(404, "NOT_FOUND", "A document was not found. It may have expired or been deleted. Please upload it again.")
    return [rows[i] for i in ids]


def read_pending(state, user_id: str, d: dict) -> None:
    """Reads a photo that was attached in chat but not read yet (this is the slow OCR step, done while the answer is prepared).
    Fills `d` with the text, stores it, and empties the stored picture: the original is not kept. A photo with no readable text is
    removed and reported in plain words, which also takes the question back (the caller undoes the half-turn)."""
    from .extract import ExtractError, extract

    row = state.db.one("select raw from app.documents where id = %s and user_id = %s and status = 'pending'", [str(d["id"]), user_id])
    if row is None or row["raw"] is None:                    # read meanwhile (the same photo sent twice): use what is stored
        fresh = state.db.one("select text, char_count, pages, ocr_pages, ocr_conf, truncated from app.documents where id = %s and user_id = %s",
                             [str(d["id"]), user_id])
        if fresh:
            d.update(fresh)
        return
    try:
        res = extract(bytes(row["raw"]), state.settings.docs)
    except ExtractError as e:
        state.db.run("delete from app.documents where id = %s and user_id = %s", [str(d["id"]), user_id])
        raise ApiError(e.status, e.code, e.message)
    state.db.run("update app.documents set text = %s, char_count = %s, pages = %s, ocr_pages = %s, ocr_conf = %s, truncated = %s, "
                 "status = 'ready', raw = null where id = %s and user_id = %s",
                 [res.text, len(res.text), res.pages, res.ocr_pages, res.ocr_conf, res.truncated, str(d["id"]), user_id])
    d.update(text=res.text, char_count=len(res.text), pages=res.pages, ocr_pages=res.ocr_pages, ocr_conf=res.ocr_conf, truncated=res.truncated, status="ready")


# ------------------------------------------------------------------------------------------------ what the assistant reads
_PAGE =re.compile(r"^\[Page \d+\]$", re.M)


def _pieces(text: str, target: int = 700) -> list[str]:
    """Paragraph-sized pieces (about `target` characters), keeping page markers with the text that follows them."""
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n(?=\[Page \d+\])", text) if p.strip()]
    out, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) > target:
            out.append(cur)
            cur = p
        else:
            cur = f"{cur}\n{p}" if cur else p
    if cur:
        out.append(cur)
    return out


def select_context(docs: list[dict], question: str, limit: int) -> str:
    """Up to `limit` characters of the documents for one chat question. A short document goes in whole. A long one contributes its
    opening (title, parties) plus the pieces that best match the question's words, in their original order."""
    from retrieval.lexical import LexicalIndex

    blocks = []
    for d in docs:
        header = f"=== Document: {d['name']} ==="
        text = d["text"]
        blocks.append((header, text))
    total = sum(len(h) + len(t) for h, t in blocks)
    if total <= limit:
        return "\n\n".join(f"{h}\n{t}" for h, t in blocks)

    budget = max(300, limit // len(blocks))
    parts = []
    for header, text in blocks:
        pieces = _pieces(text)
        keep = {0}
        used = len(pieces[0]) if pieces else 0
        try:
            idx = LexicalIndex(((i, "", p) for i, p in enumerate(pieces)))
            for i, _ in idx.search(question, k=len(pieces)):
                if i in keep:
                    continue
                if used + len(pieces[i]) > budget - len(header):
                    continue
                keep.add(i)
                used += len(pieces[i])
        except Exception:                                    # noqa: BLE001 - never fail a question because of piece ranking
            pass
        body = "\n[...]\n".join(pieces[i] for i in sorted(keep)) if pieces else text[:budget]
        parts.append(f"{header}\n{body[: budget]}")
    return "\n\n".join(parts)[:limit]
