"""Stored documents: ownership-checked loading, expiry clean-up, and choosing which part of a long document to show the assistant."""
from __future__ import annotations

import logging
import re
from uuid import UUID

from .config import DocSettings
from .db import Database
from .errors import ApiError

log = logging.getLogger("legalmate.docs")


def purge_expired(db: Database, cfg: DocSettings) -> dict:
    """Deletes documents and analyses past their retention, and marks analyses that were running when the server stopped as failed."""
    out = {}
    out["documents"] = db.run("delete from app.documents where expires_at is not null and expires_at < now()")
    out["analyses"] = db.run("delete from app.analyses where expires_at is not null and expires_at < now()")
    out["stale"] = db.run(
        "update app.analyses set status = 'failed', error = 'The analysis was interrupted. Please start it again.', finished_at = now() "
        "where status in ('queued', 'processing') and created_at < now() - make_interval(mins => %s)", [cfg.analysis_stale_minutes])
    if any(out.values()):
        log.info("clean-up: %s", out)
    return out


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
    cols = "id, name, file_type, size_bytes, pages, purpose, char_count, ocr_pages, ocr_conf, truncated, created_at" + (", text" if with_text else "")
    rows = {str(r["id"]): r for r in db.all(f"select {cols} from app.documents where user_id = %s and id = any(%s::uuid[])", [user_id, ids])}
    missing = [i for i in ids if i not in rows]
    if missing:
        raise ApiError(404, "NOT_FOUND", "A document was not found. It may have expired or been deleted. Please upload it again.")
    return [rows[i] for i in ids]


# ------------------------------------------------------------------------------------------------ what the assistant reads
_PAGE = re.compile(r"^\[Page \d+\]$", re.M)


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
