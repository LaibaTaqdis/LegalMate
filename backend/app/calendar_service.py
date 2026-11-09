"""Court holidays and vacations (data in app/reference/court_calendar.json) and the question "is this court closed that day?".

The data comes from news reports of official notifications and carries a status per entry (notified, reported, expected), its source and
the date it was collected. Nothing here pretends to be the official calendar: the dashboard says so, and links the source.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "reference" / "court_calendar.json"


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def reload() -> None:
    _data.cache_clear()


def _d(s: str) -> date:
    return date.fromisoformat(s)


def meta() -> dict:
    d = _data()
    return {"verifiedOn": d["verifiedOn"], "note": d["note"], "courts": d["courts"], "notYetAnnounced": d["notYetAnnounced"]}


def entries_out(e: dict, today: date) -> dict:
    start, end = _d(e["start"]), _d(e["end"])
    return {"id": e["id"], "title": e["title"], "kind": e["kind"], "courts": e["courts"], "courtNames": [_data()["courts"][c] for c in e["courts"]],
            "start": e["start"], "end": e["end"], "days": (end - start).days + 1, "status": e["status"], "source": e["source"], "url": e["url"] or None,
            "ongoing": start <= today <= end, "daysUntil": max(0, (start - today).days)}


def upcoming(today: date | None = None, limit: int = 6, court: str | None = None) -> list[dict]:
    """Entries that have not finished yet, soonest first (ones happening today come first). `court`: lhc | ihc | sc | fcc keeps that court's entries and the public holidays."""
    today = today or date.today()
    out = [e for e in _data()["entries"] if _d(e["end"]) >= today and (court is None or court in e["courts"] or "all" in e["courts"])]
    out.sort(key=lambda e: (_d(e["start"]), e["end"]))
    return [entries_out(e, today) for e in out[: max(1, limit)]]


def all_entries(today: date | None = None, court: str | None = None) -> list[dict]:
    today = today or date.today()
    out = [e for e in _data()["entries"] if court is None or court in e["courts"] or "all" in e["courts"]]
    out.sort(key=lambda e: _d(e["start"]))
    return [entries_out(e, today) for e in out]


def closed_on(day: date, court: str = "all") -> str | None:
    """Why the court's doors are closed on `day` (a Sunday or a public holiday), or None. Vacations are NOT a closure here: during a vacation the
    court's offices stay open and urgent matters are heard, so section 4 of the Limitation Act (court closed when the period ends) does not
    move a deadline for them."""
    if day.weekday() == 6:
        return "Sunday"
    for e in _data()["entries"]:
        if e["kind"] == "holiday" and _d(e["start"]) <= day <= _d(e["end"]) and ("all" in e["courts"] or court in e["courts"]):
            return e["title"]
    return None


def next_open_day(day: date, court: str = "all") -> tuple[date, list[str]]:
    reasons: list[str] = []
    while (why := closed_on(day, court)) is not None:
        reasons.append(f"{day.strftime('%d %b %Y')}: {why}")
        day += timedelta(days=1)
    return day, reasons


def vacation_on(day: date, court: str) -> dict | None:
    for e in _data()["entries"]:
        if e["kind"] == "vacation" and _d(e["start"]) <= day <= _d(e["end"]) and court in e["courts"]:
            return e
    return None
