"""Shared test setup: a throw-away local Postgres (no Docker, no Supabase) and an API wired to a scripted fake chat engine.

Nothing here touches DeepSeek or the real database.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import AppSettings  # noqa: E402
from app.main import create_app  # noqa: E402

SECRET = "test-secret-" + "x" * 40


@pytest.fixture(scope="session")
def pg_url():
    import pgserver
    d = Path(tempfile.mkdtemp(prefix="legalmate_pg_"))
    srv = pgserver.get_server(d, cleanup_mode="stop")
    yield srv.get_uri()
    try:
        srv.cleanup()
    finally:
        shutil.rmtree(d, ignore_errors=True)


class FakeEngine:
    """Same interface as chat.engine.ChatEngine.respond; behaviour chosen by words in the question."""

    def __init__(self):
        self.calls: list[dict] = []

    def respond(self, text, *, history=None, profile=None, language="en", attachment_text=None, on_status=None):
        self.calls.append({"text": text, "history": history or [], "profile": profile, "language": language, "attachment_text": attachment_text})
        status = on_status or (lambda s: None)
        status("understanding")
        low = text.lower()
        info = lambda reason, t: {"message": {"role": "assistant", "kind": "info", "reason": reason, "createdAt": "x", "text": t, "content": t, "confidence": None},
                                  "conversation": None, "meta": {"seconds": 0.0}}
        if "hello" in low:
            return info("greeting", "Hello! Ask me about Pakistani law.")
        if "fail" in low:
            return info("error", "I can't answer right now. Please try again in a few minutes.")
        if "busy" in low:
            return info("busy", "LegalMate has reached its answer limit for today. Please try again tomorrow.")
        if "boom" in low:
            raise RuntimeError("engine exploded")
        if "vague" in low:
            q = [{"id": "q1", "text": "Are you the tenant or the landlord?", "options": ["Tenant", "Landlord"]}]
            return {"message": {"role": "assistant", "kind": "clarify", "createdAt": "x", "intro": "I need more information.", "questions": q,
                                "confidence": None, "content": "I need more information. Are you the tenant or the landlord?"},
                    "conversation": {"title": "Housing problem", "tag": "Property Law"}, "meta": {"seconds": 0.1}}
        status("searching_sources")
        status("writing_answer")
        msg = {"role": "assistant", "kind": "answer", "createdAt": "x", "language": language, "sufficient": True,
               "intro": ["In general, rent can only change ", {"b": "by agreement"}, ". ", {"cite": 1}], "lawTitle": "What the law says",
               "law": ["Section 9 applies. ", {"cite": 1}], "steps": [["Check your agreement."]], "important": "Keep records.", "outro": "",
               "sources": [{"id": 1, "title": "Punjab Rented Premises Act, 2009", "section": "Section 9", "type": "Act",
                            "quote": "“rent shall not be increased”", "quoteVerified": True, "url": None, "pages": "p. 4",
                            "jurisdiction": "Punjab", "status": "in_force", "note": None}],
               "confidence": {"score": 82, "relevance": 90, "agreement": 80, "recency": 70, "checked": 4, "verifiedAt": "x"},
               "followUps": [], "disclaimer": "General information.", "feedback": None, "content": "In general, rent can only change by agreement."}
        return {"message": msg, "conversation": {"title": "Rent increase rules", "tag": "Property Law"}, "meta": {"seconds": 0.2, "llm_calls_this_turn": 2}}


def make_settings(pg_url: str, **over) -> AppSettings:
    base = dict(database_url=pg_url, jwt_secret=SECRET, warm_engine=False, engine_concurrency=2, db_pool_max=4,
                cors_origins=("http://localhost:5173",))
    base.update(over)
    return AppSettings(**base)


@pytest.fixture(scope="module")
def engine():
    return FakeEngine()


@pytest.fixture(scope="module")
def client(pg_url, engine):
    with TestClient(create_app(make_settings(pg_url), engine=engine)) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_limits(request):
    c = request.node.funcargs.get("client")
    if c is not None:
        c.app.state.ctx.limiter.reset()
        c.app.state.ctx.inflight.clear()
    yield


# ---- helpers used by the tests ---------------------------------------------------------------------------------
def email() -> str:
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


PASSWORD = "Str0ng!pass"


def signup(client: TestClient, addr: str | None = None, **extra):
    body = {"fullName": "Test User", "email": addr or email(), "password": PASSWORD, "acceptedTerms": True, **extra}
    r = client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 201, r.text
    j = r.json()
    return j, {"Authorization": f"Bearer {j['accessToken']}"}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.split("\n\n"):
        ev, data = None, []
        for line in block.splitlines():
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
        if ev:
            events.append((ev, json.loads("\n".join(data))))
    return events


def ask(client: TestClient, headers: dict, conv_id: str, content: str, **extra):
    r = client.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"content": content, **extra}, headers=headers)
    return r, (parse_sse(r.text) if r.headers.get("content-type", "").startswith("text/event-stream") else [])


def new_conv(client: TestClient, headers: dict, first: str = "Can my landlord raise the rent?", topic: str | None = None) -> dict:
    r = client.post("/api/v1/chat/conversations", json={"firstMessage": first, "topic": topic}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["conversation"]
