"""Related laws on an analysis: the reviewed table, the resolver, jurisdictions, failure handling, and a guard against the real law library.

    python -m pytest tests/test_law_refs.py -q
    LEGALMATE_LIVE_TESTS=1 python -m pytest tests/test_law_refs.py -q -k real_library     (checks the table against Supabase: needs DATABASE_URL)
"""
from __future__ import annotations

import os
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import law_refs as L
from app.config import DocSettings
from app.main import create_app
from tests.conftest import FakeEngine, FakeKB, make_settings, signup
from tests.test_documents import CONTRACT, pdf, upload, wait_for

A = "/api/v1"


def titles(cites):
    return [(c["title"], c["reference"].split(" - ")[0]) for c in cites]


# ---------------------------------------------------------------------------------------------- the table itself
def test_table_is_consistent():
    assert set(L.CATEGORIES) >= {"tenancy", "employment", "property", "loan", "business", "contract", "notice", "court", "other"}
    for key, (label, hint, refs) in {**L.TOPICS, **L.CATEGORIES}.items():
        assert label and hint and isinstance(refs, tuple), key
        for ref in refs:
            assert ref.act and ref.sections and all(isinstance(s, str) and s for s in ref.sections) and ref.applies, (key, ref)
            assert ref.applies == (L.ALL,) or set(ref.applies) <= {"Punjab", "ICT"}, (key, ref)
    # province laws are never offered for the other territory: Punjab tenancy law only for Punjab, the Islamabad ordinance only for ICT
    assert all(r.applies == ("Punjab",) for r in L.TOPICS["subletting"][2]) and all(r.applies == ("ICT",) for r in L.TOPICS["rent_increase"][2])
    assert "security_deposit" not in L.TOPICS                          # no section governs it: deliberately nothing is shown
    assert "contract_basics:" in L.topic_prompt() or "contract_basics" in L.topic_prompt()


def test_quote_cuts_the_right_section_out_of_a_combined_chunk():
    row = FakeKB().get_section("Contract act, 1872", "27", ["Federal"])
    quote = L._quote(row["body"], "27", 400, L._heading(row, "27"))
    assert L._heading(row, "27") == "Agreement in restraint of trade void" and L._heading(row, "26") == "Agreement in restraint of marriage void"
    assert quote.startswith("Every agreement by which any one is restrained") and "marriage" not in quote
    long = L._quote("1. " + "The tenant shall pay rent. " * 40, "1", 100)
    assert long.endswith("…") and len(long) <= 110 and not long.startswith("1.")


# ---------------------------------------------------------------------------------------------- the resolver
CLAUSES = [("c1", ["penalty_clause"], "Medium"), ("c2", ["eviction", "not_in_fake_library"], "High")]


def test_punjab_document_gets_punjab_law_and_the_general_law_with_real_text():
    cites, by_clause, notes = L.resolve(FakeKB(), category="tenancy", clause_topics=CLAUSES, jurisdiction="Punjab")
    got = titles(cites)
    assert ("Punjab Rented Premises Act, 2009", "Section 15") in got and ("Contract act, 1872", "Section 74") in got
    assert ("Islamabad Rent Restriction Ordinance, 2001", "Section 17") not in got                    # the other territory's law is not offered
    pr = next(c for c in cites if c["title"].startswith("Punjab Rented"))
    assert pr["reference"] == "Section 15 - Grounds for eviction" and pr["jurisdiction"] == "Punjab" and pr["type"] == "Act" and pr["url"]
    assert pr["quote"].startswith("A landlord may seek eviction") and pr["clauseIds"] == ["c2"] and pr["topics"] == ["Eviction and ending a tenancy"]
    assert "Amended later by Punjab Rented Premises (Amendment) Act, 2025" in pr["note"] and "check the current law" in pr["note"]
    tpa = next(c for c in cites if c["reference"].startswith("Section 111"))
    assert "repealed" in tpa["note"]                                                                  # a repealed section carries a warning
    assert by_clause["c1"] and by_clause["c2"] and set(by_clause["c2"]) <= {c["id"] for c in cites}
    assert [c["id"] for c in cites] == [f"l{i}" for i in range(1, len(cites) + 1)] and notes == []
    # the highest-risk clause's laws come first
    assert cites[0]["clauseIds"] == ["c2"] or "c2" in cites[0]["clauseIds"]


def test_islamabad_document_gets_the_islamabad_ordinance_instead():
    cites, _, _ = L.resolve(FakeKB(), category="tenancy", clause_topics=[("c1", ["eviction"], "High")], jurisdiction="ICT")
    got = titles(cites)
    assert ("Islamabad Rent Restriction Ordinance, 2001", "Section 17") in got and not any(t.startswith("Punjab Rented") for t, _ in got)


def test_unknown_jurisdiction_shows_no_provincial_law_and_says_why():
    kb = FakeKB()
    cites, _, notes = L.resolve(kb, category="tenancy", clause_topics=CLAUSES, jurisdiction=None)
    got = titles(cites)
    assert ("Contract act, 1872", "Section 74") in got and ("Transfer of Property Act, 1882", "Section 106") in got
    assert not any("Rented Premises" in t or "Rent Restriction" in t for t, _ in got)
    assert any("province" in n and "profile" in n for n in notes)
    assert not any(a[0].startswith(("Punjab Rented", "Islamabad Rent")) for a in kb.asked)           # provincial laws were not even looked up


def test_limits_unknown_topics_missing_sections_and_library_failures():
    cites, by_clause, _ = L.resolve(FakeKB(), category="tenancy", clause_topics=CLAUSES, jurisdiction="Punjab", max_total=2, per_clause=1)
    assert len(cites) == 2 and all(len(v) <= 2 for v in by_clause.values()) and set(sum(by_clause.values(), [])) <= {c["id"] for c in cites}
    # the box limit never leaves a clause without the main law that matches it
    three = [("c1", ["penalty_clause"], "High"), ("c2", ["eviction"], "High"), ("c3", ["non_compete"], "Low"), ("c4", ["contract_basics"], "Low")]
    cites, by_clause, _ = L.resolve(FakeKB(), category="tenancy", clause_topics=three, jurisdiction="Punjab", max_total=2, per_clause=1)
    assert set(by_clause) == {"c1", "c2", "c3", "c4"} and len(cites) >= 4 and all(by_clause[c] for c in by_clause)
    assert L.resolve(FakeKB(), category="court", clause_topics=[("c1", ["subletting"], "Low")], jurisdiction="Punjab")[0] == []   # not in the fake library: shown nothing
    cites, by_clause, _ = L.resolve(FakeKB(fail=True), category="tenancy", clause_topics=CLAUSES, jurisdiction="Punjab")
    assert cites == [] and by_clause == {}                                                           # library unreachable: no crash, no laws
    assert L.resolve(FakeKB(), category=None, clause_topics=[], jurisdiction="Punjab")[0] == []


def test_a_non_contract_document_does_not_get_contract_law_by_default():
    cites, _, _ = L.resolve(FakeKB(), category="court", clause_topics=[], jurisdiction="Punjab")
    assert cites == []
    cites, _, _ = L.resolve(FakeKB(), category="contract", clause_topics=[], jurisdiction="Punjab")
    assert titles(cites) == [("Contract act, 1872", "Section 10")]


# ---------------------------------------------------------------------------------------------- through the whole analysis
def app_with(pg_url, **docs):
    return create_app(make_settings(pg_url, docs=replace(DocSettings(), **docs)), engine=FakeEngine())


def analyse(c, h, text_lines):
    d = upload(c, h, pdf(text_lines)).json()["id"]
    aid = c.post(f"{A}/analyses", json={"documentIds": [d]}, headers=h).json()["id"]
    return wait_for(c, h, aid)


def test_analysis_carries_laws_linked_to_its_clauses(pg_url):
    with TestClient(app_with(pg_url)) as c:
        _, h = signup(c)
        a = analyse(c, h, CONTRACT + ["The premises are situated in Lahore, Punjab."])                  # the document names Lahore: the fake model says Punjab
        assert a["status"] == "completed" and a["jurisdiction"] == "Punjab" and a["citationsNote"] and "do not say whether your" in a["citationsNote"]
        ids = {x["id"] for x in a["citations"]}
        assert ("Punjab Rented Premises Act, 2009", "Section 15") in titles(a["citations"])
        assert a["clauses"][1]["lawRefs"] and set(a["clauses"][1]["lawRefs"]) <= ids
        assert any(x["clauseIds"] for x in a["citations"]) and any(not x["clauseIds"] for x in a["citations"])       # clause-linked laws and whole-document laws
        assert all(x["quote"] and x["title"] and x["reference"].startswith("Section") for x in a["citations"])
        assert not any("database" in x["quote"].lower() for x in a["citations"])


def test_profile_province_is_used_when_the_document_does_not_say(pg_url):
    with TestClient(app_with(pg_url)) as c:
        j, h = signup(c)
        a = analyse(c, h, CONTRACT)                                                                   # no place named: the fake model says "Unknown"
        assert a["jurisdiction"] is None and not any("Rented Premises" in x["title"] for x in a["citations"]) and any("province" in n for n in a["notes"])
        c.put(f"{A}/users/me/profile", json={"province": "Islamabad Capital Territory"}, headers=h)
        a = analyse(c, h, CONTRACT)
        assert a["jurisdiction"] == "ICT" and ("Islamabad Rent Restriction Ordinance, 2001", "Section 17") in titles(a["citations"])


def test_laws_can_be_switched_off_and_a_library_failure_never_loses_the_analysis(pg_url):
    with TestClient(app_with(pg_url, law_refs_enabled=False)) as c:
        _, h = signup(c)
        a = analyse(c, h, CONTRACT)
        assert a["status"] == "completed" and a["citations"] == [] and all(cl["lawRefs"] == [] for cl in a["clauses"])
    eng = FakeEngine()
    eng.kb = FakeKB(fail=True)
    with TestClient(create_app(make_settings(pg_url), engine=eng)) as c:
        _, h = signup(c)
        a = analyse(c, h, CONTRACT)
        assert a["status"] == "completed" and a["citations"] == [] and a["clauses"] and a["summary"]


def test_environment_settings_for_laws(monkeypatch):
    from app.config import load_doc_settings
    monkeypatch.setenv("LAW_REFS_ENABLED", "0")
    monkeypatch.setenv("LAW_REFS_MAX", "3")
    monkeypatch.setenv("LAW_REFS_QUOTE_CHARS", "99999")
    d = load_doc_settings()
    assert d.law_refs_enabled is False and d.law_refs_max == 3 and d.law_refs_quote_chars == 1200 and DocSettings().law_refs_per_clause == 2


# ---------------------------------------------------------------------------------------------- the real library
@pytest.mark.skipif(not os.environ.get("LEGALMATE_LIVE_TESTS"), reason="set LEGALMATE_LIVE_TESTS=1 to check the table against the real law library (Supabase)")
def test_every_table_entry_resolves_in_the_real_library():
    import psycopg
    from chat.settings import load_env
    from retrieval.kb import KnowledgeBase

    load_env()
    kb = KnowledgeBase.__new__(KnowledgeBase)                      # only get_section is needed: skip loading the whole keyword index
    import threading
    kb._url, kb._ef, kb._conn_lock = os.environ["DATABASE_URL"], 100, threading.Lock()
    kb.conn = psycopg.connect(kb._url, autocommit=True)
    try:
        assert L.check(kb) == []
    finally:
        kb.conn.close()
