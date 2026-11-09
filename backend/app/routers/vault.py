"""Legal Vault, part A: saved answers and analyses (list, open, rename, favourite, notes, activity, Trash)."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from .. import vault
from ..deps import current_user, get_state
from ..errors import ApiError
from ..schemas import VaultFavouriteIn, VaultNoteIn, VaultRenameIn, VaultSaveIn
from ..state import AppState

router = APIRouter(prefix="/vault", tags=["vault"])


def _limit(state: AppState, uid) -> None:
    state.limiter.check(f"vault:{uid}", 120, 60, "You are doing that very quickly. Please wait a moment.")


@router.post("/items", status_code=201)
def save_item(body: VaultSaveIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Saves a chat answer (`messageId`) or a finished analysis (`analysisId`). Saving the same one again is not an error: -> alreadySaved."""
    _limit(state, user["id"])
    cfg, uid = state.settings.docs, str(user["id"])
    if body.kind == "answer":
        if not body.messageId:
            raise ApiError(400, "VALIDATION_ERROR", "messageId: this field is required.", {"field": "messageId"})
        return vault.save_answer(state.db, cfg, uid, _uuid(body.messageId, "messageId"))
    if body.kind == "analysis":
        if not body.analysisId:
            raise ApiError(400, "VALIDATION_ERROR", "analysisId: this field is required.", {"field": "analysisId"})
        return vault.save_analysis(state.db, cfg, uid, _uuid(body.analysisId, "analysisId"))
    raise ApiError(422, "UNPROCESSABLE", "Case briefs cannot be saved to the Vault yet.")


def _uuid(value: str, field: str) -> str:
    try:
        return str(UUID(str(value)))
    except ValueError:
        raise ApiError(400, "VALIDATION_ERROR", f"{field}: not a valid id.", {"field": field})


@router.get("/items")
def list_items(category: Literal["all", "answer", "analysis", "brief", "favourites", "trash"] = "all", q: str = Query("", max_length=80),
               sort: Literal["updated_desc", "updated_asc", "name_asc", "name_desc"] = "updated_desc", page: int = Query(1, ge=1, le=10_000),
               pageSize: int | None = Query(None, ge=1, le=100), user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    return vault.list_items(state.db, state.settings.docs, str(user["id"]), category=category, q=q, sort=sort, page=page, page_size=pageSize)


@router.get("/stats")
def stats(user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Part A: `counts` (saved answers and analyses). Part B adds `files` (counts), `storage` and `filesEnabled`."""
    from .. import vault_files
    uid = str(user["id"])
    return {**vault.stats(state.db, uid), **vault_files.stats(state.db, state.settings.docs, uid), "filesEnabled": state.storage is not None}


@router.get("/items/{item_id}")
def get_item(item_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    return vault.get_item(state.db, str(user["id"]), str(item_id))


@router.patch("/items/{item_id}")
def rename_item(item_id: UUID, body: VaultRenameIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    return vault.rename(state.db, str(user["id"]), str(item_id), body.title)


@router.put("/items/{item_id}/favourite", status_code=204)
def favourite_item(item_id: UUID, body: VaultFavouriteIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    vault.set_favourite(state.db, str(user["id"]), str(item_id), body.favourite)
    return Response(status_code=204)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: UUID, permanent: bool = False, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Moves the item to the Trash. `?permanent=true` deletes an item that is already in the Trash for good."""
    _limit(state, user["id"])
    (vault.delete_forever if permanent else vault.trash)(state.db, str(user["id"]), str(item_id))
    return Response(status_code=204)


@router.post("/items/{item_id}/restore", status_code=204)
def restore_item(item_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    vault.restore(state.db, str(user["id"]), str(item_id))
    return Response(status_code=204)


@router.delete("/trash")
def empty_trash(user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    return {"deleted": vault.empty_trash(state.db, str(user["id"]))}


@router.get("/items/{item_id}/notes")
def list_notes(item_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    return {"items": vault.list_notes(state.db, str(user["id"]), str(item_id))}


@router.post("/items/{item_id}/notes", status_code=201)
def add_note(item_id: UUID, body: VaultNoteIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user["id"])
    cfg = state.settings.docs
    if len(body.text) > cfg.vault_note_chars:
        raise ApiError(400, "VALIDATION_ERROR", f"text: a note can be up to {cfg.vault_note_chars} characters.", {"field": "text"})
    return vault.add_note(state.db, cfg, str(user["id"]), str(item_id), body.text)


@router.delete("/items/{item_id}/notes/{note_id}", status_code=204)
def delete_note(item_id: UUID, note_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    vault.delete_note(state.db, str(user["id"]), str(item_id), str(note_id))
    return Response(status_code=204)


@router.get("/items/{item_id}/activity")
def list_activity(item_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    return {"items": vault.list_activity(state.db, str(user["id"]), str(item_id))}
