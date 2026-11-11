"""The calculators ranked for each kind of user (young adult, student, business owner, citizen)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import calculators as calc
from app import personas
from app.main import create_app
from tests.conftest import FakeEngine, MemoryStorage, make_settings, signup

A = "/api/v1"


# ------------------------------------------------------------------------------------------------ ranking
def test_calculators_are_ranked_for_the_kind_of_user_and_none_is_lost():
    for ut in ("Young adult", "Student", "Business owner (SME)", "Citizen", None):
        ranked = personas.calculators_for(ut)
        assert {c["key"] for c in ranked} == set(calc.CALCULATORS) and len(ranked) == len(calc.CALCULATORS)
        assert ranked[0]["recommended"] and ranked[0]["why"]
        assert [c["recommended"] for c in ranked] == sorted([c["recommended"] for c in ranked], reverse=True)     # recommended ones first
    assert personas.calculators_for("Young adult")[0]["key"] == "compensation"
    assert [c["key"] for c in personas.calculators_for("Business owner (SME)")][:2] == ["limitation", "compensation"]
    assert personas.calculators_for("Student")[0]["key"] == "limitation"


# ------------------------------------------------------------------------------------------------ the API
@pytest.fixture(scope="module")
def client(pg_url):
    with TestClient(create_app(make_settings(pg_url), engine=FakeEngine(), storage=MemoryStorage())) as c:
        yield c


def test_the_calculator_list_is_ranked_for_the_profile(client):
    _, h = signup(client)
    assert client.get(f"{A}/calculators", headers=h).json()["ranked"][0]["key"] == "limitation"                    # a citizen
    body = {"province": "Punjab", "city": "Lahore", "userType": "Young adult", "employmentStatus": "Employed", "roles": ["Employee"], "ageBand": "25-34",
            "maritalStatus": "Single", "language": "en", "interests": []}
    assert client.put(f"{A}/users/me/profile", json=body, headers=h).status_code == 200
    ranked = client.get(f"{A}/calculators", headers=h).json()["ranked"]
    assert ranked[0]["key"] == "compensation" and ranked[0]["recommended"] and len(ranked) == 5
    d = client.get(f"{A}/dashboard", headers=h).json()["forYou"]
    ya = next(p for p in d["personas"] if p["key"] == "young_adult")
    assert d["selected"] == "young_adult" and [c["key"] for c in ya["calculators"]][0] == "compensation"
