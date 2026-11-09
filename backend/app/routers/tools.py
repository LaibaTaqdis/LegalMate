"""Legal calculators, the court calendar and the dashboard."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import Field

from .. import calculators, calendar_service, dashboard, vault
from ..deps import current_user, get_state
from ..errors import ApiError, not_found
from ..schemas import Body
from ..state import AppState

router = APIRouter(tags=["tools"])


class CalcIn(Body):
    inputs: dict[str, Any] = Field(default_factory=dict)


class CalcSaveIn(Body):
    type: str = Field(max_length=30)
    inputs: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------------------------- calculators
@router.get("/calculators")
def list_calculators(_: dict = Depends(current_user)):
    """Which calculators exist, how far each can be trusted (`law` or `reported`), when its data was checked, and which one is not offered and why."""
    return calculators.meta()


@router.post("/calculators/saved", status_code=201)
def save_calculation(body: CalcSaveIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Saves a calculation to the Legal Vault. The result is worked out again here from the inputs: a result sent by the browser is never stored."""
    state.limiter.check(f"calc:{user['id']}", 60, 60, "You are doing that very quickly. Please wait a moment.")
    result = calculators.calculate(body.type, body.inputs)
    name = calculators.CALCULATORS[body.type]["name"]
    return vault.save_calculation(state.db, state.settings.docs, str(user["id"]), body.type, name, body.inputs, result)


@router.get("/calculators/saved/{item_id}/summary")
def calculation_summary(item_id: UUID, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    item = vault.get_item(state.db, str(user["id"]), str(item_id))
    if item["kind"] != "calculation":
        raise not_found("That calculation")
    pdf = calculators.summary_pdf(item["title"], item["content"]["result"], item["content"]["inputs"], item["savedAt"])
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="Calculation_Summary.pdf"'})


@router.post("/calculators/{kind}/calculate")
def calculate(kind: str, body: CalcIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    state.limiter.check(f"calc:{user['id']}", 60, 60, "You are calculating very quickly. Please wait a moment.")
    return calculators.calculate(kind, body.inputs)


# ---------------------------------------------------------------------------------------------- court calendar
@router.get("/calendar/court-holidays")
def court_holidays(limit: int = Query(6, ge=1, le=60), court: str | None = Query(None, pattern="^(lhc|ihc|sc|fcc)$"), all: bool = False, _: dict = Depends(current_user)):
    """Upcoming court holidays and vacations (or the whole list with `all=true`). Each entry carries a status (notified, reported, expected) and its source."""
    items = calendar_service.all_entries(court=court) if all else calendar_service.upcoming(limit=limit, court=court)
    return {"items": items, **calendar_service.meta()}


# ---------------------------------------------------------------------------------------------- dashboard
@router.get("/dashboard")
def get_dashboard(user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    return dashboard.build(state.db, state.settings.docs, str(user["id"]), state.storage is not None)
