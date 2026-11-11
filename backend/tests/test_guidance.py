"""Guides, draft letters and the contract check."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import calculators as calc
from app import contract_check as cc
from app import letters, personas
from app.errors import ApiError
from app.main import create_app
from tests.conftest import FakeEngine, MemoryStorage, make_settings, signup
from tests.test_documents import pdf

A = "/api/v1"
TODAY = date(2026, 11, 11)

SAMPLE = {
    "tenant_reply": {"propertyAddress": "Flat 2, Gulberg, Lahore", "noticeDate": "2026-11-01", "reasonInNotice": "He needs the flat for his son"},
    "deposit_demand": {"propertyAddress": "Flat 2, Gulberg, Lahore", "depositAmount": 60000, "paidOn": "2025-01-10", "vacatedOn": "2026-10-31"},
    "payment_notice": {"reason": "Bounced cheque", "amountOwed": 250000, "dateDue": "2026-09-30", "chequeNo": "123456", "bank": "HBL Gulberg", "chequeDate": "2026-09-30"},
    "employer_grievance": {"designation": "Sales executive", "joiningDate": "2024-02-01", "terminationDate": "2026-10-15"},
    "harassment_complaint": {"respondentName": "Mr Raza", "place": "Accounts department", "whenItHappened": "between March and June 2026", "description": "Unwelcome comments."},
    "consumer_notice": {"item": "a washing machine", "purchaseDate": "2026-09-01", "price": 85000, "defect": "It stopped working after two weeks."},
}
COMMON = {"senderName": "Ali Khan", "senderAddress": "House 5, Street 3, Lahore", "recipientName": "Mr Ahmed"}


def fields(letter_id, **extra):
    return {**COMMON, **SAMPLE[letter_id], **extra}


# ------------------------------------------------------------------------------------------------ letters
def test_every_letter_template_renders_a_complete_letter():
    assert set(SAMPLE) == set(letters.LETTERS)
    for lid in letters.LETTERS:
        r = letters.render(lid, fields(lid), TODAY)
        t = r["text"]
        assert t.startswith("11 November 2026") and "Subject: " in t and "Dear Sir or Madam," in t and "Yours faithfully," in t
        assert "Ali Khan" in t and "Mr Ahmed" in t and "None" not in t and "{" not in t, lid
        assert r["subject"] and r["fields"]["senderName"] == "Ali Khan"


def test_letters_say_what_the_user_typed_and_nothing_invented():
    t = letters.render("deposit_demand", fields("deposit_demand", deadlineDays=21), TODAY)["text"]
    assert "PKR 60,000" in t and "10 January 2025" in t and "31 October 2026" in t and "within 21 days" in t
    t = letters.render("payment_notice", fields("payment_notice"), TODAY)["text"]
    assert "number 123456" in t and "HBL Gulberg" in t and "489-F" in t                      # the one section named, checked in the law library
    t = letters.render("payment_notice", fields("payment_notice", reason="Money lent"), TODAY)["text"]
    assert "489-F" not in t and "lent you PKR 250,000" in t
    t = letters.render("tenant_reply", fields("tenant_reply", rentStatus="Some rent is unpaid"), TODAY)["text"]
    assert "outstanding" in t and "paid the rent up to date" not in t
    t = letters.render("employer_grievance", fields("employer_grievance", writtenOrder="Yes"), TODAY)["text"]
    assert "by a written order" in t


def test_letter_input_is_checked():
    def bad(lid, **kw):
        with pytest.raises(ApiError) as e:
            letters.render(lid, {**fields(lid), **kw}, TODAY)
        assert e.value.status == 422
        return str(e.value.message)
    assert "required" in bad("tenant_reply", senderName="  ")
    assert "choose one" in bad("tenant_reply", rentStatus="Whatever")
    assert "year-month-day" in bad("tenant_reply", noticeDate="01/11/2026")
    assert "does not look right" in bad("tenant_reply", noticeDate="1800-01-01")
    assert "enter a number" in bad("deposit_demand", depositAmount="a lot")
    assert "between" in bad("deposit_demand", depositAmount=0)
    assert "shorter" in bad("harassment_complaint", description="x" * 1600)
    with pytest.raises(ApiError) as e:
        letters.render("nope", {}, TODAY)
    assert e.value.status == 404


def test_letter_pdf_is_a_pdf_even_with_non_latin_names():
    out = letters.letter_pdf(letters.render("consumer_notice", fields("consumer_notice", senderName="علی خان"), TODAY)["text"])
    assert out.startswith(b"%PDF") and len(out) > 800


# ------------------------------------------------------------------------------------------------ guides and ranking
def test_guides_are_complete_and_their_tools_exist():
    out = personas.for_you(None)
    assert len(out["personas"]) == 4
    for p in out["personas"]:
        assert 3 <= len(p["guides"]) <= 8 and p["letters"] and p["calculators"], p["key"]
        for c in p["calculators"]:
            assert c["key"] in calc.CALCULATORS and c["why"] and c["recommended"]
        for l in p["letters"]:
            assert l["id"] in letters.LETTERS
        for g in p["guides"]:
            full = personas.guide(g["id"])
            assert 2 <= len(full["questions"]) <= 3 and full["situation"].endswith(".") and full["intro"]
            for q in full["questions"]:
                assert 2 <= len(q["options"]) <= 5 and "other" not in [o.lower() for o in q["options"]]    # the app adds "Other"
            for t in full["tools"]:
                assert t["link"] and t["name"]
                if t["type"] == "calculator":
                    assert t["key"] in calc.CALCULATORS and t["link"] == f"/calculator?type={t['key']}"
                if t["type"] == "letter":
                    assert t["id"] in letters.LETTERS and t["link"] == f"/letters/{t['id']}"
    with pytest.raises(ApiError) as e:
        personas.guide("g_nope")
    assert e.value.status == 404


# ------------------------------------------------------------------------------------------------ contract check
GOOD = ("This Agreement is made between Alpha Traders (the first party) and Beta Services (the second party). The services to be provided are described in the "
        "scope of work. The fee shall be paid by invoice within 30 days. The term of this Agreement starts on the effective date and lasts one year. "
        "Either party may terminate this Agreement with 30 days notice. Each party's liability is limited to the fee paid. Any dispute shall be referred to "
        "arbitration in Lahore and this Agreement is governed by the laws of Pakistan. Signed by both parties in the presence of witnesses. ") * 1


def test_contract_check_finds_clauses_and_warning_phrases():
    r = cc.check(GOOD, "service")
    assert r["ok"] and r["words"] > 40
    found = {c["key"]: c["found"] for c in r["clauses"]}
    assert all(found[k] for k in ("parties", "scope", "payment", "term", "termination", "liability", "dispute", "law", "signatures"))
    assert not found["confidentiality"] and not found["force_majeure"] and r["flags"] == [] and r["level"] == "Low"
    bad = GOOD + ("The Company may terminate this agreement at its sole discretion. The Company reserves the right to amend these terms at any time. "
                  "The Contractor irrevocably waives all claims. This agreement renews automatically. Advance payment is non-refundable. Governed by the laws of England. Date: ______ ")
    r = cc.check(bad, "service")
    keys = {f["key"] for f in r["flags"]}
    assert {"one_sided_exit", "unilateral_change", "waiver", "auto_renew", "non_refundable", "foreign_law", "blanks"} <= keys
    assert all(f["snippet"] and f["why"] and f["question"] for f in r["flags"]) and r["level"] == "High"
    assert any("sole discretion" in f["snippet"] for f in r["flags"] if f["key"] == "one_sided_exit")


def test_missing_expected_clauses_depend_on_the_kind_of_contract():
    text = "This note is between two people about a car. " * 12
    rental = cc.check(text, "rental")
    assert {c["key"] for c in rental["clauses"] if c["expected"] and not c["found"]} >= {"payment", "term", "termination", "stamp", "signatures"}
    assert cc.check(text, "no-such-type")["type"] == "general"                              # an unknown type falls back to the general one
    assert rental["summary"]["missingExpected"] + rental["summary"]["foundExpected"] == rental["summary"]["expected"]


def test_contract_check_refuses_short_or_urdu_text():
    assert cc.check("Too short.")["reason"] == "short"
    urdu = "یہ معاہدہ دو فریقین کے درمیان ہے اور اس کی شرائط درج ذیل ہیں " * 8
    assert cc.check(urdu)["reason"] == "urdu"


# ------------------------------------------------------------------------------------------------ the API
@pytest.fixture(scope="module")
def client(pg_url):
    with TestClient(create_app(make_settings(pg_url), engine=FakeEngine(), storage=MemoryStorage())) as c:
        yield c


def test_guide_and_letter_endpoints(client):
    assert client.get(f"{A}/letters").status_code == 401
    _, h = signup(client)
    g = client.get(f"{A}/guides/g_landlord", headers=h).json()
    assert g["title"] and g["questions"] and {t["type"] for t in g["tools"]} == {"letter", "calculator"}
    assert client.get(f"{A}/guides/g_nope", headers=h).status_code == 404
    assert len(client.get(f"{A}/letters", headers=h).json()["items"]) == 6
    spec = client.get(f"{A}/letters/tenant_reply", headers=h).json()
    assert {f["key"] for f in spec["fields"]} >= {"senderName", "noticeDate", "rentStatus"} and spec["note"]
    r = client.post(f"{A}/letters/tenant_reply/render", json={"fields": fields("tenant_reply")}, headers=h)
    assert r.status_code == 200 and "Ali Khan" in r.json()["text"]
    bad = client.post(f"{A}/letters/tenant_reply/render", json={"fields": {**fields("tenant_reply"), "noticeDate": "nope"}}, headers=h)
    assert bad.status_code == 422 and bad.json()["error"]["details"]["field"] == "noticeDate"
    pdf_r = client.post(f"{A}/letters/consumer_notice/pdf", json={"fields": fields("consumer_notice")}, headers=h)
    assert pdf_r.status_code == 200 and pdf_r.content.startswith(b"%PDF") and pdf_r.headers["content-type"] == "application/pdf"
    assert client.post(f"{A}/letters/nope/render", json={"fields": {}}, headers=h).status_code == 404


def test_a_letter_can_be_saved_to_the_vault_and_downloaded_but_only_by_its_owner(client):
    _, h = signup(client)
    s = client.post(f"{A}/letters/saved", json={"letterId": "deposit_demand", "fields": fields("deposit_demand")}, headers=h)
    assert s.status_code == 201
    item = client.get(f"{A}/vault/items/{s.json()['id']}", headers=h).json()
    assert item["kind"] == "letter" and "Subject:" in item["content"]["text"]
    assert item["content"]["fields"]["depositAmount"] == 60000
    listing = client.get(f"{A}/vault/items?category=letter", headers=h).json()
    assert listing["total"] == 1 and listing["counts"]["letter"] == 1 and listing["counts"]["all"] == 1
    pdf_r = client.get(f"{A}/letters/saved/{s.json()['id']}/pdf", headers=h)
    assert pdf_r.status_code == 200 and pdf_r.content.startswith(b"%PDF")
    _, h2 = signup(client)
    assert client.get(f"{A}/letters/saved/{s.json()['id']}/pdf", headers=h2).status_code == 404
    # a saved calculation is not a letter
    c = client.post(f"{A}/calculators/saved", json={"type": "stamp", "inputs": {"amount": 1_000_000}}, headers=h).json()
    assert client.get(f"{A}/letters/saved/{c['id']}/pdf", headers=h).status_code == 404
    # the browser cannot make the server store text it wrote itself
    assert client.post(f"{A}/letters/saved", json={"letterId": "deposit_demand", "fields": {**fields("deposit_demand"), "text": "FAKE"}}, headers=h).status_code == 201
    texts = [client.get(f"{A}/vault/items/{i['id']}", headers=h).json()["content"]["text"] for i in client.get(f"{A}/vault/items?category=letter", headers=h).json()["items"]]
    assert all("FAKE" not in t for t in texts)


def test_contract_check_endpoint(client):
    _, h = signup(client)
    assert client.get(f"{A}/contract-check", headers=h).json()["types"][0]["key"] == "general"
    lines = [GOOD[i:i + 90] for i in range(0, len(GOOD), 90)]
    up = client.post(f"{A}/documents", files={"file": ("contract.pdf", pdf(lines), "application/pdf")}, data={"purpose": "analysis"}, headers=h)
    assert up.status_code == 201
    r = client.post(f"{A}/contract-check", json={"documentId": up.json()["id"], "contractType": "service"}, headers=h)
    assert r.status_code == 200 and r.json()["document"]["name"] == "contract.pdf" and r.json()["summary"]["foundExpected"] >= 6
    _, h2 = signup(client)
    assert client.post(f"{A}/contract-check", json={"documentId": up.json()["id"]}, headers=h2).status_code == 404       # not theirs
    short = client.post(f"{A}/documents", files={"file": ("tiny.pdf", pdf(["This short note is between two friends about selling a car.", "It was written on a single line and has no further terms."]), "application/pdf")}, data={"purpose": "analysis"}, headers=h)
    assert client.post(f"{A}/contract-check", json={"documentId": short.json()["id"]}, headers=h).status_code == 422


def test_the_dashboard_carries_the_guides_and_letters_of_each_kind_of_user(client):
    _, h = signup(client)
    d = client.get(f"{A}/dashboard", headers=h).json()["forYou"]
    for p in d["personas"]:
        assert p["guides"] and p["letters"], p["key"]
        assert all(set(g) == {"id", "title", "text", "icon"} for g in p["guides"])
        assert all(client.get(f"{A}/guides/{g['id']}", headers=h).status_code == 200 for g in p["guides"])
