"""Answer language: English stays English, Urdu script gets Urdu, Roman Urdu gets Roman Urdu. Zero model calls."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chat import lang, prompts                           # noqa: E402
from chat.engine import ChatEngine                       # noqa: E402
from chat.strings import _T, tr                          # noqa: E402

from tests.test_chat_offline import ANALYSIS, ANSWER, FakeKB, ScriptedLLM, passage   # noqa: E402

CASES = [
    ("Can my landlord raise the rent without telling me?", "en"),
    ("Police stopped me and asked me to handover student card of my university should i give?", "en"),
    ("my friend want a divorce from husband", "en"),
    ("who will win the world cup", "en"),
    ("مالک کس صورت میں کرایہ دار کو بے دخل کروا سکتا ہے؟", "ur"),
    ("رینٹ ٹربیونل میں درخواست کیسے دی جاتی ہے؟", "ur"),
    ("میرے landlord نے کرایہ بڑھا دیا ہے", "ur"),
    ("yay rent trubenl kia hai jo tum baar baar bol rahay ho", "ur-roman"),
    ("kiraya kitna barh sakta hai", "ur-roman"),
    ("mera malik makan mujhe ghar se nikal raha hai kya kar sakta hoon", "ur-roman"),
    ("mujhe talaq chahiye shohar maar peet karta hai", "ur-roman"),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_language_follows_what_the_user_wrote(text, expected):
    assert lang.resolve("auto", text) == expected
    assert lang.resolve(None, text) == expected


def test_an_explicit_choice_beats_detection():
    assert lang.resolve("ur", "Can my landlord raise the rent?") == "ur"
    assert lang.resolve("en", "kiraya kitna barh sakta hai") == "en"
    assert lang.resolve("ur-roman", "Can my landlord raise the rent?") == "ur-roman"


def test_a_bare_reply_keeps_the_language_of_the_conversation():
    hist = [{"role": "user", "content": "mera malik makan mujhe ghar se nikal raha hai"}, {"role": "assistant", "content": "x"}]
    assert lang.resolve("auto", "ok", hist) == "ur-roman"
    assert lang.resolve("auto", "1", hist) == "ur-roman"
    hist_ur = [{"role": "user", "content": "مالک مکان نے مجھے نکال دیا ہے"}]
    assert lang.resolve("auto", "thanks", hist_ur) == "ur"
    assert lang.resolve("auto", "ok") == "en"                                    # nothing to go on


def test_a_clear_new_language_wins_over_history():
    hist = [{"role": "user", "content": "مالک مکان نے مجھے نکال دیا ہے"}]
    assert lang.resolve("auto", "Can my landlord evict me without notice?", hist) == "en"


def test_the_analyser_can_turn_short_english_looking_text_into_roman_urdu():
    assert lang.resolve("auto", "qanoon batao", hint="ur-roman") == "ur-roman"
    assert lang.resolve("auto", "Can my landlord raise the rent without telling me?", hint="ur-roman") == "en"      # a long plain English sentence stays English


def test_every_fixed_text_exists_in_all_three_languages():
    for key, row in _T.items():
        assert set(row) == {"en", "ur", "ur-roman"}, key
        assert all(v.strip() for v in row.values()), key
    assert any("؀" <= ch <= "ۿ" for ch in tr("greeting", "ur"))
    assert not any("؀" <= ch <= "ۿ" for ch in tr("greeting", "ur-roman"))
    assert "{scope}" not in tr("note_repealed", "ur", scope="Punjab")


def test_the_answer_prompt_names_all_three_languages():
    sysmsg = prompts.ANSWER_SYSTEM
    assert '"ur-roman"' in sysmsg and "Roman Urdu" in sysmsg and "Urdu script" in sysmsg
    assert prompts.answer_messages("q", history=[], profile_line="", answer_language="ur-roman", passages=[passage(1)])[-1]["content"].startswith("answer_language: ur-roman")


# ---- the engine ------------------------------------------------------------------------------------------------------
def _answer(text, **kw):
    llm = ScriptedLLM(dict(ANALYSIS), dict(ANSWER))
    eng = ChatEngine(FakeKB([passage(1)]), llm)
    out = eng.respond(text, **kw)
    return out, llm


def test_urdu_question_gets_urdu_headings_and_disclaimer():
    out, llm = _answer("مالک کس صورت میں کرایہ دار کو بے دخل کروا سکتا ہے؟")
    m = out["message"]
    assert m["language"] == "ur" and m["lawTitle"] == tr("law_title", "ur") and m["disclaimer"] == tr("disclaimer", "ur")
    assert llm.sent[-1][-1]["content"].startswith("answer_language: ur")


def test_roman_urdu_question_is_answered_in_roman_urdu():
    out, llm = _answer("yay rent trubenl kia hai jo tum baar baar bol rahay ho")
    m = out["message"]
    assert m["language"] == "ur-roman" and m["lawTitle"] == "Qanoon kya kehta hai"
    assert llm.sent[-1][-1]["content"].startswith("answer_language: ur-roman")


def test_english_stays_english_even_if_the_interface_is_urdu():
    out, llm = _answer("Can my landlord raise the rent without telling me?")
    assert out["message"]["language"] == "en" and out["message"]["lawTitle"] == "What the law says"
    assert llm.sent[-1][-1]["content"].startswith("answer_language: en")


def test_forced_language_is_used_for_the_answer():
    out, llm = _answer("Can my landlord raise the rent without telling me?", language="ur-roman")
    assert out["message"]["language"] == "ur-roman"


def test_fixed_messages_follow_the_language_too():
    eng = ChatEngine(FakeKB([]), ScriptedLLM(dict(ANALYSIS)))
    assert eng.respond("obscure kiraya sawal hai kya", language="auto")["message"]["text"] == tr("no_source", "ur-roman")
    ur = ChatEngine(FakeKB([]), ScriptedLLM(dict(ANALYSIS))).respond("مجھے کرایہ کے بارے میں بتائیں")
    assert ur["message"]["text"] == tr("no_source", "ur") and ur["message"]["language"] == "ur"
    g = ChatEngine(FakeKB([]), ScriptedLLM(None)).respond("Hello!")
    assert g["message"]["text"] == tr("greeting", "en") and g["message"]["language"] == "en"


def test_model_reply_in_the_wrong_script_is_replaced_by_the_fixed_text():
    wrong = {"intent": "out_of_scope", "language": "ur", "emergency": False, "jurisdiction": None, "title": "x", "tag": "Other",
             "needs_clarification": False, "questions": [], "search_queries": ["a", "b", "c"], "reply": "I can only help with Pakistani law."}
    out = ChatEngine(FakeKB([]), ScriptedLLM(wrong)).respond("آج موسم کیسا ہے")
    assert out["message"]["text"] == tr("out_of_scope", "ur")


def test_clarifying_prompt_is_localised():
    ask = dict(ANALYSIS, needs_clarification=True, questions=[{"text": "Aap kiraya daar hain ya malik?", "options": ["Kiraya daar", "Malik"]}])
    out = ChatEngine(FakeKB([passage(1)]), ScriptedLLM(ask)).respond("mujhe apni property ka masla hai kya karoon")
    assert out["message"]["kind"] == "clarify" and out["message"]["intro"] == tr("clarify_intro", "ur-roman")

