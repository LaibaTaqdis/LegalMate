"""Legal calculators, the court calendar and the real dashboard. Local Postgres, fake model, in-memory storage: no network."""
from __future__ import annotations

import itertools
import json
from datetime import date
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

from app import calculators as calc
from app import calendar_service as cal
from app.errors import ApiError
from app.main import create_app
from tests.conftest import FakeEngine, MemoryStorage, ask, make_settings, new_conv, signup
from tests.test_documents import pdf

A = "/api/v1"
TODAY = date(2026, 11, 9)


# ---------------------------------------------------------------------------------------------- the court calendar
def test_calendar_data_is_well_formed():
    data = json.loads(cal.DATA.read_text(encoding="utf-8"))
    ids = [e["id"] for e in data["entries"]]
    assert len(ids) == len(set(ids))
    for e in data["entries"]:
        assert date.fromisoformat(e["start"]) <= date.fromisoformat(e["end"]), e["id"]
        assert e["status"] in ("notified", "reported", "expected") and e["kind"] in ("holiday", "vacation", "optional"), e["id"]
        assert set(e["courts"]) <= set(data["courts"]), e["id"]
        assert e["source"], e["id"]
        if e["status"] != "expected":
            assert e["url"].startswith("https://"), f"{e['id']} has no source link"           # a reported date must say where it was reported
    assert data["verifiedOn"] and data["notYetAnnounced"]


def test_upcoming_is_sorted_skips_the_past_and_marks_what_is_on_now():
    up = cal.upcoming(TODAY, limit=5)
    assert [e["start"] for e in up] == sorted(e["start"] for e in up)
    assert all(e["end"] >= TODAY.isoformat() for e in up)
    assert up[0]["id"] == "iqbal-2026" and up[0]["ongoing"] is True and up[0]["daysUntil"] == 0
    assert any(e["id"] == "quaid-2026" for e in up)
    ihc = cal.upcoming(date(2026, 7, 10), limit=10, court="ihc")
    assert {e["id"] for e in ihc} >= {"ihc-summer-2026", "independence-2026"} and not any("lhc" == c for e in ihc for c in e["courts"] if "all" not in e["courts"])
    assert cal.upcoming(date(2030, 1, 1)) == []


def test_a_closed_day_is_a_sunday_or_a_public_holiday_but_not_a_vacation():
    assert cal.closed_on(date(2026, 11, 8)) == "Sunday"                                       # 8 Nov 2026 is a Sunday
    assert cal.closed_on(date(2026, 11, 9)) == "Iqbal Day"
    assert cal.closed_on(date(2026, 7, 7), "lhc") is None                                    # summer vacation: offices stay open, so no section 4 shift
    assert cal.vacation_on(date(2026, 7, 7), "lhc")["id"] == "lhc-summer-2026" and cal.vacation_on(date(2026, 7, 7), "ihc")["id"] == "ihc-summer-2026"
    assert cal.closed_on(date(2026, 5, 27), "lhc") == "Eid ul-Azha holidays (revised)" and cal.closed_on(date(2026, 5, 26), "lhc")
    nxt, why = cal.next_open_day(date(2026, 6, 25))                                         # Ashura Thu-Fri, then Saturday is open
    assert nxt == date(2026, 6, 27) and len(why) == 2
    nxt, why = cal.next_open_day(date(2026, 12, 25))                                        # Quaid-e-Azam Day (Friday) is closed; Saturday 26 Dec is open
    assert nxt == date(2026, 12, 26) and why == ["25 Dec 2026: Quaid-e-Azam Day"]
    assert cal.closed_on(date(2026, 12, 26)) is None                                         # Christmas for Christian employees is optional: not a court closure
    nxt, why = cal.next_open_day(date(2026, 12, 27))                                        # a Sunday, then Monday is open
    assert nxt == date(2026, 12, 28) and why == ["27 Dec 2026: Sunday"]


# ---------------------------------------------------------------------------------------------- inheritance (Hanafi)
def shares(**kw):
    base = dict(amount=1_200_000, spouse="None", wives=1, sons=0, daughters=0, father="No", mother="No")
    base.update(kw)
    r = calc.calculate("inheritance", base)
    return {k: Fraction(v) for k, v in r["details"]["shares"].items()}, r


def test_inheritance_textbook_cases():
    s, r = shares(spouse="Wife", sons=2, daughters=1)
    assert s == {"wives": Fraction(1, 8), "sons": Fraction(7, 10), "daughters": Fraction(7, 40)}          # a son takes twice a daughter: 7/20 and 7/40
    s, _ = shares(spouse="Husband", sons=1)
    assert s == {"husband": Fraction(1, 4), "sons": Fraction(3, 4)}
    s, r = shares(spouse="Husband", father="Yes", mother="Yes")
    assert s == {"husband": Fraction(1, 2), "mother": Fraction(1, 6), "father": Fraction(1, 3)} and "Umariyyatayn" in " ".join(r["notes"])
    s, _ = shares(spouse="Wife", father="Yes", mother="Yes")
    assert s == {"wives": Fraction(1, 4), "mother": Fraction(1, 4), "father": Fraction(1, 2)}
    s, _ = shares(father="Yes", mother="Yes")
    assert s == {"mother": Fraction(1, 3), "father": Fraction(2, 3)}
    s, _ = shares(daughters=1, father="Yes", mother="Yes")
    assert s == {"daughters": Fraction(1, 2), "mother": Fraction(1, 6), "father": Fraction(1, 3)}      # father: 1/6 fixed + the rest
    s, _ = shares(sons=1, father="Yes", mother="Yes")
    assert s == {"mother": Fraction(1, 6), "father": Fraction(1, 6), "sons": Fraction(2, 3)}


def test_inheritance_awl_and_radd():
    s, r = shares(spouse="Husband", daughters=2, father="Yes", mother="Yes")                       # 1/4 + 2/3 + 1/6 + 1/6 = 5/4: every share shrinks ('awl)
    assert s == {"husband": Fraction(3, 15), "daughters": Fraction(8, 15), "mother": Fraction(2, 15), "father": Fraction(2, 15)} and "'awl" in " ".join(r["notes"])
    s, r = shares(daughters=1, mother="Yes")                                                         # 1/2 + 1/6 = 2/3: the rest goes back to them (radd)
    assert s == {"daughters": Fraction(3, 4), "mother": Fraction(1, 4)} and "radd" in " ".join(r["notes"])
    s, _ = shares(mother="Yes")
    assert s == {"mother": Fraction(1)}
    s, r = shares(spouse="Husband", mother="Yes")                                                    # the spouse never receives radd
    assert s == {"husband": Fraction(1, 2), "mother": Fraction(1, 2)}


def test_inheritance_several_wives_share_one_portion_and_amounts_add_up():
    r = calc.calculate("inheritance", dict(amount=8_000_000, spouse="Wife", wives=2, sons=1, daughters=0))
    wives = next(x for x in r["rows"] if x["label"].startswith("Widows"))
    assert "1/8 of the estate" in wives["label"] and wives["value"] == "PKR 1,000,000, PKR 500,000 each"
    for combo in itertools.product(("None", "Husband", "Wife"), (0, 1, 3), (0, 1, 2), ("No", "Yes"), ("No", "Yes")):          # no combination may hand out more than the estate
        spouse, sons, daughters, father, mother = combo
        if spouse == "None" and not (sons or daughters or father == "Yes" or mother == "Yes"):
            continue
        if not (sons or daughters or father == "Yes" or mother == "Yes"):
            continue
        s, _ = shares(spouse=spouse, sons=sons, daughters=daughters, father=father, mother=mother)
        assert sum(s.values()) <= 1, combo
        if sons or father == "Yes" or (daughters or mother == "Yes") and spouse == "None":
            assert sum(s.values()) == 1, combo                                                      # a residuary heir or radd uses up the whole estate


def test_inheritance_refuses_what_it_cannot_do_and_bad_input():
    with pytest.raises(ApiError) as e:
        calc.calculate("inheritance", dict(amount=1_000_000, spouse="Husband"))
    assert "other relatives" in e.value.message
    with pytest.raises(ApiError):
        calc.calculate("inheritance", dict(amount=1_000_000))
    for bad in (dict(amount=0, sons=1), dict(amount="abc", sons=1), dict(amount=1_000_000, sons=-1), dict(amount=1_000_000, sons=1.5), dict(amount=1_000_000, spouse="Cousin", sons=1)):
        with pytest.raises(ApiError) as e:
            calc.calculate("inheritance", bad)
        assert e.value.status == 400


# ---------------------------------------------------------------------------------------------- limitation
def lim(kind, d, court="lhc", today=TODAY, **kw):
    return calc.calculate("limitation", dict(kind=kind, date=d, court=court, **kw), today=today)


def test_limitation_periods_follow_the_first_schedule():
    assert lim("contract_unregistered", "2026-03-10")["text"] == "10 Mar 2029"                  # Article 115: three years (six was Azad Kashmir's change)
    assert lim("contract_registered", "2026-03-10")["text"] == "10 Mar 2032"                    # Article 116: six years
    assert lim("possession_immovable", "2014-03-10")["details"]["periodEnds"] == "2026-03-10"  # twelve years
    assert lim("contract_unregistered", "2024-02-29")["details"]["periodEnds"] == "2027-02-28"  # from a leap day: the earlier date, to be safe
    assert lim("possession_immovable", "2020-02-29")["details"]["periodEnds"] == "2032-02-29"  # 2032 is a leap year too (a Sunday, so the last day moves to Monday)
    assert lim("possession_immovable", "2020-02-29")["text"] == "01 Mar 2032"
    assert lim("appeal_district", "2026-10-01")["details"]["periodEnds"] == "2026-10-31"        # Article 152: thirty days
    assert lim("appeal_high_court", "2026-10-01")["details"]["periodEnds"] == "2026-12-30"      # Article 156: ninety days
    assert lim("appeal_acquittal", "2026-08-31")["details"]["periodEnds"] == "2027-02-28"       # six months, clamped to the month's end
    assert lim("residuary", "2026-01-15")["text"] == "15 Jan 2032"
    r = lim("contract_unregistered", "2026-03-10")
    assert r["details"]["daysLeft"] == (date(2029, 3, 10) - TODAY).days and r["confidence"] == "law"


def test_limitation_leaves_out_the_time_to_get_a_certified_copy_for_appeals_only():
    r = lim("appeal_district", "2026-10-01", copyDays=5)
    assert r["details"]["periodEnds"] == "2026-10-31" and r["details"]["lastDay"] == "2026-11-05"
    assert lim("residuary", "2026-10-01", copyDays=5)["details"]["lastDay"] == "2032-10-01"      # a suit gets no such exclusion


def test_the_last_day_moves_when_the_court_is_closed_and_says_so():
    r = lim("appeal_district", "2026-10-10")                                                       # 9 Nov 2026 would be day 30: Iqbal Day (Monday), closed
    assert r["details"]["periodEnds"] == "2026-11-09" and r["details"]["lastDay"] == "2026-11-10" and r["details"]["movedBy"] == ["09 Nov 2026: Iqbal Day"]
    assert "section 4" in r["notes"][0]
    r = lim("appeal_district", "2026-10-09")                                                       # day 30 = 8 Nov 2026, a Sunday, then Iqbal Day Monday
    assert r["details"]["lastDay"] == "2026-11-10" and len(r["details"]["movedBy"]) == 2


def test_a_deadline_inside_a_vacation_is_not_moved_but_the_user_is_told():
    r = lim("appeal_district", "2026-06-10", court="lhc")                                         # 10 Jul 2026 (Friday) is inside the LHC summer vacation
    assert r["details"]["lastDay"] == "2026-07-10" and not r["details"]["movedBy"]
    assert any("vacation" in n and "does not move the deadline" in n for n in r["notes"])
    assert not any("vacation" in n for n in lim("appeal_district", "2026-06-10", court="sc")["notes"])


def test_limitation_expired_and_bad_input():
    r = lim("appeal_district", "2026-01-01")
    assert r["details"]["daysLeft"] < 0 and r["rows"][-1]["label"] == "Status" and "Expired" in r["rows"][-1]["value"]
    for bad in (dict(kind="nonsense", date="2026-01-01"), dict(kind="residuary", date="not-a-date"), dict(kind="residuary", date="1800-01-01"),
                dict(kind="residuary", date="2026-01-01", court="mars"), dict(kind="appeal_district", date="2026-01-01", copyDays=-1)):
        with pytest.raises(ApiError) as e:
            calc.calculate("limitation", bad, today=TODAY)
        assert e.value.status == 400


# ---------------------------------------------------------------------------------------------- compensation (Standing Order 12)
def comp(**kw):
    base = dict(salary=85_000, years=4, months=0, reason="Termination without misconduct", workman="Permanent", providentFund="No")
    base.update(kw)
    return calc.calculate("compensation", base)


def test_gratuity_counts_every_year_and_a_part_year_over_six_months():
    assert comp()["total"] == 85_000 * 4 + 85_000                                                   # 4 years gratuity + one month's notice pay
    assert comp(months=6)["total"] == 85_000 * 4 + 85_000                                           # exactly six months does not count
    assert comp(months=7)["total"] == 85_000 * 5 + 85_000                                           # more than six months counts as a year
    assert comp(years=0, months=3)["total"] == 85_000                                               # under a year: notice pay only


def test_notice_pay_only_for_permanent_workmen_terminated_without_misconduct():
    assert comp(reason="Resignation")["total"] == 85_000 * 4
    assert comp(reason="Retirement")["total"] == 85_000 * 4
    assert comp(reason="Retrenchment")["total"] == 85_000 * 5
    assert comp(workman="Temporary / probationer")["total"] == 85_000 * 4                           # no notice pay for temporary workmen
    r = comp(providentFund="Yes")
    assert r["total"] == 85_000 and any("provident fund" in n.lower() for n in r["notes"])
    assert "Standing Order 12" in r["source"]["reference"]
    assert any("90 days" in n and "three months" in n for n in comp()["notes"])                      # grievance time limits are from the two Industrial Relations Acts


# ---------------------------------------------------------------------------------------------- stamp duty and property: labelled "reported"
def test_stamp_and_property_say_they_are_reported_not_official():
    s = calc.calculate("stamp", dict(amount=5_000_000))
    assert s["total"] == 50_000 and s["confidence"] == "reported" and "ordinance" in s["source"]["title"].lower()
    assert any("sub-registrar" in n for n in s["notes"])
    p = calc.calculate("property", dict(amount=10_000_000))
    assert p["details"] == {"seller": 275_000.0, "buyer": 225_000.0} and p["confidence"] == "reported"                # 2.75% seller, 1% stamp + 1.25% buyer
    nb = calc.calculate("property", dict(amount=60_000_000, buyerStatus="Non-filer", sellerStatus="Non-filer"))
    assert nb["details"]["buyer"] == 60_000_000 * 0.01 + 60_000_000 * 0.145 and nb["details"]["seller"] == 60_000_000 * 0.115
    assert any("one commentary source" in n for n in nb["notes"])
    for bad in (dict(amount=0), dict(amount=1_000_000, buyerStatus="Maybe"), dict(amount=1_000_000, instrument="Gift deed")):
        with pytest.raises(ApiError):
            calc.calculate("property" if "buyerStatus" in bad or "instrument" not in bad else "stamp", bad)


def test_court_fee_is_openly_not_offered_and_unknown_calculators_are_404():
    with pytest.raises(ApiError) as e:
        calc.calculate("court", dict(amount=1_000_000))
    assert e.value.status == 422 and "could not be verified" in e.value.message
    with pytest.raises(ApiError) as e:
        calc.calculate("nonsense", {})
    assert e.value.status == 404
    m = calc.meta()
    assert [u["key"] for u in m["unavailable"]] == ["court"] and {i["key"] for i in m["items"]} == {"limitation", "inheritance", "compensation", "stamp", "property"}
    assert {i["confidence"] for i in m["items"]} == {"law", "reported"}


# ---------------------------------------------------------------------------------------------- the API
@pytest.fixture(scope="module")
def storage():
    return MemoryStorage()


@pytest.fixture(scope="module")
def client(pg_url, storage):
    with TestClient(create_app(make_settings(pg_url), engine=FakeEngine(), storage=storage)) as c:
        yield c


def test_calculator_endpoints(client):
    assert client.get(f"{A}/calculators").status_code == 401
    _, h = signup(client)
    m = client.get(f"{A}/calculators", headers=h).json()
    assert m["verifiedOn"] and m["unavailable"][0]["key"] == "court" and len(m["options"]["limitation"]) == 10
    r = client.post(f"{A}/calculators/inheritance/calculate", json={"inputs": dict(amount=12_000_000, spouse="Wife", sons=2, daughters=1)}, headers=h)
    assert r.status_code == 200 and r.json()["rows"][1]["value"] == "PKR 1,500,000" and r.json()["source"]["url"] and r.json()["calculatedAt"]
    assert client.post(f"{A}/calculators/inheritance/calculate", json={"inputs": dict(amount=-5)}, headers=h).status_code == 400
    assert client.post(f"{A}/calculators/court/calculate", json={"inputs": {}}, headers=h).status_code == 422
    assert client.post(f"{A}/calculators/nope/calculate", json={"inputs": {}}, headers=h).status_code == 404


def test_a_calculation_can_be_saved_to_the_vault_and_downloaded_as_a_pdf(client):
    _, h = signup(client)
    _, other = signup(client)
    forged = {"type": "compensation", "inputs": dict(salary=100_000, years=3), "result": {"total": 999_999_999}}          # a result sent by the browser is ignored
    r = client.post(f"{A}/calculators/saved", json=forged, headers=h)
    assert r.status_code == 201
    item = client.get(f"{A}/vault/items/{r.json()['id']}", headers=h).json()
    assert item["kind"] == "calculation" and item["content"]["result"]["total"] == 400_000 and item["title"].startswith("Compensation: PKR 400,000")
    assert client.get(f"{A}/vault/items?category=calculation", headers=h).json()["counts"]["calculation"] == 1
    pdf_r = client.get(f"{A}/calculators/saved/{r.json()['id']}/summary", headers=h)
    assert pdf_r.status_code == 200 and pdf_r.content.startswith(b"%PDF") and "attachment" in pdf_r.headers["content-disposition"]
    assert client.get(f"{A}/calculators/saved/{r.json()['id']}/summary", headers=other).status_code == 404
    mid, _ = (lambda c: (ask(client, h, c["id"], "Can my landlord raise the rent?")[1][-1][1]["id"], c))(new_conv(client, h))
    assert client.get(f"{A}/calculators/saved/{mid}/summary", headers=h).status_code == 404                   # not a calculation
    assert client.post(f"{A}/calculators/saved", json={"type": "court", "inputs": {}}, headers=h).status_code == 422
    assert client.post(f"{A}/calculators/saved", json={"type": "limitation", "inputs": {"kind": "x"}}, headers=h).status_code == 400


def test_court_holidays_endpoint(client):
    _, h = signup(client)
    r = client.get(f"{A}/calendar/court-holidays?limit=3", headers=h).json()
    assert len(r["items"]) <= 3 and r["verifiedOn"] and r["note"] and "winter" in r["notYetAnnounced"].lower()
    allr = client.get(f"{A}/calendar/court-holidays?all=true", headers=h).json()["items"]
    assert len(allr) == len(json.loads(cal.DATA.read_text(encoding="utf-8"))["entries"]) and allr[0]["start"] <= allr[-1]["start"]
    sc = client.get(f"{A}/calendar/court-holidays?all=true&court=sc", headers=h).json()["items"]
    assert sc and all("sc" in e["courts"] or "all" in e["courts"] for e in sc)
    assert client.get(f"{A}/calendar/court-holidays?court=mars", headers=h).status_code == 400
    assert client.get(f"{A}/calendar/court-holidays").status_code == 401


# ---------------------------------------------------------------------------------------------- the dashboard
def test_dashboard_is_empty_for_a_new_user_and_shows_real_storage_and_activity_later(client):
    _, h = signup(client)
    d = client.get(f"{A}/dashboard", headers=h).json()
    assert d["activity"] == [] and d["vault"]["usedBytes"] == 0 and d["vault"]["quotaBytes"] == 50 * 1024 * 1024 and d["vault"]["filesEnabled"] is True
    assert {b["category"] for b in d["vault"]["breakdown"]} == {"documents", "images"} and d["resources"] and all(r["link"].startswith("https://") for r in d["resources"])
    assert set(d["holidays"]) >= {"items", "verifiedOn", "note", "notYetAnnounced"}

    mid, _ = (lambda c: (ask(client, h, c["id"], "Can my landlord raise the rent?")[1][-1][1]["id"], c))(new_conv(client, h, "Rent question"))
    client.post(f"{A}/chat/messages/{mid}/save", headers=h)
    data = pdf()
    up = client.post(f"{A}/vault/files", files={"file": ("lease.pdf", data, "application/pdf")}, headers=h)
    assert up.status_code == 201
    client.post(f"{A}/calculators/saved", json={"type": "stamp", "inputs": {"amount": 1_000_000}}, headers=h)
    d = client.get(f"{A}/dashboard", headers=h).json()
    types = {a["type"] for a in d["activity"]}
    assert types == {"chat", "saved", "file"} and len(d["activity"]) <= 8
    assert [a["occurredAt"] for a in d["activity"]] == sorted((a["occurredAt"] for a in d["activity"]), reverse=True)
    assert d["vault"]["usedBytes"] == len(data) and d["vault"]["fileCount"] == 1 and d["vault"]["savedCount"] == 2
    assert next(b for b in d["vault"]["breakdown"] if b["category"] == "documents")["bytes"] == len(data)
    file_row = next(a for a in d["activity"] if a["type"] == "file")
    assert file_row["title"] == "lease.pdf" and file_row["link"] == f"/vault/file/{up.json()['id']}"
    assert next(a for a in d["activity"] if a["type"] == "saved" and a["subtitle"].startswith("Calculation"))["link"].startswith("/vault/item/")


def test_dashboard_never_shows_another_users_data(client):
    _, a = signup(client)
    _, b = signup(client)
    client.post(f"{A}/vault/files", files={"file": ("private.pdf", pdf(), "application/pdf")}, headers=a)
    new_conv(client, a, "A secret matter")
    d = client.get(f"{A}/dashboard", headers=b).json()
    assert d["activity"] == [] and d["vault"]["usedBytes"] == 0 and d["vault"]["fileCount"] == 0
    assert client.get(f"{A}/dashboard").status_code == 401


def test_dashboard_without_storage_says_files_are_off(pg_url):
    with TestClient(create_app(make_settings(pg_url), engine=FakeEngine())) as c:
        _, h = signup(c)
        assert c.get(f"{A}/dashboard", headers=h).json()["vault"]["filesEnabled"] is False
