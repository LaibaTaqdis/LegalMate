"""The "For you" part of the dashboard: ready-made questions, step-by-step guides, draft letters and a ranked list of calculators per kind of user
(young adult, student, business owner, citizen).

The content is in app/reference/personas.json. A card never states the law: it opens a chat with a ready question, so the answer is written from the
law library with its sources. `basis` names the Acts that were checked to be in the library (and to come up for that question) on `verifiedOn`.
The kind of user comes from the Personalise profile (`userType`); every user can still open the other tabs.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from . import calculators, letters
from .errors import not_found

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


def guide_cards(ids: list[str]) -> list[dict]:
    by_id = {g["id"]: g for g in _data()["guides"]}
    return [{"id": i, "title": by_id[i]["title"], "text": by_id[i]["text"], "icon": by_id[i]["icon"]} for i in ids]


def guide(guide_id: str) -> dict:
    g = next((x for x in _data()["guides"] if x["id"] == guide_id), None)
    if g is None:
        raise not_found("That guide")
    tools = []
    for t in g["tools"]:
        if t["type"] == "calculator":
            tools.append({**t, "name": calculators.CALCULATORS[t["key"]]["name"], "link": f"/calculator?type={t['key']}"})
        elif t["type"] == "letter":
            tools.append({**t, "name": letters.LETTERS[t["id"]]["title"], "link": f"/letters/{t['id']}"})
        else:
            tools.append({**t, "name": "Contract check", "link": "/contract-check"})
    return {**g, "tools": tools, "note": "These steps come from the law library with its sources. They are information, not legal advice."}


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
        cal = calculators_for(p["userType"])
        personas.append({"key": p["key"], "userType": p["userType"], "title": p["title"], "subtitle": p["subtitle"],
                         "topics": [{"id": t["id"], "title": t["title"], "text": t["text"], "icon": t["icon"], "action": t["action"],
                                     "question": t.get("question"), "link": t.get("link"), "basis": t["basis"]} for t in p["topics"]],
                         "checklist": checklist, "guides": guide_cards(p.get("guides", [])),
                         "letters": [{"id": i, "title": letters.LETTERS[i]["title"], "summary": letters.LETTERS[i]["summary"]} for i in p.get("letters", [])],
                         "calculators": [c for c in cal if c["recommended"]]})
    return {"selected": selected_for(user_type), "verifiedOn": d["verifiedOn"], "note": d["note"], "personas": personas}
