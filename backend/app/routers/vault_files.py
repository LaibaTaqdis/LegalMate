"""Legal Vault, part B: your own files and folders (upload, list, preview/download links, folders, notes, Trash)."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile

from .. import docs_service, vault_files
from ..deps import current_user, get_state
from ..errors import ApiError
from ..schemas import VaultFavouriteIn, VaultFilePatch, VaultFolderIn, VaultNoteIn
from ..state import AppState

router = APIRouter(prefix="/vault", tags=["vault-files"])
Category = Literal["all", "favourites", "trash", "Contracts", "Notices", "Court Documents", "Property", "Personal", "Family", "Other"]


def _limit(state: AppState, uid) -> None:
    state.limiter.check(f"vaultfile:{uid}", 120, 60, "You are doing that very quickly. Please wait a moment.")


def _uuid(value: str | None, field: str) -> str | None:
    if not value:
        return None
    try:
        return str(UUID(str(value)))
    except ValueError:
        raise ApiError(400, "VALIDATION_ERROR", f"{field}: not a valid id.", {"field": field})


# ---------------------------------------------------------------------------------------------- files
@router.post("/files", status_code=201)
def upload_file(file: UploadFile = File(...), folderId: str | None = Form(None), category: str | None = Form(None),
                user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    cfg, uid = state.settings.docs, str(user["id"])
    if cfg.vault_uploads_per_hour > 0:
        state.limiter.check(f"vaultup:{uid}", cfg.vault_uploads_per_hour, 3600, "You are adding files very quickly. Please wait a little and try again.")
    data = file.file.read(cfg.max_upload_bytes + 1)                                   # never read more than the limit
    return vault_files.upload(state, uid, data, file.filename, _uuid(folderId, "folderId"), (category or "").strip() or None)


@router.get("/files")
def list_files(category: Category = "all", folderId: str | None = Query(None, max_length=64), q: str = Query("", max_length=80),
               sort: Literal["updated_desc", "updated_asc", "name_asc", "name_desc", "size_desc"] = "updated_desc", page: int = Query(1, ge=1, le=10_000),
               pageSize: int | None = Query(None, ge=1, le=100), user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    cfg = state.settings.docs
    docs_service.purge_if_due(state.db, cfg, state.storage)                          # the Trash empties itself (at most once a minute)
    return vault_files.list_files(state.db, cfg, str(user["id"]), category=category, folder_id=_uuid(folderId, "folderId"), q=q, sort=sort, page=page,
                                  page_size=pageSize or cfg.vault_page_size)


@router.get("/files/{file_id}")
def get_file(file_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    return vault_files.get_file(state.db, str(user["id"]), str(file_id))


@router.get("/files/{file_id}/link")
def file_link(file_id: UUID, download: bool = False, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """A signed link that works for a few minutes (VAULT_LINK_SECONDS): `download=true` makes the browser save it, otherwise it opens in place."""
    _limit(state, user["id"])
    return vault_files.link(state, str(user["id"]), str(file_id), download)


@router.get("/files/{file_id}/text")
def file_text(file_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    return vault_files.read_file_text(state.db, str(user["id"]), str(file_id))


@router.patch("/files/{file_id}")
def patch_file(file_id: UUID, body: VaultFilePatch, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    changes = {k: getattr(body, k) for k in body.model_fields_set if k in ("name", "folderId", "category")}
    if "name" in changes and changes["name"] is None:
        raise ApiError(400, "VALIDATION_ERROR", "name: please enter a name.", {"field": "name"})
    if changes.get("folderId"):
        changes["folderId"] = _uuid(changes["folderId"], "folderId")
    if "category" in changes and changes["category"] is None:
        raise ApiError(400, "VALIDATION_ERROR", "category: choose a category.", {"field": "category"})
    return vault_files.patch(state.db, str(user["id"]), str(file_id), changes)


@router.put("/files/{file_id}/favourite", status_code=204)
def favourite_file(file_id: UUID, body: VaultFavouriteIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    vault_files.set_favourite(state.db, str(user["id"]), str(file_id), body.favourite)
    return Response(status_code=204)


@router.delete("/files/{file_id}", status_code=204)
def delete_file(file_id: UUID, permanent: bool = False, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Moves the file to the Trash. `?permanent=true` deletes a file that is already in the Trash for good (the stored original too)."""
    _limit(state, user["id"])
    if permanent:
        vault_files.delete_forever(state, str(user["id"]), str(file_id))
    else:
        vault_files.trash(state.db, str(user["id"]), str(file_id))
    return Response(status_code=204)


@router.post("/files/{file_id}/restore", status_code=204)
def restore_file(file_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    vault_files.restore(state.db, str(user["id"]), str(file_id))
    return Response(status_code=204)


@router.delete("/files-trash")
def empty_files_trash(user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    return {"deleted": vault_files.empty_trash(state, str(user["id"]))}


@router.get("/files/{file_id}/notes")
def list_file_notes(file_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    return {"items": vault_files.list_notes(state.db, str(user["id"]), str(file_id))}


@router.post("/files/{file_id}/notes", status_code=201)
def add_file_note(file_id: UUID, body: VaultNoteIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    cfg = state.settings.docs
    if len(body.text) > cfg.vault_note_chars:
        raise ApiError(400, "VALIDATION_ERROR", f"text: a note can be up to {cfg.vault_note_chars} characters.", {"field": "text"})
    return vault_files.add_note(state.db, cfg, str(user["id"]), str(file_id), body.text)


@router.delete("/files/{file_id}/notes/{note_id}", status_code=204)
def delete_file_note(file_id: UUID, note_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    vault_files.delete_note(state.db, str(user["id"]), str(file_id), str(note_id))
    return Response(status_code=204)


@router.get("/files/{file_id}/activity")
def file_activity(file_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    return {"items": vault_files.list_activity(state.db, str(user["id"]), str(file_id))}


# ---------------------------------------------------------------------------------------------- folders
@router.get("/folders")
def list_folders(user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    return {"items": vault_files.list_folders(state.db, str(user["id"]))}


@router.post("/folders", status_code=201)
def create_folder(body: VaultFolderIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    if body.name is None:
        raise ApiError(400, "VALIDATION_ERROR", "name: this field is required.", {"field": "name"})
    return vault_files.create_folder(state.db, state.settings.docs, str(user["id"]), body.name, body.color)


@router.patch("/folders/{folder_id}")
def update_folder(folder_id: UUID, body: VaultFolderIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    return vault_files.update_folder(state.db, str(user["id"]), str(folder_id), body.name, body.color)


@router.delete("/folders/{folder_id}", status_code=204)
def delete_folder(folder_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Deletes the folder; the files in it are kept and simply have no folder."""
    _limit(state, user["id"])
    vault_files.delete_folder(state.db, str(user["id"]), str(folder_id))
    return Response(status_code=204)
