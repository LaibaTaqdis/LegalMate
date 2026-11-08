"""Which language should this answer be in? Decided by code, from what the user actually wrote, so it is the same every time.

Three answer languages:
    "en"        English
    "ur"        Urdu in Urdu script
    "ur-roman"  Urdu written in Latin letters ("Roman Urdu"), the way people type it on a phone

The user's message wins. An explicit choice in the composer (en / ur / ur-roman) overrides it; "auto" (the default) detects.
A reply that carries no language of its own ("ok", "yes", a tapped one-word option) keeps the language of the conversation.
"""
from __future__ import annotations

import re

LANGS = ("en", "ur", "ur-roman")

_URDU_LETTER = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_WORD = re.compile(r"[A-Za-z؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿']+")

# Roman Urdu words that are not English words, so one or two of them is a reliable signal.
_STRONG = set("""
kya kia kiya hai hain nahi nahin nhi nai mujhe mujhay mujhko mera meri mere humein hamein hamara hamari aap aapko aapka aapki aapke
tum tumhara tumhari tumhein ko ka ki ke kaise kese kaisay kyun kyu kiun kyunke kyunki kab kahan kahaan kon kaun koi kisi kuch sab
agar lekin magar aur bhi sakta sakti sakte chahiye chahie karna karne karni karo karein karen kare kijiye kijiyega batao bataiye
batayein bata btao wala wali wale mein maine usko usne unhon unka unki unke iska iski iske abhi phir bohat bahut zyada hota hoti hote
hoga hogi honge tha thi thay raha rahi rahay rahe gaya gayi gaye diya dena dene lena lene liya jaye jaaye jana jata jati aata aati
chalta rehta rehna baar bol bolo bolna dekho dekhein samajh samjha samjhao shukriya mehrbani meharbani
kiraya kiraye kirayedar malik makan dukan ghar zameen jaidad jayedad mukadma muqadma adalat wakeel qanoon qanun haq haqooq huqooq
nokri naukri tankhwah tankhah mulazim talaq nikah khula shohar biwi walid walida beta beti bachay bachon thana qarz qarza mehngai
sarkar hukumat dawa dastavez dastaveez muahida muaahida ijazat sabit saboot saboot jurm saza jurmana zamanat gawah gawahi
""".split())
# Short words that are also English or names: half a point each.
_WEAK = set("jo ho se pe ye yeh wo woh mat ab".split())

_GREETING_ROMAN = re.compile(r"^\s*(salam|salaam|assalam[\w\s\-']*|aoa|shukriya|jazak\w*)\W*$", re.I)


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text or "")


def _roman_score(tokens: list[str]) -> float:
    s = 0.0
    for t in tokens:
        w = t.lower()
        if w in _STRONG:
            s += 1.0
        elif w in _WEAK:
            s += 0.5
    return s


def detect_one(text: str) -> tuple[str, bool]:
    """(language, confident). Not confident means the text is too short or too bare to say ("ok", "yes", "1", "Tenant")."""
    toks = _tokens(text)
    urdu = [t for t in toks if _URDU_LETTER.search(t)]
    latin = [t for t in toks if not _URDU_LETTER.search(t)]
    if urdu and (len(urdu) >= 2 or not latin) and len(urdu) >= 0.35 * len(toks):
        return "ur", True
    if _GREETING_ROMAN.match(text or ""):
        return "ur-roman", False                                  # "salam": a hint, but history may know better
    score = _roman_score(latin)
    if score >= 2 or (score >= 1 and score / max(1, len(latin)) >= 0.3):
        return "ur-roman", True
    return "en", len(latin) >= 4


def conversation_language(text: str, history: list[dict] | None = None, hint: str | None = None) -> str:
    """Language of the user's latest message; if it says nothing, the language of the last message that did.
    `hint` is the analyser's guess ("en", "ur", "ur-roman"); it can only turn English into Roman Urdu on short or marked text."""
    lang, sure = detect_one(text)
    if not sure:
        for h in reversed(history or []):
            if h.get("role") == "user":
                prev, prev_sure = detect_one(h.get("content") or "")
                if prev_sure:
                    lang = prev
                    break
    if lang == "en" and hint in ("ur-roman", "ur") and not _URDU_LETTER.search(text or ""):
        toks = _tokens(text)
        if len(toks) <= 5 or _roman_score(toks) >= 0.5:
            lang = "ur-roman"
    return lang


def resolve(requested: str | None, text: str, history: list[dict] | None = None, hint: str | None = None) -> str:
    """requested: "auto" (or None) | "en" | "ur" | "ur-roman"."""
    if requested in LANGS:
        return requested
    return conversation_language(text, history, hint)
