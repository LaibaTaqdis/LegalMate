"""Step-by-step guides, draft letters and the contract check (the tools behind the dashboard's "For you" section)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import Field

from .. import contract_check, docs_service, letters, personas, vault
from ..deps import current_user, get_state
from ..errors import ApiError, not_found
from ..schemas import Body
from ..state import AppState

router = APIRouter(tags=["guidance"])


class LetterIn(Body):
    fields: dict[str, Any] = Field(default_factory=dict)


class LetterSaveIn(Body):
    letterId: str = Field(max_length=40)
    fields: dict[str, Any] = Field(default_factory=dict)


class ContractIn(Body):
    documentId: UUID
    contractType: str = Field("general", max_length=20)


def _limit(state: AppState, user: dict) -> None:
    state.limiter.check(f"guidance:{user['id']}", 90, 60, "You are doing that very quickly. Please wait a moment.")


# ---------------------------------------------------------------------------------------------- guides
@router.get("/guides/{guide_id}")
def get_guide(guide_id: str, _: dict = Depends(current_user)):
    """One step-by-step guide: its questions (the app adds an "Other" box), the situation sentence, and the tools that help (calculator, letter, contract check)."""
    return personas.guide(guide_id)


# ---------------------------------------------------------------------------------------------- letters
@router.get("/letters")
def list_letters(_: dict = Depends(current_user)):
    return {"items": letters.catalog()}


@router.post("/letters/saved", status_code=201)
def save_letter(body: LetterSaveIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Saves a drafted letter to the Legal Vault. The letter is built again here from the facts: text sent by the browser is never stored."""
    _limit(state, user)
    return vault.save_letter(state.db, state.settings.docs, str(user["id"]), body.letterId, letters.render(body.letterId, body.fields))


@router.get("/letters/saved/{item_id}/pdf")
def saved_letter_pdf(item_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    item = vault.get_item(state.db, str(user["id"]), str(item_id))
    if item["kind"] != "letter":
        raise not_found("That letter")
    return Response(letters.letter_pdf(item["content"]["text"]), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="Draft_Letter.pdf"'})


@router.get("/letters/{letter_id}")
def get_letter(letter_id: str, _: dict = Depends(current_user)):
    return letters.spec(letter_id)


@router.post("/letters/{letter_id}/render")
def render_letter(letter_id: str, body: LetterIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user)
    return letters.render(letter_id, body.fields)


@router.post("/letters/{letter_id}/pdf")
def letter_pdf(letter_id: str, body: LetterIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    _limit(state, user)
    return Response(letters.letter_pdf(letters.render(letter_id, body.fields)["text"]), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="Draft_Letter.pdf"'})


# ---------------------------------------------------------------------------------------------- contract check
@router.get("/contract-check")
def contract_check_options(_: dict = Depends(current_user)):
    return contract_check.meta()


@router.post("/contract-check")
def run_contract_check(body: ContractIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Checks an uploaded document's wording for the usual clauses and for warning phrases. No model is called."""
    _limit(state, user)
    doc = docs_service.load_owned(state.db, str(user["id"]), [str(body.documentId)], with_text=True)[0]
    if doc.get("status") == "pending":
        raise ApiError(422, "UNPROCESSABLE", "That photo has not been read yet. Upload it again on this page.")
    out = contract_check.check(doc.get("text") or "", body.contractType)
    if not out["ok"]:
        raise ApiError(422, "UNPROCESSABLE", out["message"])
    return {**out, "document": {"id": str(doc["id"]), "name": doc["name"], "pages": doc["pages"]}}
