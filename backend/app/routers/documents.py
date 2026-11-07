"""Document upload: the text is extracted at once (PDF, Word, English and Urdu OCR); the original file is not kept."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from .. import docs_service
from ..deps import current_user, get_state
from ..errors import ApiError, not_found
from ..extract import ExtractError, extract
from ..state import AppState
from ..users_repo import iso

router = APIRouter(tags=["documents"])
_CTRL = re.compile(r"[\x00-\x1f\x7f/\\]")


def _safe_name(raw: str | None) -> str:
    name = _CTRL.sub("_", (raw or "document").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]).strip()
    return (name or "document")[:120]


# ---------------------------------------------------------------------------------------------- upload
@router.post("/documents", status_code=201)
def upload_document(file: UploadFile = File(...), purpose: str = Form("analysis"), saveToVault: bool = Form(False),
                    user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    cfg, uid = state.settings.docs, str(user["id"])
    if purpose not in ("analysis", "chat"):
        raise ApiError(400, "VALIDATION_ERROR", "purpose must be analysis or chat.", {"field": "purpose"})
    if cfg.uploads_per_hour > 0:
        state.limiter.check(f"upload:{uid}", cfg.uploads_per_hour, 3600, "You are uploading very quickly. Please wait a little and try again.")
    docs_service.purge_expired(state.db, cfg)
    if cfg.docs_per_user > 0:
        n = state.db.one("select count(*) as n from app.documents where user_id = %s", [uid])["n"]
        if n >= cfg.docs_per_user:
            raise ApiError(422, "QUOTA_EXCEEDED", f"You have {n} stored documents, which is the limit. Delete some documents or wait for old ones to expire.")

    data = file.file.read(cfg.max_upload_bytes + 1)                                   # never read more than the limit
    if len(data) > cfg.max_upload_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", f"This file is larger than {cfg.max_upload_mb} MB.")
    if not data:
        raise ApiError(400, "VALIDATION_ERROR", "The file is empty.", {"field": "file"})
    try:
        res = extract(data, cfg)
    except ExtractError as e:
        raise ApiError(e.status, e.code, e.message)

    expires = datetime.now(timezone.utc) + timedelta(days=cfg.doc_retention_days) if cfg.doc_retention_days > 0 else None
    row = state.db.one(
        "insert into app.documents (user_id, name, file_type, size_bytes, pages, purpose, text, char_count, ocr_pages, ocr_conf, truncated, expires_at) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id, created_at",
        [uid, _safe_name(file.filename), res.file_type, len(data), res.pages, purpose, res.text, len(res.text), res.ocr_pages, res.ocr_conf, res.truncated, expires])
    warnings = list(res.warnings)
    if saveToVault:
        warnings.append("The Legal Vault is not available yet, so the original file was not kept. Only the text needed for analysis is stored.")
    return {"id": str(row["id"]), "name": _safe_name(file.filename), "sizeBytes": len(data), "fileType": res.file_type, "pages": res.pages,
            "ocrUsed": res.ocr_pages > 0, "urdu": res.urdu, "truncated": res.truncated, "charCount": len(res.text), "warnings": warnings,
            "expiresAt": iso(expires)}


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    if state.db.run("delete from app.documents where id = %s and user_id = %s", [str(doc_id), user["id"]]) == 0:
        raise not_found("That document")
    return Response(status_code=204)


# ---------------------------------------------------------------------------------------------- analyses (later)
@router.post("/analyses")
def create_analysis(_: dict = Depends(current_user)):
    raise ApiError(501, "NOT_IMPLEMENTED", "Document analysis is not available yet.")
