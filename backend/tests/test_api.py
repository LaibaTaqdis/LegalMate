"""API tests: accounts and sessions, profile, conversations, the streaming chat endpoint, isolation between users, limits.

    python -m pytest tests/test_api.py -q        (starts a local Postgres; makes zero DeepSeek calls)
"""
from __future__ import annotations

import time

import jwt
from fastapi.testclient import TestClient

from app.main import create_app
from app.migrations_check import tables_without_rls  # noqa: F401  (defined in app/migrations_check.py)
from tests.conftest import PASSWORD, SECRET, ask, email, make_settings, new_conv, signup

A = "/api/v1"


# ------------------------------------------------------------------------------------------------ basics
def test_health_and_ready(client):
    assert client.get("/health").json() == {"status": "ok"}
    r = client.get("/health/ready")
    assert r.status_code == 200 and r.json()["database"] is True


def test_unknown_route_and_missing_token_use_the_error_shape(client):
    r = client.get(f"{A}/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    r = client.get(f"{A}/auth/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"
    assert r.headers["cache-control"] == "no-store" and r.headers["x-content-type-options"] == "nosniff"


def test_cors_allows_the_frontend_only(client):
    ok = client.options(f"{A}/auth/login", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options(f"{A}/auth/login", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers


def test_every_app_table_has_row_level_security(client):
    assert tables_without_rls(client.app.state.ctx.db) == []


def test_migrations_are_idempotent(client):
    from app.db import migrate
    assert migrate(client.app.state.ctx.db) == []


# ------------------------------------------------------------------------------------------------ accounts
def test_register_login_me_and_cnic_is_masked(client):
    addr = email()
    j, h = signup(client, addr, phone="0300 1234567", cnic="35202-1234567-1", preferredLanguage="ur")
    u = j["user"]
    assert u["email"] == addr and u["role"] == "client" and u["preferredLanguage"] == "ur" and u["profileCompleted"] is False
    assert u["phone"] == "300 1234567" and u["cnic"] == "*****-***567-1"          # only 4 digits ever stored
    assert "password" not in str(u).lower() and "hash" not in str(u).lower()
    assert client.get(f"{A}/auth/me", headers=h).json()["email"] == addr
    r = client.post(f"{A}/auth/login", json={"identifier": addr.upper(), "password": PASSWORD, "role": "client"})
    assert r.status_code == 200 and r.json()["user"]["id"] == u["id"]
    r = client.post(f"{A}/auth/login", json={"identifier": "+92 300 1234567", "password": PASSWORD})      # sign in with the phone number
    assert r.status_code == 200 and r.json()["user"]["id"] == u["id"]


def test_register_validation_and_duplicates(client):
    addr = email()
    signup(client, addr, phone="03111234567")
    r = client.post(f"{A}/auth/register", json={"fullName": "X Y", "email": addr, "password": PASSWORD, "acceptedTerms": True})
    assert r.status_code == 409 and r.json()["error"]["details"] == {"field": "email"}
    r = client.post(f"{A}/auth/register", json={"fullName": "X Y", "email": email(), "password": PASSWORD, "acceptedTerms": True, "phone": "0311 1234567"})
    assert r.status_code == 409 and r.json()["error"]["details"] == {"field": "phone"}
    for bad, needle in [({"password": "alllowercase1!"}, "uppercase"), ({"password": "Short1!"}, "password"), ({"email": "nope"}, "valid email"),
                        ({"acceptedTerms": False}, "accept"), ({"cnic": "123"}, "CNIC"), ({"phone": "12345"}, "phone")]:
        body = {"fullName": "X Y", "email": email(), "password": PASSWORD, "acceptedTerms": True, **bad}
        r = client.post(f"{A}/auth/register", json=body)
        assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR" and needle.lower() in r.json()["error"]["message"].lower(), (bad, r.text)


def test_register_is_rate_limited_per_address(client):
    codes = [client.post(f"{A}/auth/register", json={"fullName": "X Y", "email": email(), "password": PASSWORD, "acceptedTerms": True}).status_code for _ in range(7)]
    assert codes[:6] == [201] * 6 and codes[6] == 429


def test_login_failures_roles_and_lockout(client):
    addr = email()
    signup(client, addr)
    r = client.post(f"{A}/auth/login", json={"identifier": addr, "password": "Wrong!pass1"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "INVALID_CREDENTIALS"
    r2 = client.post(f"{A}/auth/login", json={"identifier": "ghost@example.com", "password": "Wrong!pass1"})
    assert r2.json()["error"] == r.json()["error"]                      # an unknown email looks exactly like a wrong password
    r = client.post(f"{A}/auth/login", json={"identifier": addr, "password": PASSWORD, "role": "admin"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"
    for _ in range(7):
        client.post(f"{A}/auth/login", json={"identifier": addr, "password": "Wrong!pass1"})
    r = client.post(f"{A}/auth/login", json={"identifier": addr, "password": PASSWORD})
    assert r.status_code == 429 and "Retry-After" in r.headers          # even the right password waits while locked


def test_refresh_rotation_and_theft_detection(client):
    j, _ = signup(client)
    old = j["refreshToken"]
    r = client.post(f"{A}/auth/refresh", json={"refreshToken": old})
    assert r.status_code == 200
    new = r.json()
    assert new["refreshToken"] != old and set(new) == {"accessToken", "refreshToken"}
    # replaying the old token right away is treated as a race between tabs: refused, but the session lives
    assert client.post(f"{A}/auth/refresh", json={"refreshToken": old}).status_code == 401
    assert client.post(f"{A}/auth/refresh", json={"refreshToken": new["refreshToken"]}).status_code == 200
    # replaying it long after rotation means it leaked: the whole session is revoked
    db = client.app.state.ctx.db
    db.run("update app.refresh_tokens set revoked_at = now() - interval '1 hour' where token_hash = %s", [__import__("app.security", fromlist=["x"]).hash_token(old)])
    assert client.post(f"{A}/auth/refresh", json={"refreshToken": old}).status_code == 401
    latest = client.post(f"{A}/auth/refresh", json={"refreshToken": new["refreshToken"]})
    assert latest.status_code == 401                                    # the legitimate holder is signed out too
    assert client.post(f"{A}/auth/refresh", json={"refreshToken": "x" * 40}).json()["error"]["code"] == "INVALID_REFRESH"


def test_logout_revokes_the_session(client):
    j, h = signup(client)
    assert client.post(f"{A}/auth/logout", json={"refreshToken": j["refreshToken"]}).status_code == 204
    assert client.post(f"{A}/auth/refresh", json={"refreshToken": j["refreshToken"]}).status_code == 401
    assert client.post(f"{A}/auth/logout", json={}).status_code == 204


def test_bad_forged_expired_and_suspended_tokens(client):
    j, h = signup(client)
    uid = j["user"]["id"]
    assert client.get(f"{A}/auth/me", headers={"Authorization": "Bearer garbage"}).json()["error"]["code"] == "TOKEN_EXPIRED"
    forged = jwt.encode({"sub": uid, "role": "admin", "typ": "access", "iat": int(time.time()), "exp": int(time.time()) + 600}, "another-secret-" + "y" * 40, algorithm="HS256")
    assert client.get(f"{A}/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    expired = jwt.encode({"sub": uid, "role": "client", "typ": "access", "iat": int(time.time()) - 900, "exp": int(time.time()) - 600}, SECRET, algorithm="HS256")
    assert client.get(f"{A}/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    refresh_as_access = jwt.encode({"sub": uid, "typ": "refresh", "iat": int(time.time()), "exp": int(time.time()) + 600}, SECRET, algorithm="HS256")
    assert client.get(f"{A}/auth/me", headers={"Authorization": f"Bearer {refresh_as_access}"}).status_code == 401
    assert client.get(f"{A}/auth/me", headers=h).status_code == 200
    client.app.state.ctx.db.run("update app.users set status = 'suspended' where id = %s", [uid])
    assert client.get(f"{A}/auth/me", headers=h).status_code == 401      # takes effect immediately, not when the token expires
    assert client.post(f"{A}/auth/login", json={"identifier": j["user"]["email"], "password": PASSWORD}).status_code == 403


def test_change_password_keeps_this_device_and_signs_out_the_others(client):
    addr = email()
    j1, h1 = signup(client, addr)
    j2 = client.post(f"{A}/auth/login", json={"identifier": addr, "password": PASSWORD}).json()      # a second device
    assert client.post(f"{A}/users/me/password", json={"currentPassword": "Nope!nope1", "newPassword": "Newer!pass2"}, headers=h1).status_code == 422
    assert client.post(f"{A}/users/me/password", json={"currentPassword": PASSWORD, "newPassword": "weak"}, headers=h1).status_code == 400
    assert client.post(f"{A}/users/me/password", json={"currentPassword": PASSWORD, "newPassword": "Newer!pass2"}, headers=h1).status_code == 204
    assert client.post(f"{A}/auth/refresh", json={"refreshToken": j2["refreshToken"]}).status_code == 401
    assert client.post(f"{A}/auth/refresh", json={"refreshToken": j1["refreshToken"]}).status_code == 200
    assert client.post(f"{A}/auth/login", json={"identifier": addr, "password": "Newer!pass2"}).status_code == 200
    assert client.post(f"{A}/auth/login", json={"identifier": addr, "password": PASSWORD}).status_code == 401


def test_update_account(client):
    j, h = signup(client)
    other, _ = signup(client, phone="0322 5550101")
    r = client.patch(f"{A}/users/me", json={"name": "New Name", "city": "Lahore", "phone": "0333 1112223"}, headers=h)
    assert r.status_code == 200 and r.json()["name"] == "New Name" and r.json()["city"] == "Lahore" and r.json()["phone"] == "333 1112223"
    assert client.patch(f"{A}/users/me", json={"email": other["user"]["email"]}, headers=h).status_code == 409
    assert client.patch(f"{A}/users/me", json={"role": "admin", "status": "active"}, headers=h).json()["role"] == "client"     # cannot promote yourself
    assert client.patch(f"{A}/users/me", json={"name": "A"}, headers=h).status_code == 400


# ------------------------------------------------------------------------------------------------ profile
def test_profile_roundtrip_and_validation(client):
    j, h = signup(client)
    assert client.get(f"{A}/users/me/profile", headers=h).json()["completed"] is False
    body = {"province": "Punjab", "city": "Lahore", "userType": "Young adult", "employmentStatus": "Employed", "roles": ["Tenant", "Employee"],
            "ageBand": "25-34", "maritalStatus": "Single", "language": "both", "interests": ["Family", "Employment"]}
    r = client.put(f"{A}/users/me/profile", json=body, headers=h)
    assert r.status_code == 200 and r.json()["completed"] is True and r.json()["roles"] == ["Tenant", "Employee"]
    me = client.get(f"{A}/auth/me", headers=h).json()
    assert me["profileCompleted"] is True and me["preferredLanguage"] == "both" and me["city"] == "Lahore"
    assert client.get(f"{A}/users/me/profile", headers=h).json()["province"] == "Punjab"
    for bad in ({"province": "Mars"}, {"roles": ["Judge"]}, {"city": "Lahore<script>"}, {"ageBand": "17"}):
        assert client.put(f"{A}/users/me/profile", json=bad, headers=h).status_code == 400, bad
    assert client.put(f"{A}/users/me/profile", json={}, headers=h).json()["province"] is None     # a skipped form still completes setup


# ------------------------------------------------------------------------------------------------ conversations
def test_conversation_lifecycle_and_isolation(client):
    _, h = signup(client)
    _, other = signup(client)
    c = new_conv(client, h, "Can my landlord raise the rent in the middle of the contract?", topic="tenant-rights")
    assert c["title"] == "Tenant rights in Pakistan" and c["tag"] == "Property Law" and c["icon"] == "home"
    c2 = new_conv(client, h, "x" * 100)
    assert len(c2["title"]) <= 48 and c2["tag"] == "General"
    assert [x["id"] for x in client.get(f"{A}/chat/conversations", headers=h).json()["items"]] == [c2["id"], c["id"]]
    assert client.get(f"{A}/chat/conversations", headers=other).json()["items"] == []
    assert client.patch(f"{A}/chat/conversations/{c['id']}", json={"title": "My rent case"}, headers=h).json()["title"] == "My rent case"
    assert client.put(f"{A}/chat/conversations/{c['id']}/pin", json={"pinned": True}, headers=h).status_code == 204
    assert client.get(f"{A}/chat/conversations/{c['id']}", headers=h).json()["conversation"]["pinned"] is True
    for call in (lambda: client.get(f"{A}/chat/conversations/{c['id']}", headers=other),          # another user's conversation: 404, not 403
                 lambda: client.patch(f"{A}/chat/conversations/{c['id']}", json={"title": "hacked"}, headers=other),
                 lambda: client.delete(f"{A}/chat/conversations/{c['id']}", headers=other),
                 lambda: client.put(f"{A}/chat/conversations/{c['id']}/pin", json={"pinned": False}, headers=other),
                 lambda: ask(client, other, c["id"], "hello")[0]):
        assert call().status_code == 404
    assert client.get(f"{A}/chat/conversations/not-a-uuid", headers=h).status_code == 400
    assert client.delete(f"{A}/chat/conversations/{c['id']}", headers=h).status_code == 204
    assert client.get(f"{A}/chat/conversations/{c['id']}", headers=h).status_code == 404


# ------------------------------------------------------------------------------------------------ chat stream
def test_chat_answer_stream_stores_both_messages_and_names_the_conversation(client, engine):
    j, h = signup(client)
    client.put(f"{A}/users/me/profile", json={"province": "Punjab", "roles": ["Tenant"], "language": "en"}, headers=h)
    client.patch(f"{A}/users/me", json={"phone": "0300 9998887"}, headers=h)
    c = new_conv(client, h)
    r, ev = ask(client, h, c["id"], "Can my landlord raise the rent?")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    assert [e for e, _ in ev] == ["status", "status", "status", "conversation", "answer"]
    assert [d.get("state") for e, d in ev if e == "status"] == ["thinking", "searching_sources", "writing_answer"]
    conv, ans = ev[-2][1], ev[-1][1]
    assert conv["title"] == "Rent increase rules" and conv["tag"] == "Property Law" and conv["icon"] == "home"
    assert ans["kind"] == "answer" and ans["role"] == "assistant" and ans["id"] and ans["sources"][0]["id"] == 1 and ans["confidence"]["score"] == 82
    assert ans["intro"][1] == {"b": "by agreement"} and ans["feedback"] is None

    full = client.get(f"{A}/chat/conversations/{c['id']}", headers=h).json()
    assert [m["role"] for m in full["messages"]] == ["user", "assistant"]
    assert full["messages"][0]["content"] == "Can my landlord raise the rent?" and full["messages"][1]["id"] == ans["id"]
    assert full["conversation"]["title"] == "Rent increase rules" and full["conversation"]["preview"].startswith("Can my landlord")

    # what the engine was told about the user: context yes, identity never
    p = engine.calls[-1]["profile"]
    assert p["province"] == "Punjab" and p["role"] == "Tenant"
    flat = str(engine.calls[-1])
    assert j["user"]["email"] not in flat and "Test User" not in flat and "9998887" not in flat

    # a follow-up carries the conversation so far, and does not rename a conversation again
    r, ev = ask(client, h, c["id"], "And can he evict me?")
    assert [h_["role"] for h_ in engine.calls[-1]["history"]] == ["user", "assistant"]
    assert engine.calls[-1]["history"][0]["content"] == "Can my landlord raise the rent?"
    assert ev[-2][1]["title"] == "Rent increase rules"
    client.patch(f"{A}/chat/conversations/{c['id']}", json={"title": "Mine"}, headers=h)
    _, ev = ask(client, h, c["id"], "One more question about rent")
    assert ev[-2][1]["title"] == "Mine"                                  # a name the user chose is kept


def test_chat_other_message_kinds_and_language(client, engine):
    _, h = signup(client)
    c = new_conv(client, h)
    _, ev = ask(client, h, c["id"], "vague housing problem")
    assert ev[-1][1]["kind"] == "clarify" and ev[-1][1]["questions"][0]["options"] == ["Tenant", "Landlord"] and ev[-2][1]["title"] == "Housing problem"
    _, ev = ask(client, h, c["id"], "hello there")
    assert ev[-1][1]["kind"] == "info" and ev[-1][1]["reason"] == "greeting"
    _, ev = ask(client, h, c["id"], "kiraya kitna barh sakta hai", language="ur")
    assert engine.calls[-1]["language"] == "ur"
    kinds = [m["kind"] for m in client.get(f"{A}/chat/conversations/{c['id']}", headers=h).json()["messages"]]
    assert kinds == ["user", "clarify", "user", "info", "user", "answer"]


def test_failed_turns_leave_no_half_conversation(client):
    _, h = signup(client)
    c = new_conv(client, h)
    _, ev = ask(client, h, c["id"], "please fail")
    assert ev[-1][0] == "error" and ev[-1][1]["code"] == "UNAVAILABLE" and "answer" not in [e for e, _ in ev]
    _, ev = ask(client, h, c["id"], "so busy today")
    assert ev[-1][0] == "error" and ev[-1][1]["code"] == "RATE_LIMITED"
    _, ev = ask(client, h, c["id"], "boom")
    assert ev[-1][0] == "error" and ev[-1][1]["code"] == "INTERNAL" and "exploded" not in str(ev)          # internals never reach the browser
    assert client.get(f"{A}/chat/conversations/{c['id']}", headers=h).json()["messages"] == []
    _, ev = ask(client, h, c["id"], "now a real question about rent")                                       # and the user can simply try again
    assert ev[-1][0] == "answer"


def test_message_input_rules(client):
    _, h = signup(client)
    c = new_conv(client, h)
    assert ask(client, h, c["id"], "   ")[0].status_code == 400
    assert ask(client, h, c["id"], "x" * 4001)[0].status_code == 400
    r, _ = ask(client, h, c["id"], "see my file", attachmentIds=["3f2c4c1e-0000-4000-8000-000000000000"])
    assert r.status_code == 404 and "not found" in r.json()["error"]["message"]          # an attachment that does not exist (or is not theirs)
    r = client.post(f"{A}/chat/conversations/{c['id']}/messages", content=b"{" + b" " * 2_000_000 + b"}", headers={**h, "Content-Type": "application/json"})
    assert r.status_code == 413


def test_one_answer_at_a_time_per_user(client):
    j, h = signup(client)
    c = new_conv(client, h)
    client.app.state.ctx.inflight.add(j["user"]["id"])
    r, _ = ask(client, h, c["id"], "question while another is running")
    assert r.status_code == 429 and "still answering" in r.json()["error"]["message"]


def test_chat_rate_limits(pg_url):
    app = create_app(make_settings(pg_url, max_msgs_per_hour=3, max_msgs_per_day=100), engine=__import__("tests.conftest", fromlist=["x"]).FakeEngine())
    with TestClient(app) as c2:
        _, h = signup(c2)
        conv = new_conv(c2, h)
        codes = [ask(c2, h, conv["id"], f"rent question {i}")[0].status_code for i in range(4)]
        assert codes == [200, 200, 200, 429]
    app = create_app(make_settings(pg_url, max_msgs_per_hour=50, max_msgs_per_day=2), engine=__import__("tests.conftest", fromlist=["x"]).FakeEngine())
    with TestClient(app) as c3:
        _, h = signup(c3)
        conv = new_conv(c3, h)
        codes = [ask(c3, h, conv["id"], f"rent question {i}")[0].status_code for i in range(3)]
        assert codes == [200, 200, 429]
        assert "today's limit" in ask(c3, h, conv["id"], "again")[0].json()["error"]["message"]


def test_engine_down_gives_a_clear_503_and_recovers(pg_url):
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        raise ConnectionError("database is paused")

    from app.state import EngineHolder
    holder = EngineHolder(factory=factory)
    holder.RETRY_AFTER_S = 0.2
    app = create_app(make_settings(pg_url))
    with TestClient(app) as c4:
        c4.app.state.ctx.engine = holder
        _, h = signup(c4)
        conv = new_conv(c4, h)
        _, ev = ask(c4, h, conv["id"], "rent question")
        assert ev[-1][0] == "error" and ev[-1][1]["code"] == "UNAVAILABLE" and "paused" not in str(ev)
        ready = c4.get("/health/ready").json()
        assert ready["engine"] is False
        ask(c4, h, conv["id"], "rent question")
        assert calls["n"] == 1                                              # retries are throttled, not hammered
        time.sleep(0.3)
        from tests.conftest import FakeEngine
        holder._factory = FakeEngine
        _, ev = ask(c4, h, conv["id"], "rent question")
        assert ev[-1][0] == "answer"


# ------------------------------------------------------------------------------------------------ feedback and the rest
def test_feedback_reports_and_not_yet_available_features(client):
    _, h = signup(client)
    _, other = signup(client)
    c = new_conv(client, h)
    _, ev = ask(client, h, c["id"], "Can my landlord raise the rent?")
    mid = ev[-1][1]["id"]
    assert client.post(f"{A}/chat/messages/{mid}/feedback", json={"vote": "up"}, headers=h).status_code == 204
    assert client.get(f"{A}/chat/conversations/{c['id']}", headers=h).json()["messages"][1]["feedback"] == "up"
    assert client.post(f"{A}/chat/messages/{mid}/feedback", json={"vote": "sideways"}, headers=h).status_code == 400
    assert client.post(f"{A}/chat/messages/{mid}/feedback", json={"vote": "down"}, headers=other).status_code == 404
    assert client.post(f"{A}/chat/sources/report", json={"messageId": mid, "sourceId": 1}, headers=h).status_code == 204
    assert client.post(f"{A}/chat/sources/report", json={"messageId": mid, "sourceId": 1}, headers=other).status_code == 404
    assert client.post(f"{A}/chat/messages/{mid}/save", headers=h).status_code == 200                      # the Legal Vault saves it (tests/test_vault.py has the detail)
    assert client.post(f"{A}/chat/messages/{mid}/save", headers=other).status_code == 404
    for call in (lambda: client.get(f"{A}/analyses/{mid}/report", headers=h), lambda: client.post(f"{A}/analyses/{mid}/share", headers=h)):
        r = call()
        assert r.status_code == 501 and r.json()["error"]["code"] == "NOT_IMPLEMENTED"


def test_deleting_a_user_removes_their_conversations(client):
    j, h = signup(client)
    c = new_conv(client, h)
    ask(client, h, c["id"], "Can my landlord raise the rent?")
    db = client.app.state.ctx.db
    db.run("delete from app.users where id = %s", [j["user"]["id"]])
    assert db.one("select count(*) as n from app.messages where user_id = %s", [j["user"]["id"]])["n"] == 0
    assert db.one("select count(*) as n from app.conversations where user_id = %s", [j["user"]["id"]])["n"] == 0
