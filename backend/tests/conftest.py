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


def _row(act, jur, label, heading, body, nums=None, unit="section", status="unverified", amended=()):
    return {"act_title": act, "jurisdiction": jur, "section_label": label, "heading": heading, "body": body, "section_nums": nums or [label.split()[-1]],
            "unit_type": unit, "legal_status": status, "status_scope": None, "amended_by_titles": list(amended), "source_urls": [f"https://example.test/{act[:4]}.pdf"]}


# a few real sections (headings as stored in the law library), enough to exercise the resolver
LAW = {
    ("Contract act, 1872", "74"): _row("Contract act, 1872", "Federal", "Section 74", "Compensation for breach of contract where penalty stipulated for",
                                       "74. Compensation for breach of contract where penalty stipulated for. When a contract has been broken, if a sum is named in the contract "
                                       "as the amount to be paid in case of such breach, the party complaining is entitled to receive reasonable compensation not exceeding the amount so named."),
    ("Contract act, 1872", "10"): _row("Contract act, 1872", "Federal", "Section 10", "What agreements are contracts",
                                       "10. What agreements are contracts. All agreements are contracts if they are made by the free consent of parties competent to contract."),
    ("Contract act, 1872", "27"): _row("Contract act, 1872", "Federal", "Section 26 to 27", "Agreement in restraint of marriage void; Agreement in restraint of trade void",
                                       "26. Agreement in restraint of marriage void. Every agreement in restraint of the marriage of any person is void.\n27. Agreement in restraint of trade void. "
                                       "Every agreement by which any one is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void.",
                                       nums=["26", "27"]),
    ("Punjab Rented Premises Act, 2009", "15"): _row("Punjab Rented Premises Act, 2009", "Punjab", "Section 15", "Grounds for eviction",
                                                     "15. Grounds for eviction.– A landlord may seek eviction of the tenant only on the grounds of default in payment of rent, subletting, or personal need.",
                                                     amended=["Punjab Rented Premises (Amendment) Act, 2025"]),
    ("Islamabad Rent Restriction Ordinance, 2001", "17"): _row("Islamabad Rent Restriction Ordinance, 2001", "ICT", "Section 17", "Eviction of tenant",
                                                                "17. Eviction of tenant.– A tenant shall not be evicted except in accordance with this section."),
    ("Transfer of Property Act, 1882", "106"): _row("Transfer of Property Act, 1882", "Federal", "Section 106", "Duration of certain leases in absence of written contract or local usage",
                                                    "106. Duration of certain leases in absence of written contract or local usage. In the absence of a contract or local law or usage to the contrary, "
                                                    "a lease of immovable property for agricultural or manufacturing purposes shall be deemed to be a lease from year to year."),
    ("Transfer of Property Act, 1882", "111"): _row("Transfer of Property Act, 1882", "Federal", "Section 111", "Determination of lease", "111. Determination of lease. A lease of immovable property determines by efflux of the time limited thereby.", status="repealed"),
    ("Transfer of Property Act, 1882", "105"): _row("Transfer of Property Act, 1882", "Federal", "Section 105", "Lease defined", "105. Lease defined. A lease of immovable property is a transfer of a right to enjoy such property."),
}


class FakeKB:
    """get_section like the real KnowledgeBase: exact title, first preferred jurisdiction that has it, None if absent."""

    def __init__(self, fail=False):
        self.fail, self.asked = fail, []

    def get_section(self, act, section, jurisdictions):
        self.asked.append((act, section, tuple(jurisdictions)))
        if self.fail:
            raise ConnectionError("law library unreachable")
        row = LAW.get((act, section))
        return dict(row) if row and row["jurisdiction"] in jurisdictions else None


class FakeLLM:
    """Stands in for DeepSeek in document analysis. It quotes the document it is given, and cheats on purpose when told to."""

    def __init__(self):
        self.calls: list[list[dict]] = []

    def complete(self, messages, *, tag, max_tokens=800, temperature=0.1, **kw):
        import re
        from chat.llm import BudgetExceeded
        self.calls.append(messages)
        doc = re.search(r"<document>\n(.*?)\n</document>", messages[-1]["content"], re.S).group(1)
        if "TRIGGER_BUDGET" in doc:
            raise BudgetExceeded("cap")
        if "TRIGGER_BADJSON" in doc:
            return type("R", (), {"text": "not json at all"})()
        lines = [l for l in re.split(r"(?<=[.!])\s+|\n", doc) if len(l.strip()) > 25 and not l.startswith("[Page")]
        out = {"documentType": "Tenancy Agreement", "category": "tenancy", "jurisdiction": "Punjab" if "Lahore" in doc else "Unknown", "overallRisk": {"level": "Low", "note": ""},
               "summary": "A twelve month rental agreement.",
               "clauses": [{"title": "Rent", "reference": "Clause 3", "risk": "Low", "summary": "Rent is due monthly.", "detail": "You pay every month.", "quote": lines[0].strip(), "topics": ["rent_payment", "not_a_real_topic"]},
                           {"title": "Termination", "reference": "Clause 6", "risk": "High", "summary": "The landlord may end it quickly.",
                            "detail": "Notice of 99999 days is not what the text says.", "quote": "the landlord may throw you out whenever he likes", "topics": ["eviction", "penalty_clause"]}],
               "risks": [{"title": "Short notice", "description": "Little time to move.", "level": "High", "quote": lines[-1].strip()}],
               "obligations": ["Pay rent on time."], "importantDates": ["1 January 2026 - start"], "missingInformation": ["Inventory list"],
               "recommendedActions": ["Ask to extend the notice period."]}
        import json
        return type("R", (), {"text": json.dumps(out)})()


class FakeEngine:
    """Same interface as chat.engine.ChatEngine.respond; behaviour chosen by words in the question."""

    def __init__(self):
        self.calls: list[dict] = []
        self.llm = FakeLLM()
        self.kb = FakeKB()

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
