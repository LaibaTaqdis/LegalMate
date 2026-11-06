"""Deterministic checks on the model's answer. No LLM calls: this is code, so it cannot be talked around.

  * every [[n]] marker refers to a passage that was actually supplied
  * every quote is a verbatim substring of its passage (otherwise it is replaced by the closest real sentence)
  * every "section N / article N" mentioned appears in the supplied passages
  * every figure (days, rupees, years) in the legal text appears in the supplied passages
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from .richtext import cited_ids

_SECTION_REF = re.compile(
    r"(?i)\b(?:sections?|sec\.?|s\.|articles?|art\.?)\s*((?:\d+[A-Z]{0,2}(?:-[A-Z])?)(?:\s*(?:,|and|&|to|-|–)\s*\d+[A-Z]{0,2}(?:-[A-Z])?)*)")
_NUM = re.compile(r"(?<![\w\[])\d[\d,]*(?![\w\]])")


def norm(s: str) -> str:
    s = (s or "").lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"[\[\]*]", "", s)
    return re.sub(r"\s+", " ", s).strip()


_UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
          "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_NUMWORD = re.compile(r"\b(?:(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[\s-](one|two|three|four|five|six|seven|eight|nine))?|"
                      r"(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen)|(hundred))\b")


def words_to_digits(text: str) -> str:
    """'twenty-five per centum' -> '25 per centum', so a figure the model writes as digits matches a statute that spells it out.
    The digit form is appended next to the words, nothing is removed."""
    def rep(m):
        if m.group(1):
            return m.group(0) + " " + str(_TENS[m.group(1)] + (_UNITS[m.group(2)] if m.group(2) else 0))
        if m.group(3):
            return m.group(0) + " " + str(_UNITS[m.group(3)])
        return m.group(0) + " 100"
    return _NUMWORD.sub(rep, text)


def sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.;:])\s+|\n+", text) if len(x.strip()) > 20]


@dataclass
class Report:
    invalid_cites: list[int] = field(default_factory=list)
    quotes: dict = field(default_factory=dict)             # id -> {"quote": str, "verified": bool}
    unverified_sections: list[str] = field(default_factory=list)
    unverified_numbers: list[str] = field(default_factory=list)
    cited_fraction: float = 0.0
    cited_ids: list[int] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def quote_rate(self) -> float:
        return (sum(1 for q in self.quotes.values() if q["verified"]) / len(self.quotes)) if self.quotes else 0.0


def _best_sentence(quote: str, body: str) -> str:
    cands = sentences(body) or [body[:200]]
    q = norm(quote)
    qt = set(re.findall(r"[a-z0-9]+", q))

    def sc(s: str) -> tuple:
        st = set(re.findall(r"[a-z0-9]+", norm(s)))
        return (len(qt & st) / (len(qt | st) or 1), len(s) > 60, difflib.SequenceMatcher(None, q, norm(s)).ratio())   # overlap first, then prefer real sentences over headings
    return max(cands, key=sc)[:240]


def verify(answer: dict, passages: list[dict], max_chars: int = 1500) -> Report:
    r = Report()
    n = len(passages)
    bodies = [p["body"][:max_chars] for p in passages]
    # act titles and section labels count as source text too: "Karachi Rent Restriction Act, 1953" legitimately contains 1953
    all_text = norm(" ".join(bodies) + " " + " ".join(f"{p.get('act_title', '')} {p.get('section_label', '')} {p.get('heading', '')}" for p in passages))
    legal_fields = [answer.get("intro", ""), answer.get("law", "")] + list(answer.get("steps") or [])
    other_fields = [answer.get("important", ""), answer.get("outro", "")]
    every = legal_fields + other_fields

    # 1. citations must point at supplied passages
    ids = [i for f in every for i in cited_ids(f)]
    r.invalid_cites = sorted({i for i in ids if not 1 <= i <= n})
    r.cited_ids = sorted({i for i in ids if 1 <= i <= n})
    if r.invalid_cites:
        r.issues.append(f"invalid citation numbers removed: {r.invalid_cites}")

    # 2. quotes must be verbatim
    for u in answer.get("used") or []:
        try:
            i = int(u.get("id"))
        except (TypeError, ValueError):
            continue
        if not 1 <= i <= n:
            continue
        q = str(u.get("quote", "")).strip()
        ok = bool(q) and norm(q) in norm(bodies[i - 1])
        if not ok:
            q = _best_sentence(q, bodies[i - 1])
            r.issues.append(f"quote for [{i}] was not verbatim; replaced by the closest real sentence")
        r.quotes[i] = {"quote": q, "verified": ok}
    for i in r.cited_ids:                                   # cited but no quote given: take the best sentence
        if i not in r.quotes:
            r.quotes[i] = {"quote": _best_sentence(" ".join(legal_fields), bodies[i - 1]), "verified": False}

    # 3. section / article numbers mentioned must exist in the passages
    known = set()
    for p in passages:
        known |= {x.lower() for x in (p.get("section_nums") or [])}
    mentioned = set()
    for f in every:
        for m in _SECTION_REF.finditer(re.sub(r"\[\[\d+\]\]", "", f)):
            mentioned |= {x.lower().replace(" ", "") for x in re.findall(r"\d+[A-Za-z]{0,2}(?:-[A-Za-z])?", m.group(1))}
    for s in sorted(mentioned):
        in_text = re.search(rf"(?<![\d]){re.escape(s)}(?![\d])", all_text) is not None
        if s not in known and not in_text:
            r.unverified_sections.append(s)
    if r.unverified_sections:
        r.issues.append(f"section/article numbers not found in the sources: {r.unverified_sections}")

    # 4. figures (days, amounts, years) in the legal text must exist in the passages
    legal_text = re.sub(r"\[\[\d+\]\]", " ", " ".join(legal_fields + [answer.get("important", "")]))
    legal_text = _SECTION_REF.sub(" ", legal_text)
    flat = words_to_digits(all_text).replace(",", "")
    for m in _NUM.finditer(legal_text):
        token = m.group(0).replace(",", "")
        if len(token) >= 2 and not re.search(rf"(?<!\d){re.escape(token)}(?!\d)", flat):
            r.unverified_numbers.append(token)
    r.unverified_numbers = sorted(set(r.unverified_numbers))
    if r.unverified_numbers:
        r.issues.append(f"figures not found in the sources: {r.unverified_numbers}")

    # 5. how much of the legal text is backed by a citation
    sents = [s for f in legal_fields for s in sentences(f)]
    r.cited_fraction = (sum(1 for s in sents if any(1 <= i <= n for i in cited_ids(s))) / len(sents)) if sents else 0.0   # only VALID cites count
    return r
