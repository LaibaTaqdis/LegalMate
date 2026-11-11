"""The "For you" part of the dashboard: ready-made questions, a checklist and a ranked list of calculators per kind of user
(young adult, student, business owner, citizen).

The content is in app/reference/personas.json. A card never states the law: it opens a chat with a ready question, so the answer is written from the
law library with its sources. `basis` names the Acts that were checked to be in the library (and to come up for that question) on `verifiedOn`.
The kind of user comes from the Personalise profile (`userType`); every user can still open the other tabs.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from . import calculators

DATA = Path(__file__).resolve().parent / "reference" / "personas.json"
DEFAULT = "citizen"


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _persona(key: str) -> dict:
    return next(p for p in _data()["personas"] if p["key"] == key)


def selected_for(user_type: str | None) -> str:
    for p in _data()["personas"]:
        if p["userType"] == user_type:
            return p["key"]
    return DEFAULT


def calculators_for(user_type: str | None) -> list[dict]:
    """The calculators ranked for this kind of user, first = most useful, each with one line on why. The rest follow in their usual order."""
    ranked = _persona(selected_for(user_type)).get("calculators", [])
    seen = {c["key"] for c in ranked}
    rest = [{"key": k, "why": None} for k in calculators.CALCULATORS if k not in seen]
    return [{"key": c["key"], "name": calculators.CALCULATORS[c["key"]]["name"], "why": c["why"], "recommended": c["why"] is not None} for c in ranked + rest]


def for_you(user_type: str | None) -> dict:
    d = _data()
    personas = []
    for p in d["personas"]:
        topics = {t["id"]: t for t in p["topics"]}
        checklist = []
        for c in p.get("checklist", []):
            item = {"id": c["id"], "text": c["text"], "question": None, "link": c.get("link")}
            if c.get("ask"):
                item["question"] = topics[c["ask"]]["question"]
            checklist.append(item)
        personas.append({"key": p["key"], "userType": p["userType"], "title": p["title"], "subtitle": p["subtitle"],
                         "topics": [{"id": t["id"], "title": t["title"], "text": t["text"], "icon": t["icon"], "action": t["action"],
                                     "question": t.get("question"), "link": t.get("link"), "basis": t["basis"]} for t in p["topics"]],
                         "checklist": checklist,
                         "calculators": [c for c in calculators_for(p["userType"]) if c["recommended"]]})
    return {"selected": selected_for(user_type), "verifiedOn": d["verifiedOn"], "note": d["note"], "personas": personas}
