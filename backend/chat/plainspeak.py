"""Keeps the machinery out of what the user reads.

The model is told not to talk about "the database", "the passages" or "the text available to me", but a prompt is only a request.
This runs on every piece of answer text before it is sent and rewrites those phrases into plain speech. Citation markers
([[1]]) and **bold** are left alone.
"""
from __future__ import annotations

import re

# (pattern, replacement); applied in order. Replacements keep the sentence grammatical.
_RULES: list[tuple[re.Pattern, str]] = [pattern_repl for pattern_repl in (
    # "In the text available to me, ..." / "In the passages I have, ..."  ->  "As far as I could find, ..."
    (re.compile(r"\b[Ii]n (?:the |my |our )?(?:law |legal )?(?:text|texts|passages?|provisions?|material|sources?)(?: that (?:is|are) )?(?: (?:available|provided|supplied|given) (?:to me|here))?(?: that)?(?: I (?:have|can see|was given|was shown))?,"), "As far as I could find,"),
    (re.compile(r"\b[Ii]n (?:the |my |our )?(?:law |legal )?text (?:available to me|I (?:have|can see|was given))\b"), "As far as I could find"),
    # "... in the database that ..." -> "... that ..."
    (re.compile(r"\s+(?:in|within|from|inside|under) (?:the |my |our |this )?(?:legal |law )?(?:database|knowledge base|data ?base|dataset|data|records|system|corpus)\b"), ""),
    (re.compile(r"\b(?:the |my |our )?(?:legal |law )?(?:database|knowledge base|dataset|corpus)\b"), "the laws I have"),
    # "The passages I have ..." / "the supplied passages" / "the law text available to me"
    (re.compile(r"\b(?:[Tt]he )?(?:supplied |provided |available |given )?(?:law )?(?:passages?|excerpts?|extracts?)(?: (?:I have|I was given|available to me|provided to me|supplied to me|provided|supplied))?\b"), "the laws I found"),
    (re.compile(r"\b(?:[Tt]he )?(?:law )?text(?:s)? (?:available to me|I have|I was given|provided to me|supplied to me)\b"), "what I found"),
    (re.compile(r"\b(?:[Tt]he )?(?:sources|material) (?:provided|supplied|given|available) (?:to me|here)\b"), "what I found"),
    (re.compile(r"\b(?:retrieved|retrieval)\b"), "found"),
    (re.compile(r"\b(?:as an? )?(?:AI|language model|chatbot|LLM)\b(?: assistant)?"), "assistant"),
)]
_CAPS = re.compile(r"(^|[.!?]\s+|\n)(the laws I found|what I found|as far as I could find)")
_SPACES = re.compile(r"[ \t]{2,}")


def plain(text: str) -> str:
    if not text:
        return text
    out = text
    for pat, rep in _RULES:
        out = pat.sub(rep, out)
    out = _CAPS.sub(lambda m: m.group(1) + m.group(2)[0].upper() + m.group(2)[1:], out)     # sentence starts with a capital again
    out = re.sub(r"(?<=[a-z]) ,", ",", out)
    return _SPACES.sub(" ", out)


def plain_answer(ans: dict) -> dict:
    """The model's answer JSON with every user-visible string cleaned (the `used` quotes are the law's own words and stay untouched)."""
    clean = dict(ans)
    for k in ("intro", "law", "law_title", "important", "outro"):
        if isinstance(clean.get(k), str):
            clean[k] = plain(clean[k])
    if isinstance(clean.get("steps"), list):
        clean["steps"] = [plain(s) if isinstance(s, str) else s for s in clean["steps"]]
    if isinstance(clean.get("follow_ups"), list):
        clean["follow_ups"] = [plain(s) if isinstance(s, str) else s for s in clean["follow_ups"]]
    return clean
