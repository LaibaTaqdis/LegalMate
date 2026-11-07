"""Offline tests for the chat engine: ZERO DeepSeek calls, no database.

    python -m tests.test_chat_offline         (or: pytest backend/tests)
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from pathlib import Path

import httpx

from chat import llm as llm_mod
from chat.confidence import score
from chat.engine import ChatEngine, norm_jurisdiction
from chat.llm import BudgetExceeded, CacheMiss, DeepSeek, LLMError, parse_json
from chat.pii import scrub
from chat.richtext import cited_ids, strip_markup, to_segments
from chat.settings import Settings
from chat.verify import verify


# ---------------------------------------------------------------- fixtures
def passage(i=1, **kw):
    base = dict(chunk_id=f"c{i}", doc_id=f"d{i}", act_title="Punjab Rented Premises Act, 2009", year=2009, doc_type="act",
                jurisdiction="Punjab", legal_status="unverified", status_scope=None, status_note="", section_label="Section 15",
                heading="Grounds for eviction", section_nums=["15"], page_start=6, page_end=6, source_urls=[], amended_by_titles=[],
                cosine=0.78, body="15. Grounds for eviction. A landlord may seek eviction of the tenant if the tenant has failed to pay rent "
                                  "within thirty days after the expiry of the period.")
    base.update(kw)
    return base


def settings(tmp: Path, **kw) -> Settings:
    base = Settings(deepseek_api_key="test-key", deepseek_base_url="http://x", deepseek_model="deepseek-flash", thinking=False,
                    max_calls_per_run=3, daily_call_cap=100, mode="live", cache_dir=tmp / "cache", ledger_path=tmp / "ledger.jsonl",
                    price_in_miss=0.3, price_in_hit=0.03, price_out=1.2, database_url="")
    return replace(base, **kw)


class FakeResp:
    status_code = 200

    def __init__(self, text):
        self._t = text

    def json(self):
        return {"choices": [{"message": {"content": self._t}}], "usage": {"prompt_tokens": 100, "completion_tokens": 50}}


# ---------------------------------------------------------------- privacy
def test_pii_scrub():
    t, n = scrub("My CNIC is 35202-1234567-1, call 0300-1234567 or +92 321 7654321, mail a.b@example.com, IBAN PK36SCBL0000001123456702")
    assert "35202" not in t and "1234567" not in t and "@" not in t and "PK36" not in t
    assert n.get("CNIC") == 1 and n.get("PHONE", 0) >= 2 and n.get("EMAIL") == 1 and n.get("IBAN") == 1
    t2, n2 = scrub("Section 489F of the Penal Code applies within 30 days; rent is Rs 25000")
    assert t2 == "Section 489F of the Penal Code applies within 30 days; rent is Rs 25000" and not n2


# ---------------------------------------------------------------- rich text
def test_richtext():
    segs = to_segments("Cannot **evict you** [[1]] unless rent unpaid [[2]][[9]].", {1, 2})
    assert segs == ["Cannot ", {"b": "evict you"}, " ", {"cite": 1}, " unless rent unpaid ", {"cite": 2}, "."], segs
    assert cited_ids("a [[1]] b [[3]]") == [1, 3]
    assert strip_markup("**x** y [[1]]") == "x y"


# ---------------------------------------------------------------- verifier
def test_verifier_catches_cheating():
    ps = [passage(1)]
    ans = {"intro": "A landlord may evict if rent is unpaid [[1]], see Section 15 [[1]].",
           "law": "The tenant must pay within thirty days [[1]] and a fine of 50000 rupees applies under Section 99 [[1]]. Invented claim [[7]].",
           "steps": ["Pay the rent [[1]]."], "important": "", "outro": "",
           "used": [{"id": 1, "quote": "failed to pay rent within thirty days after the expiry of the period"},
                    {"id": 7, "quote": "ghost"}]}
    r = verify(ans, ps)
    assert r.invalid_cites == [7]
    assert r.quotes[1]["verified"] is True
    assert r.unverified_sections == ["99"], r.unverified_sections
    assert "50000" in r.unverified_numbers
    bad = verify({**ans, "used": [{"id": 1, "quote": "tenant shall be evicted immediately without notice"}]}, ps)
    assert bad.quotes[1]["verified"] is False and "landlord" in bad.quotes[1]["quote"].lower()   # replaced by a REAL sentence
    assert 0 < r.cited_fraction <= 1


def test_confidence():
    ps = [passage(1)]
    good = verify({"intro": "x is true [[1]].", "law": "A landlord may seek eviction if rent is unpaid [[1]].", "steps": [], "used": [{"id": 1, "quote": "failed to pay rent"}]}, ps)
    s = score(ps, good, True, 8)
    assert s["score"] >= 70 and set(s) >= {"score", "relevance", "agreement", "recency", "checked", "verifiedAt"}
    assert score(ps, good, False, 8)["score"] <= 45
    rep = score([passage(1, legal_status="repealed")], good, True, 8)["recency"]
    amd = score([passage(1, amended_by_titles=["X (Amendment) Act, 2025"])], good, True, 8)["recency"]
    assert rep < amd < s["recency"]


# ---------------------------------------------------------------- LLM client rails
def test_llm_cache_ledger_budget_replay(monkeypatch_httpx=None):
    calls = []
    real_post = httpx.post
    httpx.post = lambda *a, **k: (calls.append(1), FakeResp('{"ok": true}'))[1]
    try:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            llm = DeepSeek(settings(tmp))
            m = [{"role": "user", "content": "hello"}]
            r1 = llm.complete(m, tag="t")
            r2 = llm.complete(m, tag="t")                       # identical request: from cache, no network
            assert not r1.cached and r2.cached and len(calls) == 1 and llm.cache_hits == 1
            assert len((tmp / "ledger.jsonl").read_text().splitlines()) == 1 and "test-key" not in (tmp / "ledger.jsonl").read_text()
            llm.complete([{"role": "user", "content": "b"}], tag="t")
            llm.complete([{"role": "user", "content": "c"}], tag="t")
            try:
                llm.complete([{"role": "user", "content": "d"}], tag="t")      # 4th live call, cap is 3
                raise AssertionError("cap not enforced")
            except BudgetExceeded:
                pass
            assert len(calls) == 3
            # daily cap is enforced from the ledger even in a NEW process
            llm2 = DeepSeek(settings(tmp, max_calls_per_run=50, daily_call_cap=3))
            try:
                llm2.complete([{"role": "user", "content": "e"}], tag="t")
                raise AssertionError("daily cap not enforced")
            except BudgetExceeded:
                pass
            # replay mode never uses the network
            rp = DeepSeek(settings(tmp, mode="replay"))
            assert rp.complete(m, tag="t").cached
            try:
                rp.complete([{"role": "user", "content": "never seen"}], tag="t")
                raise AssertionError("replay allowed a miss")
            except CacheMiss:
                pass
            assert len(calls) == 3
    finally:
        httpx.post = real_post
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1} and parse_json('Sure! {"a": 2} done') == {"a": 2}


# ---------------------------------------------------------------- engine
class ScriptedLLM:
    """Stands in for DeepSeek: returns scripted JSON per tag and counts 'live' calls."""

    def __init__(self, analyse, answer=None, rescue=None):
        self.script = {"analyse": analyse, "answer": answer, "rescue": rescue}
        self.live_calls = 0

    def complete(self, messages, *, tag, **kw):
        self.live_calls += 1
        v = self.script[tag]
        if isinstance(v, list):                      # several answers in a row (first look, second look)
            v = v.pop(0)
        if v is None:
            raise LLMError(f"no scripted response for {tag}")
        if isinstance(v, Exception):
            raise v
        return type("R", (), {"text": json.dumps(v)})()


class FakeKB:
    def __init__(self, passages):
        self.p = passages
        self.queries = []

    def search(self, q, jur=None, k=10, **kw):
        self.queries.append((q, jur))
        return [dict(p, score=1.0 / (i + 1)) for i, p in enumerate(self.p)][:k]


ANALYSIS = {"intent": "legal_question", "language": "en", "emergency": False, "jurisdiction": "Punjab", "title": "Eviction for unpaid rent",
            "tag": "Property Law", "needs_clarification": False, "questions": [],
            "search_queries": ["tenant unpaid rent eviction", "Punjab Rented Premises Act grounds for eviction"], "reply": ""}
ANSWER = {"sufficient": True, "intro": "Your landlord can seek eviction if you do not pay rent [[1]].",
          "law_title": "What the law says", "law": "A landlord may **seek eviction** if the tenant fails to pay rent within thirty days [[1]]. See Section 15 [[1]].",
          "steps": ["Pay or deposit the rent now [[1]]."], "important": "Do not ignore a notice. See Section 99 for fines.", "outro": "Want help with a reply?",
          "used": [{"id": 1, "quote": "tenant has failed to pay rent within thirty days"}], "follow_ups": ["Can I deposit rent in court?"]}


def test_engine_flows():
    kb = FakeKB([passage(1), passage(2, doc_id="d2", chunk_id="c2", act_title="Other Act, 1990", year=1990, section_nums=["3"])])
    # greeting: no LLM call at all
    llm = ScriptedLLM(ANALYSIS, ANSWER)
    eng = ChatEngine(kb, llm)
    out = eng.respond("Hello!")
    assert out["message"]["kind"] == "info" and llm.live_calls == 0
    # legal question: exactly 2 calls, frontend shape, verification applied
    out = eng.respond("My landlord wants to evict me. my CNIC is 35202-1234567-1", profile={"province": "Punjab", "city": "Lahore", "name": "Ali Khan"})
    m, meta = out["message"], out["meta"]
    assert llm.live_calls == 2 and meta["llm_calls_this_turn"] == 2
    assert m["kind"] == "answer" and m["intro"][-2] == {"cite": 1}
    assert [s["id"] for s in m["sources"]] == [1] and m["sources"][0]["quoteVerified"] is True
    assert m["sources"][0]["type"] == "Act" and m["confidence"]["score"] > 0
    assert "99" in meta["verify"]["unverified_sections"]                      # the invented section was caught
    assert meta["pii_removed"] == {"CNIC": 1}
    assert out["conversation"] == {"title": "Eviction for unpaid rent", "tag": "Property Law"}
    assert kb.queries[0][1] == "Punjab"                                       # jurisdiction reached retrieval
    assert isinstance(m["law"], list) and {"b": "seek eviction"} in m["law"]
    # clarification: 1 call only, no retrieval
    kb2 = FakeKB([passage(1)])
    llm = ScriptedLLM({**ANALYSIS, "needs_clarification": True, "questions": [{"text": "Are you the tenant or the landlord?", "options": ["Tenant", "Landlord"]}]})
    out = ChatEngine(kb2, llm).respond("I need help with my house")
    assert out["message"]["kind"] == "clarify" and llm.live_calls == 1 and not kb2.queries
    assert out["message"]["questions"][0]["options"] == ["Tenant", "Landlord"]
    # ...but never asks twice
    llm = ScriptedLLM({**ANALYSIS, "needs_clarification": True, "questions": [{"text": "again?", "options": ["a", "b"]}]}, ANSWER)
    out = ChatEngine(FakeKB([passage(1)]), llm).respond("Tenant", history=[{"role": "assistant", "content": "q", "kind": "clarify"}])
    assert out["message"]["kind"] == "answer"
    # out of scope: 1 call, polite reply
    llm = ScriptedLLM({**ANALYSIS, "intent": "out_of_scope", "reply": "I can only help with Pakistani law."})
    out = ChatEngine(FakeKB([]), llm).respond("who will win the world cup")
    assert out["message"]["kind"] == "info" and llm.live_calls == 1
    # budget exhausted: no exception, a friendly info message
    out = ChatEngine(FakeKB([passage(1)]), ScriptedLLM(BudgetExceeded("cap"))).respond("question about tenancy")
    assert out["message"]["kind"] == "info" and out["message"]["reason"] == "busy"
    # progress callbacks fire in order for a full legal answer
    seen: list[str] = []
    ChatEngine(FakeKB([passage(1)]), ScriptedLLM(ANALYSIS, ANSWER)).respond("question about tenancy", on_status=seen.append)
    assert seen == ["understanding", "searching_sources", "writing_answer"], seen
    # no sources found: no answer call
    llm = ScriptedLLM(ANALYSIS, ANSWER)
    out = ChatEngine(FakeKB([]), llm).respond("obscure question")
    assert out["message"]["reason"] == "no_source" and llm.live_calls == 1
    # a model that cites a source it was never given cannot slip through
    llm = ScriptedLLM(ANALYSIS, {**ANSWER, "intro": "Fake claim that is quite long [[5]].", "law": "Nothing real is said here at all [[5]].",
                                 "steps": [], "used": []})
    out = ChatEngine(FakeKB([passage(1)]), llm).respond("tenant question here")
    assert out["message"]["sources"] == [] and out["meta"]["verify"]["issues"]
    assert out["meta"]["verify"]["cited_fraction"] == 0.0               # an invalid citation is not a citation
    assert out["message"]["confidence"]["score"] == 0                    # nothing grounded -> zero confidence


def test_profile_never_leaks_identity():
    from chat.engine import profile_line
    line = profile_line({"name": "Ali Khan", "cnic": "35202-1234567-1", "phone": "0300", "email": "a@b.c", "address": "House 1", "province": "Punjab", "city": "Lahore"})
    assert "Ali" not in line and "35202" not in line and "@" not in line and "House" not in line and "province=Punjab" in line


def test_jurisdiction_mapping():
    assert norm_jurisdiction("Islamabad Capital Territory") == "ICT" and norm_jurisdiction("Lahore") == "Punjab"
    assert norm_jurisdiction("Sindh") is None and norm_jurisdiction(None) is None


def test_second_look_when_the_first_search_misses():
    insufficient = {**ANSWER, "sufficient": False, "intro": "I could not find a specific law that directly answers this.", "law": "", "steps": ["Ask a lawyer."],
                    "used": [], "follow_ups": []}
    rescue = {"search_queries": ["Code of Criminal Procedure refusal to give name and residence", "Refusal to give name and residence", "Constitution Article 4"]}
    # first answer insufficient -> rescue queries -> better answer: 4 calls, the second answer is used
    kb = FakeKB([passage(1)])
    llm = ScriptedLLM(ANALYSIS, [insufficient, ANSWER], rescue)
    seen: list[str] = []
    out = ChatEngine(kb, llm, rescue=True).respond("police asked for my card", on_status=seen.append)
    assert llm.live_calls == 4 and out["message"]["sufficient"] is True and out["message"]["sources"], out["message"]
    assert out["meta"]["second_look"]["helped"] is True and seen[-2:] == ["searching_deeper", "writing_answer"], seen
    assert any("refusal to give name" in q.lower() for q, _ in kb.queries)                  # the rescue queries really were searched
    # second look does not help: the first answer is kept (still 4 calls)
    llm = ScriptedLLM(ANALYSIS, [insufficient, insufficient], rescue)
    out = ChatEngine(FakeKB([passage(1)]), llm, rescue=True).respond("police asked for my card")
    assert llm.live_calls == 4 and out["message"]["sufficient"] is False and out["meta"]["second_look"]["helped"] is False
    # the budget runs out during the second look: the user still gets the first answer
    llm = ScriptedLLM(ANALYSIS, insufficient, BudgetExceeded("cap"))
    out = ChatEngine(FakeKB([passage(1)]), llm, rescue=True).respond("police asked for my card")
    assert out["message"]["kind"] == "answer" and out["message"]["sufficient"] is False
    # a sufficient first answer never triggers it (2 calls), and it can be switched off
    llm = ScriptedLLM(ANALYSIS, ANSWER, rescue)
    ChatEngine(FakeKB([passage(1)]), llm).respond("tenant question")
    assert llm.live_calls == 2
    llm = ScriptedLLM(ANALYSIS, insufficient, rescue)
    ChatEngine(FakeKB([passage(1)]), llm).respond("tenant question")        # off by default
    assert llm.live_calls == 2


def test_nothing_the_user_sees_talks_about_the_machinery():
    from chat import engine as eng_mod, prompts
    banned = ("database", "passage", "retriev", "text available to me", "my data")
    user_facing = [eng_mod.DISCLAIMER, eng_mod.BUSY_TEXT, eng_mod.EMERGENCY]
    out = ChatEngine(FakeKB([]), ScriptedLLM(ANALYSIS, ANSWER)).respond("obscure question")             # the "no source" reply
    user_facing.append(out["message"]["text"])
    for text in user_facing:
        assert not any(b in text.lower() for b in banned), text
    assert "NEVER describe how you work" in prompts.ANSWER_SYSTEM and "in the database" not in prompts.ANSWER_SYSTEM


def test_plain_speech_filter_removes_machinery_talk():
    leaky = {**ANSWER, "intro": "I could not find a law in the database that answers this [[1]].",
             "law": "The passages I have say a landlord may **seek eviction** [[1]]. In the text available to me, there is no other rule.",
             "important": "The law text available to me is partly outdated.", "steps": ["Check the passages provided to me again [[1]]."]}
    out = ChatEngine(FakeKB([passage(1)]), ScriptedLLM(ANALYSIS, leaky)).respond("tenant question")["message"]
    flat = json.dumps([out["intro"], out["law"], out["steps"], out["important"]]).lower()
    for bad in ("database", "passage", "text available", "text i have"):
        assert bad not in flat, (bad, flat)
    assert "as far as i could find" in flat and {"b": "seek eviction"} in out["law"] and {"cite": 1} in out["intro"]     # bold and citations survive


def test_act_router_and_toc_detection():
    from chat.engine import ActRouter
    r = ActRouter([("d1", "Court Fees Act, 1870", "Federal", False), ("d2", "Punjab Pre-emption Act, 1991", "Punjab", False),
                   ("d3", "Qanun-e-Shahadat (Amendment) Act, 2025", "Federal", True), ("d4", "Contract act, 1872", "Federal", False)])
    assert r.match("Court Fees Act 1870 ad valorem fee on plaint") == ["d1"]
    assert r.match("right under the Pre-emption Act of a neighbour") == ["d2"]          # jurisdiction prefix is optional
    assert r.match("Contract Act 1872 oral agreement") == ["d4"] and r.match("Qanun-e-Shahadat amendment") == []   # amendments never routed
    assert r.match("an act of god") == []
    from ingest.s3_chunk import looks_like_toc
    toc = chr(10).join(f"{i}. Heading number {i} of the contents" for i in range(1, 12))
    law = chr(10).join(["15. Grounds for eviction.- A landlord may seek eviction of the tenant if the tenant has failed to pay rent for thirty days."] * 7)
    assert looks_like_toc(toc) and not looks_like_toc(law)


def test_number_words_match_digits():
    from chat.verify import verify, words_to_digits
    assert "25" in words_to_digits("twenty-five per centum") and "30" in words_to_digits("thirty days")
    ps = [passage(1, body="the wife may surrender fifty per centum of deferred dower")]
    assert verify({"intro": "She may surrender 50 percent [[1]].", "law": "", "steps": [], "used": []}, ps).unverified_numbers == []
    assert verify({"intro": "She may surrender 77 percent [[1]].", "law": "", "steps": [], "used": []}, ps).unverified_numbers == ["77"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok  ", t.__name__)
    print(f"\n{len(tests)} tests passed (no DeepSeek calls were made)")
