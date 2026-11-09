"""Legal Vault part A: saved answers and analyses. Local Postgres, fake model: zero DeepSeek calls.

    python -m pytest tests/test_vault.py -q
"""
from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from app.config import DocSettings
from app.main import create_app
from tests.conftest import FakeEngine, ask, make_settings, new_conv, signup
from tests.test_documents import CONTRACT, pdf, upload, wait_for

A = "/api/v1"


def answer_id(client, h, question="Can my landlord raise the rent?", conv=None):
    conv = conv or new_conv(client, h, question)
    r, ev = ask(client, h, conv["id"], question)
    assert r.status_code == 200 and ev[-1][0] == "answer" and ev[-1][1]["kind"] == "answer", ev
    return ev[-1][1]["id"], conv


def save(client, h, mid):
    return client.post(f"{A}/chat/messages/{mid}/save", headers=h)


def finished_analysis(client, h, save_to_vault=False):
    doc = upload(client, h, pdf(CONTRACT)).json()
    r = client.post(f"{A}/analyses", json={"documentIds": [doc["id"]], "depth": "quick", "saveToVault": save_to_vault}, headers=h)
    assert r.status_code == 202, r.text
    done = wait_for(client, h, r.json()["id"])
    assert done["status"] == "completed", done
    return done


# ---------------------------------------------------------------------------------------------- saving
def test_a_chat_answer_is_saved_once_and_opens_as_it_was(client):
    _, h = signup(client)
    mid, conv = answer_id(client, h, "Can my landlord raise the rent without telling me?")
    r = save(client, h, mid)
    assert r.status_code == 200 and r.json()["alreadySaved"] is False
    item_id = r.json()["id"]
    assert save(client, h, mid).json() == {"id": item_id, "alreadySaved": True}                      # saving again is not a second item

    items = client.get(f"{A}/vault/items", headers=h).json()
    assert items["total"] == 1 and items["counts"]["answer"] == 1 and items["counts"]["all"] == 1
    it = items["items"][0]
    assert it["id"] == item_id and it["kind"] == "answer" and it["title"].startswith("Can my landlord raise the rent")
    assert it["tag"] == "Property Law" and it["conversationId"] == conv["id"] and it["favourite"] is False and "content" not in it

    full = client.get(f"{A}/vault/items/{item_id}", headers=h).json()
    assert full["content"]["question"].startswith("Can my landlord") and full["content"]["answer"]["sources"][0]["title"].startswith("Punjab Rented")
    assert full["content"]["answer"]["law"] and "feedback" not in full["content"]["answer"]

    msgs = client.get(f"{A}/chat/conversations/{conv['id']}", headers=h).json()["messages"]
    assert [m.get("savedToVault") for m in msgs if m["role"] == "assistant"] == [True]              # the Save button knows after a reload
    same = client.post(f"{A}/vault/items", json={"kind": "answer", "messageId": mid}, headers=h)    # the generic endpoint is the same thing
    assert same.status_code == 201 and same.json()["id"] == item_id


def test_a_saved_answer_outlives_its_conversation(client):
    _, h = signup(client)
    mid, conv = answer_id(client, h)
    item_id = save(client, h, mid).json()["id"]
    assert client.delete(f"{A}/chat/conversations/{conv['id']}", headers=h).status_code == 204
    got = client.get(f"{A}/vault/items/{item_id}", headers=h)
    assert got.status_code == 200 and got.json()["content"]["answer"]["intro"]


def test_only_answers_can_be_saved_and_bad_requests_are_clear(client):
    _, h = signup(client)
    conv = new_conv(client, h, "hello")
    _, ev = ask(client, h, conv["id"], "hello there")                                                # a greeting: an info message, not an answer
    assert ev[-1][1]["kind"] == "info"
    r = save(client, h, ev[-1][1]["id"])
    assert r.status_code == 422 and "answer" in r.json()["error"]["message"].lower()
    assert client.post(f"{A}/vault/items", json={"kind": "answer"}, headers=h).status_code == 400
    assert client.post(f"{A}/vault/items", json={"kind": "analysis", "analysisId": "nope"}, headers=h).status_code == 400
    assert client.post(f"{A}/vault/items", json={"kind": "brief"}, headers=h).status_code == 422
    assert client.post(f"{A}/vault/items", json={"kind": "answer", "messageId": "9b2f2a0e-0000-4000-8000-000000000000"}, headers=h).status_code == 404


def test_an_analysis_is_saved_by_hand_and_a_running_one_cannot_be(client):
    j, h = signup(client)
    done = finished_analysis(client, h)
    r = client.post(f"{A}/analyses/{done['id']}/save", headers=h)
    assert r.status_code == 200 and r.json()["alreadySaved"] is False
    assert client.post(f"{A}/analyses/{done['id']}/save", headers=h).json()["alreadySaved"] is True
    it = client.get(f"{A}/vault/items?category=analysis", headers=h).json()["items"][0]
    assert it["kind"] == "analysis" and it["title"] == "contract.pdf" and it["risk"] in ("Low", "Medium", "High") and it["summary"]
    snap = client.get(f"{A}/vault/items/{it['id']}", headers=h).json()["content"]
    assert snap["id"] == done["id"] and snap["clauses"] and snap["overallRisk"]["level"] == it["risk"]

    running = client.app.state.ctx.db.one("insert into app.analyses (user_id, status) values (%s, 'processing') returning id", [j["user"]["id"]])["id"]
    r = client.post(f"{A}/analyses/{running}/save", headers=h)
    assert r.status_code == 422 and "not finished" in r.json()["error"]["message"]


def test_the_save_to_vault_tick_saves_the_analysis_when_it_is_ready(client):
    _, h = signup(client)
    done = finished_analysis(client, h, save_to_vault=True)
    items = client.get(f"{A}/vault/items", headers=h).json()
    assert items["total"] == 1 and items["items"][0]["sourceId"] == done["id"]
    ticked_off = finished_analysis(client, h, save_to_vault=False)
    assert client.get(f"{A}/vault/items", headers=h).json()["total"] == 1 and ticked_off["id"] != done["id"]


def test_a_saved_analysis_stays_after_the_analysis_is_deleted(client):
    _, h = signup(client)
    done = finished_analysis(client, h)
    item_id = client.post(f"{A}/analyses/{done['id']}/save", headers=h).json()["id"]
    assert client.delete(f"{A}/analyses/{done['id']}", headers=h).status_code == 204
    assert client.get(f"{A}/vault/items/{item_id}", headers=h).json()["content"]["clauses"]


# ---------------------------------------------------------------------------------------------- privacy
def test_one_users_vault_is_invisible_to_another(client):
    _, a = signup(client)
    _, b = signup(client)
    mid, _ = answer_id(client, a)
    item_id = save(client, a, mid).json()["id"]
    assert save(client, b, mid).status_code == 404                                                   # not their message
    assert client.get(f"{A}/vault/items", headers=b).json()["total"] == 0
    for method, path, body in (("get", f"/vault/items/{item_id}", None), ("patch", f"/vault/items/{item_id}", {"title": "mine now"}),
                               ("put", f"/vault/items/{item_id}/favourite", {"favourite": True}), ("delete", f"/vault/items/{item_id}", None),
                               ("post", f"/vault/items/{item_id}/restore", None), ("get", f"/vault/items/{item_id}/notes", None),
                               ("post", f"/vault/items/{item_id}/notes", {"text": "hi"}), ("get", f"/vault/items/{item_id}/activity", None)):
        r = client.request(method, A + path, headers=b, **({"json": body} if body else {}))
        assert r.status_code == 404, (method, path, r.status_code)
    assert client.get(f"{A}/vault/items/{item_id}", headers=a).json()["title"]                      # and nothing happened to it
    assert client.get(f"{A}/vault/items").status_code == 401


# ---------------------------------------------------------------------------------------------- listing
def test_list_filters_search_sort_and_pages(client):
    _, h = signup(client)
    ids = {}
    for q in ("Zakat on savings", "Alimony after divorce", "Bail in a theft case"):
        mid, _ = answer_id(client, h, q)
        ids[q] = save(client, h, mid).json()["id"]
    done = finished_analysis(client, h)
    client.post(f"{A}/analyses/{done['id']}/save", headers=h)
    client.put(f"{A}/vault/items/{ids['Alimony after divorce']}/favourite", json={"favourite": True}, headers=h)

    def items(**p):
        return client.get(f"{A}/vault/items", params=p, headers=h).json()

    assert items()["total"] == 4 and items()["counts"] == {"all": 4, "answer": 3, "analysis": 1, "brief": 0, "calculation": 0, "favourites": 1, "trash": 0}
    assert items(category="analysis")["total"] == 1 and items(category="answer")["total"] == 3
    assert [i["title"] for i in items(category="favourites")["items"]] == ["Alimony after divorce"]
    assert [i["title"] for i in items(q="bail")["items"]] == ["Bail in a theft case"]                 # title search, any case
    assert items(q="by agreement")["total"] == 3                                                     # the summary text is searched too
    assert items(q="50%_")["total"] == 0                                                              # LIKE characters are literal
    titles = [i["title"] for i in items(sort="name_asc")["items"]]
    assert titles == sorted(titles, key=str.lower) and [i["title"] for i in items(sort="name_desc")["items"]] == titles[::-1]
    p1, p2 = items(pageSize=3, page=1), items(pageSize=3, page=2)
    assert len(p1["items"]) == 3 and len(p2["items"]) == 1 and p1["total"] == 4 and {i["id"] for i in p1["items"]}.isdisjoint({i["id"] for i in p2["items"]})
    assert client.get(f"{A}/vault/items?sort=sideways", headers=h).status_code == 400
    assert client.get(f"{A}/vault/stats", headers=h).json()["counts"]["all"] == 4


# ---------------------------------------------------------------------------------------------- changing
def test_rename_favourite_notes_and_activity(client):
    _, h = signup(client)
    mid, _ = answer_id(client, h)
    item_id = save(client, h, mid).json()["id"]
    r = client.patch(f"{A}/vault/items/{item_id}", json={"title": "  My rent question  "}, headers=h)
    assert r.status_code == 200 and r.json()["title"] == "My rent question"
    assert client.patch(f"{A}/vault/items/{item_id}", json={"title": "   "}, headers=h).status_code == 400
    assert client.patch(f"{A}/vault/items/{item_id}", json={"title": "x" * 161}, headers=h).status_code == 400
    assert client.put(f"{A}/vault/items/{item_id}/favourite", json={"favourite": True}, headers=h).status_code == 204
    assert client.get(f"{A}/vault/items/{item_id}", headers=h).json()["favourite"] is True
    client.put(f"{A}/vault/items/{item_id}/favourite", json={"favourite": False}, headers=h)

    n1 = client.post(f"{A}/vault/items/{item_id}/notes", json={"text": "Ask the landlord for it in writing."}, headers=h)
    n2 = client.post(f"{A}/vault/items/{item_id}/notes", json={"text": "Keep the receipts."}, headers=h)
    assert n1.status_code == 201 and n2.status_code == 201
    notes = client.get(f"{A}/vault/items/{item_id}/notes", headers=h).json()["items"]
    assert [n["text"] for n in notes] == ["Keep the receipts.", "Ask the landlord for it in writing."]    # newest first
    assert client.get(f"{A}/vault/items", headers=h).json()["items"][0]["noteCount"] == 2
    assert client.delete(f"{A}/vault/items/{item_id}/notes/{n1.json()['id']}", headers=h).status_code == 204
    assert client.delete(f"{A}/vault/items/{item_id}/notes/{n1.json()['id']}", headers=h).status_code == 404
    assert client.post(f"{A}/vault/items/{item_id}/notes", json={"text": "y" * 2001}, headers=h).status_code == 400
    assert client.post(f"{A}/vault/items/{item_id}/notes", json={"text": ""}, headers=h).status_code == 400

    acts = [a["action"] for a in client.get(f"{A}/vault/items/{item_id}/activity", headers=h).json()["items"]]
    assert acts[-1] == "saved" and acts.count("noted") == 2 and "renamed" in acts and "favourited" in acts and "unfavourited" in acts
    assert acts[0] == "noted"                                                                          # newest first


def test_trash_restore_delete_forever_and_empty_trash(client):
    _, h = signup(client)
    ids = [save(client, h, answer_id(client, h, f"Question number {i}")[0]).json()["id"] for i in range(3)]
    assert client.delete(f"{A}/vault/items/{ids[0]}", headers=h).status_code == 204
    assert client.delete(f"{A}/vault/items/{ids[0]}", headers=h).status_code == 204                   # already in the Trash: nothing more to do
    lst = client.get(f"{A}/vault/items", headers=h).json()
    assert lst["total"] == 2 and lst["counts"]["trash"] == 1 and ids[0] not in [i["id"] for i in lst["items"]]
    tr = client.get(f"{A}/vault/items?category=trash", headers=h).json()
    assert [i["id"] for i in tr["items"]] == [ids[0]] and tr["items"][0]["trashedAt"]
    assert client.get(f"{A}/vault/items/{ids[0]}", headers=h).status_code == 200                      # still readable while in the Trash
    assert client.patch(f"{A}/vault/items/{ids[0]}", json={"title": "x"}, headers=h).status_code == 404   # but not editable
    assert client.post(f"{A}/vault/items/{ids[0]}/notes", json={"text": "x"}, headers=h).status_code == 422

    assert client.delete(f"{A}/vault/items/{ids[1]}?permanent=true", headers=h).status_code == 422   # not in the Trash yet
    assert client.post(f"{A}/vault/items/{ids[0]}/restore", headers=h).status_code == 204
    assert client.get(f"{A}/vault/items", headers=h).json()["total"] == 3
    client.delete(f"{A}/vault/items/{ids[0]}", headers=h)
    client.delete(f"{A}/vault/items/{ids[1]}", headers=h)
    assert client.delete(f"{A}/vault/items/{ids[0]}?permanent=true", headers=h).status_code == 204
    assert client.get(f"{A}/vault/items/{ids[0]}", headers=h).status_code == 404
    assert client.delete(f"{A}/vault/trash", headers=h).json() == {"deleted": 1}
    assert client.get(f"{A}/vault/items", headers=h).json()["total"] == 1


def test_saving_again_takes_an_answer_out_of_the_trash(client):
    _, h = signup(client)
    mid, _ = answer_id(client, h)
    item_id = save(client, h, mid).json()["id"]
    client.delete(f"{A}/vault/items/{item_id}", headers=h)
    r = save(client, h, mid)
    assert r.json() == {"id": item_id, "alreadySaved": False}
    assert client.get(f"{A}/vault/items", headers=h).json()["total"] == 1


def test_the_trash_empties_itself_after_the_set_number_of_days(client):
    from app.docs_service import purge_expired
    _, h = signup(client)
    old, recent = (save(client, h, answer_id(client, h, f"Trash question {n}")[0]).json()["id"] for n in ("a", "b"))
    for i in (old, recent):
        client.delete(f"{A}/vault/items/{i}", headers=h)
    db = client.app.state.ctx.db
    db.run("update app.vault_items set trashed_at = now() - interval '31 days' where id = %s", [old])
    db.run("update app.vault_items set trashed_at = now() - interval '29 days' where id = %s", [recent])
    assert purge_expired(db, client.app.state.ctx.settings.docs)["vault_trash"] >= 1
    assert client.get(f"{A}/vault/items/{old}", headers=h).status_code == 404 and client.get(f"{A}/vault/items/{recent}", headers=h).status_code == 200


# ---------------------------------------------------------------------------------------------- limits from settings
def test_limits_come_from_settings(pg_url):
    cfg = replace(DocSettings(), vault_max_items=2, vault_max_notes=1, vault_note_chars=50, vault_page_size=1)
    with TestClient(create_app(make_settings(pg_url, docs=cfg), engine=FakeEngine())) as c:
        _, h = signup(c)
        m1, m2, m3 = (answer_id(c, h, f"Limit question {i}")[0] for i in range(3))
        i1 = save(c, h, m1).json()["id"]
        save(c, h, m2)
        r = save(c, h, m3)
        assert r.status_code == 422 and r.json()["error"]["code"] == "QUOTA_EXCEEDED" and "2 items" in r.json()["error"]["message"]
        assert save(c, h, m1).json()["alreadySaved"] is True                                          # saving what is already there still works
        assert c.post(f"{A}/vault/items/{i1}/notes", json={"text": "one"}, headers=h).status_code == 201
        assert c.post(f"{A}/vault/items/{i1}/notes", json={"text": "two"}, headers=h).status_code == 422
        assert c.post(f"{A}/vault/items/{i1}/notes", json={"text": "z" * 51}, headers=h).status_code == 400
        page = c.get(f"{A}/vault/items", headers=h).json()
        assert page["pageSize"] == 1 and len(page["items"]) == 1 and page["total"] == 2
