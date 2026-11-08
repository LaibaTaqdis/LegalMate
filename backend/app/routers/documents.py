"""Document upload (text is extracted at once; the original file is not kept) and document analysis (a background job the browser polls)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from psycopg.types.json import Jsonb

from .. import docs_service
from ..deps import current_user, get_state
from ..errors import ApiError, not_found
from ..extract import ExtractError, check_image, compact_image, extract, sniff
from ..schemas import AnalysisIn
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
    docs_service.purge_if_due(state.db, cfg)
    if cfg.docs_per_user > 0:
        n = state.db.one("select count(*) as n from app.documents where user_id = %s", [uid])["n"]
        if n >= cfg.docs_per_user:
            raise ApiError(422, "QUOTA_EXCEEDED", f"You have {n} stored documents, which is the limit. Delete some documents or wait for old ones to expire.")

    data = file.file.read(cfg.max_upload_bytes + 1)                                   # never read more than the limit
    if len(data) > cfg.max_upload_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", f"This file is larger than {cfg.max_upload_mb} MB.")
    if not data:
        raise ApiError(400, "VALIDATION_ERROR", "The file is empty.", {"field": "file"})
    expires = datetime.now(timezone.utc) + timedelta(days=cfg.doc_retention_days) if cfg.doc_retention_days > 0 else None
    try:
        kind = sniff(data)
        if purpose == "chat" and cfg.ocr_enabled and cfg.ocr_defer_chat and kind in ("jpg", "png"):
            # A photo in chat: accept it now, read it when the question is sent (the chat shows "Analyzing the image…"), so the upload is instant.
            check_image(data, cfg)
            name, original_size = _safe_name(file.filename), len(data)
            data, kind = compact_image(data, kind, cfg)
            row = state.db.one(
                "insert into app.documents (user_id, name, file_type, size_bytes, pages, purpose, text, char_count, status, raw, expires_at) "
                "values (%s, %s, %s, %s, 1, 'chat', '', 0, 'pending', %s, %s) returning id", [uid, name, kind, original_size, data, expires])
            return {"id": str(row["id"]), "name": name, "sizeBytes": original_size, "fileType": kind, "pages": 1, "ocrUsed": False, "urdu": False,
                    "truncated": False, "charCount": 0, "pending": True, "warnings": [], "expiresAt": iso(expires)}
        res = extract(data, cfg)
    except ExtractError as e:
        raise ApiError(e.status, e.code, e.message)

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


# ---------------------------------------------------------------------------------------------- analyses
@router.post("/analyses", status_code=202)
def create_analysis(body: AnalysisIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    from ..analysis import run_analysis

    cfg, uid = state.settings.docs, str(user["id"])
    ids = docs_service.parse_ids(body.documentIds)
    if len(ids) > cfg.analysis_max_docs:
        raise ApiError(422, "UNPROCESSABLE", f"You can analyse up to {cfg.analysis_max_docs} documents at once.")
    owned = docs_service.load_owned(state.db, uid, ids, with_text=False)               # 404 for anything missing or not theirs
    if any(d.get("status") == "pending" for d in owned):
        raise ApiError(422, "UNPROCESSABLE", "That photo has not been read yet. Upload it again on the Analysis page.")
    label = owned[0]["name"] + (f" (+{len(owned) - 1} more)" if len(owned) > 1 else "")
    if not state.engine.enabled:
        raise ApiError(503, "UNAVAILABLE", "Document analysis is switched off on this server.")
    running = state.db.one("select count(*) as n from app.analyses where user_id = %s and status in ('queued', 'processing') "
                           "and created_at > now() - make_interval(mins => %s)", [uid, cfg.analysis_stale_minutes])["n"]
    if running >= cfg.analysis_per_user_running:
        raise ApiError(429, "RATE_LIMITED", "Your earlier analysis is still running. Please wait for it to finish.")
    if cfg.analysis_per_day > 0:
        today = state.db.one("select count(*) as n from app.analyses where user_id = %s and created_at > now() - interval '24 hours'", [uid])["n"]
        if today >= cfg.analysis_per_day:
            raise ApiError(429, "RATE_LIMITED", f"You have reached today's limit of {cfg.analysis_per_day} analyses. Please come back tomorrow.")
    row = state.db.one("insert into app.analyses (user_id, document_id, language, depth, input) values (%s, %s, %s, %s, %s) returning id",
                       [uid, ids[0], body.language, body.depth, Jsonb({"documentIds": ids, "name": label})])
    aid = str(row["id"])
    try:
        state.analysis_executor.submit(run_analysis, state, aid)
    except Exception:
        state.db.run("update app.analyses set status = 'failed', error = 'The server is busy. Please try again.' where id = %s", [aid])
        raise ApiError(503, "UNAVAILABLE", "LegalMate is busy right now. Please try again in a moment.")
    return {"id": aid, "status": "queued"}


_NAME = "coalesce(a.result->'document'->>'name', a.input->>'name', d.name, 'Document')"
_RISK = "a.result->'overallRisk'->>'level'"
_SORTS = {"newest": "a.created_at desc", "oldest": "a.created_at asc", "name": f"lower({_NAME}) asc, a.created_at desc",
          "risk": f"case {_RISK} when 'High' then 3 when 'Medium' then 2 when 'Low' then 1 else 0 end desc, a.created_at desc"}


@router.get("/analyses")
def list_analyses(q: str = Query("", max_length=80), risk: Literal["all", "High", "Medium", "Low"] = "all",
                  status: Literal["all", "completed", "running", "failed"] = "all", days: int = Query(0, ge=0, le=3650),
                  sort: Literal["newest", "oldest", "name", "risk"] = "newest", page: int = Query(1, ge=1, le=10_000),
                  pageSize: int | None = Query(None, ge=1, le=50), user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """The user's analysis history, newest first by default. Filters: name search, overall risk, status, age in days. Also returns the
    counts the filter chips show (over everything the user has, not just the current filter)."""
    size = pageSize or state.settings.docs.analysis_page_size
    where, params = ["a.user_id = %s"], [user["id"]]
    if q.strip():
        where.append(f"{_NAME} ilike %s")
        params.append("%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
    if risk != "all":
        where.append(f"{_RISK} = %s")
        params.append(risk)
    if status == "running":
        where.append("a.status in ('queued', 'processing')")
    elif status != "all":
        where.append("a.status = %s")
        params.append(status)
    if days:
        where.append("a.created_at > now() - make_interval(days => %s)")
        params.append(days)
    cond = " and ".join(where)
    frm = "from app.analyses a left join app.documents d on d.id = a.document_id"
    rows_sql = (
        f"select a.id, a.status, a.progress, a.error, a.created_at, a.finished_at, a.expires_at, {_NAME} as name, {_RISK} as risk, "
        f"a.result->'document'->>'documentType' as doc_type, a.result->'document'->>'fileType' as file_type, a.result->'counts' as counts, "
        f"coalesce(d.file_type, a.result->'document'->>'fileType') as ftype {frm} where {cond} order by {_SORTS[sort]} limit %s offset %s")
    counts_sql = (
        "select count(*) as every, count(*) filter (where status = 'completed') as completed, "
        "count(*) filter (where status in ('queued', 'processing')) as running, count(*) filter (where status = 'failed') as failed, "
        "count(*) filter (where result->'overallRisk'->>'level' = 'High') as high, count(*) filter (where result->'overallRisk'->>'level' = 'Medium') as medium, "
        "count(*) filter (where result->'overallRisk'->>'level' = 'Low') as low from app.analyses where user_id = %s")
    rows, (c,), (t,) = state.db.batch([(rows_sql, [*params, size, (page - 1) * size]), (counts_sql, [user["id"]]),
                                       (f"select count(*) as n {frm} where {cond}", params)])        # one network round trip for all three
    total = t["n"]
    items = [{"id": str(r["id"]), "status": "processing" if r["status"] in ("queued", "processing") else r["status"], "progress": r["progress"],
              "error": r["error"], "name": r["name"], "fileType": r["ftype"], "documentType": r["doc_type"], "risk": r["risk"],
              "counts": r["counts"], "createdAt": iso(r["created_at"]), "finishedAt": iso(r["finished_at"]), "expiresAt": iso(r["expires_at"])} for r in rows]
    return {"items": items, "total": total, "page": page, "pageSize": size,
            "counts": {"all": c["every"], "completed": c["completed"], "running": c["running"], "failed": c["failed"],
                       "High": c["high"], "Medium": c["medium"], "Low": c["low"]}}


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Removes the analysis AND the stored text of the document(s) it was made from (nothing of it is kept afterwards)."""
    row = state.db.one("select input from app.analyses where id = %s and user_id = %s", [str(analysis_id), user["id"]])
    if row is None:
        raise not_found("That analysis")
    with state.db.tx() as c:
        ids = [i for i in ((row["input"] or {}).get("documentIds") or []) if isinstance(i, str)]
        c.execute("delete from app.analyses where id = %s and user_id = %s", [str(analysis_id), user["id"]])
        if ids:
            c.execute("delete from app.documents where user_id = %s and purpose = 'analysis' and id = any(%s::uuid[]) "
                      "and not exists (select 1 from app.analyses x where x.document_id = app.documents.id)", [user["id"], ids])
    return Response(status_code=204)


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    r = state.db.one("select id, status, progress, error, result, input from app.analyses where id = %s and user_id = %s", [str(analysis_id), user["id"]])
    if r is None:
        raise not_found("That analysis")
    base = {"id": str(r["id"]), "status": r["status"], "progress": r["progress"], "error": r["error"]}
    if r["status"] == "completed" and r["result"]:
        return {**base, **r["result"]}
    ids = (r["input"] or {}).get("documentIds", [])
    name = None
    if ids:
        d = state.db.one("select name from app.documents where id = %s", [ids[0]])
        name = d["name"] if d else None
    return {**base, "document": {"name": name or "your document"}}


def _later() -> ApiError:
    return ApiError(501, "NOT_IMPLEMENTED", "This is not available yet.")


@router.get("/analyses/{analysis_id}/report")
def analysis_report(analysis_id: UUID, _: dict = Depends(current_user)):
    raise ApiError(501, "NOT_IMPLEMENTED", "Downloading the report as a PDF is not available yet.")


@router.post("/analyses/{analysis_id}/save")
def analysis_save(analysis_id: UUID, _: dict = Depends(current_user)):
    raise ApiError(501, "NOT_IMPLEMENTED", "The Legal Vault is not available yet, so the analysis cannot be saved there.")


@router.post("/analyses/{analysis_id}/share")
def analysis_share(analysis_id: UUID, _: dict = Depends(current_user)):
    raise ApiError(501, "NOT_IMPLEMENTED", "Sharing an analysis is not available yet.")
