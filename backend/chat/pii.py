"""Strip personal identifiers from text BEFORE it is sent to an external LLM (DeepSeek's servers are outside Pakistan).

Conservative regexes for the identifiers that matter most; names and free-text addresses cannot be removed reliably
by pattern, so the profile sent to the model never includes them and the system prompt tells the model not to ask.
"""
from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("IBAN", re.compile(r"\bPK\d{2}[A-Z]{4}\d{16}\b", re.I)),
    ("CNIC", re.compile(r"(?<!\d)\d{5}[- ]?\d{7}[- ]?\d(?!\d)")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+92|0092|92|0)[ -]?3\d{2}[ -]?\d{7}(?!\d)")),
    ("PHONE", re.compile(r"(?<!\d)0\d{2,3}[ -]?\d{7,8}(?!\d)")),
    ("CARD", re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")),
]


def scrub(text: str) -> tuple[str, dict[str, int]]:
    """-> (clean text, counts of what was removed). Replaces with [CNIC], [PHONE], [EMAIL], [IBAN], [CARD]."""
    counts: dict[str, int] = {}
    out = text
    for label, rx in _PATTERNS:
        out, n = rx.subn(f"[{label}]", out)
        if n:
            counts[label] = counts.get(label, 0) + n
    return out, counts
