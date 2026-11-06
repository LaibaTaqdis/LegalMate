"""Text cleaning for extracted legal PDFs: encoding repair, running header/footer removal,
footnote separation, and reflow into paragraphs (each tagged with its PDF page).

Everything here is deterministic and conservative: it never rewrites legal wording, it only
repairs encoding artefacts and strips layout noise.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

FFFD = "�"
# U+2015 bar, U+2E3A/3B long dashes, U+2212 minus, U+23AF line ext., PUA symbol-font dashes/bullets
_DASH_VARIANTS = "―⸺⸻−⎯‒"

# ---------------------------------------------------------------- encoding repair

_PAIRED_QUOTE = re.compile(r"(?<![^\s(\[])" + FFFD + r"(?=[^\s" + FFFD + r"])([^" + FFFD + r"\n]{1,120}?)(?<=\S)" + FFFD)
_FOOTNOTE_MARK = re.compile(r"(?<![\w])\d{1,2}(?=\[)")


def fix_encoding(text: str, stats: Counter | None = None) -> str:
    """Repair the common mojibake in these PDFs. `stats` counts what was repaired."""
    stats = stats if stats is not None else Counter()
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("\xa0", " ").replace("​", "").replace("\x0c", "\n").replace("­", "-")
    t = t.replace("", " ").replace("‎", "").replace("‏", "")
    # The PDFs use many glyphs for the em-dash that follows "Short title.": unify them.
    n = sum(t.count(c) for c in _DASH_VARIANTS)
    if n:
        stats["dash_variants"] += n
        t = t.translate({ord(c): "—" for c in _DASH_VARIANTS})
    # OCR-damaged NADRA gazettes: "presid€nt" -> "president"
    n = len(re.findall("(?<=[a-z])€(?=[a-z])", t))
    if n:
        stats["euro_as_e"] += n
        t = re.sub("(?<=[a-z])€(?=[a-z])", "e", t)

    # Lines where U+FFFD replaced the *spaces* (e.g. "THE�PAKISTAN�ORDINANCE")
    lines = []
    for line in t.split("\n"):
        if FFFD in line and " " not in line.strip() and line.count(FFFD) >= 2:
            stats["fffd_as_space"] += line.count(FFFD)
            line = line.replace(FFFD, " ")
        lines.append(line)
    t = "\n".join(lines)

    if FFFD in t:
        n0 = t.count(FFFD)
        t = _PAIRED_QUOTE.sub(lambda m: "“" + m.group(1) + "”", t)       # "Government"
        t = re.sub(r"(?<=[A-Za-z])" + FFFD + r"(?=s\b)", "’", t)               # President's
        t = re.sub(r"(?<=s)" + FFFD + r"(?=\s)", "’", t)                       # Workers' Welfare
        t = re.sub(r"(?<=[.:;,])" + FFFD, "—", t)                              # "Legis.<dash>The"
        t = re.sub(r"\s*" + FFFD + r"\s*", " — ", t)                           # anything left: dash
        stats["fffd_repaired"] += n0

    # "__" / "___" used as an em-dash ("Explanation.__ If", "as follows:___")
    n = len(re.findall(r"(?<!_)_{2,3}(?!_)", t))
    if n:
        stats["underscore_dash"] += n
        t = re.sub(r"(?<!_)_{2,3}(?!_)", "—", t)

    # Inline amendment footnote markers: "1[(b) any of the]" -> "[(b) any of the]"
    n = len(_FOOTNOTE_MARK.findall(t))
    if n:
        stats["footnote_marks"] += n
        t = _FOOTNOTE_MARK.sub("", t)

    t = re.sub(r"[ \t]+", " ", t)
    return t


# ---------------------------------------------------------------- header / footer removal

_PAGE_NO = re.compile(r"^\s*(page\s+)?\d{1,4}(\s+of\s+\d{1,4})?\s*$", re.I)
_SECTION_START = re.compile(r"^\s*(\d{1,3}[A-Z]{0,2}(-[A-Z]{1,2})?\.|\(\w{1,5}\))\s")
# Footnote lines: number glued to a verb ("1Subs. by ...", "1This Act was ...") or "1. Subs."/"2. Ins."
_FOOTNOTE_GLUED = re.compile(
    r"^\s*\d{1,2}\s?(?:Subs\.|Ins\.|Inserted\b|Substituted\b|Added\b|Omitted\b|Rep\.|Repealed\b|"
    r"The\s+(?:words|figures|full\s+stop|comma|colon|semi-?colon|letters|brackets|expression|marginal|proviso|"
    r"sub-?section|section|word)\b|Ibid\b|Re-?numbered\b|Vide\b|See\b|"
    r"This\s+(?:Act|Ordinance|Code|Order)\s+was\b|Cl\.|Clause\s+\(|Sub-?section\s+\()")
_FOOTNOTE_DOTTED = re.compile(r"^\s*\d{1,2}\s*[\.\)]\s+(?:Subs\.|Ins\.|Rep\.|Added\s+by|Inserted\s+by|Substituted\s+by)")


def _is_footnote_start(line: str) -> bool:
    return bool(_FOOTNOTE_GLUED.match(line) or _FOOTNOTE_DOTTED.match(line))


def _norm_line(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", s.strip().lower()))


def detect_running_lines(pages: list[str], frac: float = 0.2) -> set[str]:
    """Lines (digits normalised) that repeat in the header/footer zone of many pages."""
    if len(pages) < 6:
        return set()
    c: Counter = Counter()
    for p in pages:
        ls = [l for l in p.split("\n") if l.strip()]
        zone = ls[:4] + ls[-4:]
        seen = set()
        for l in zone:
            s = _norm_line(l)
            if 6 <= len(s) <= 110 and not _SECTION_START.match(l) and s not in seen:
                seen.add(s)
                c[s] += 1
    thr = max(3, int(len(pages) * frac))
    return {s for s, n in c.items() if n >= thr}


def split_footnotes(lines: list[str]) -> tuple[list[str], list[str]]:
    """Footnotes sit at the page bottom. Find the first footnote-looking line in the last third
    of the page and treat everything after it as footnote text."""
    n = len(lines)
    start = max(0, n - max(14, n // 3))
    for i in range(start, n):
        if _is_footnote_start(lines[i]):
            return lines[:i], lines[i:]
    return lines, []


def clean_pages(raw_pages: list[str]) -> tuple[list[tuple[int, list[str]]], list[tuple[int, str]], Counter]:
    """-> ([(page_no_1based, body_lines)], [(page_no, footnote_text)], repair_stats)"""
    stats: Counter = Counter()
    pages = [fix_encoding(p, stats) for p in raw_pages]
    running = detect_running_lines(pages)
    body, notes = [], []
    for i, p in enumerate(pages, start=1):
        ls = [l.rstrip() for l in p.split("\n")]
        kept = []
        for l in ls:
            if _PAGE_NO.match(l):
                stats["page_number_lines"] += 1
                continue
            if l.strip() and _norm_line(l) in running:
                stats["running_header_lines"] += 1
                continue
            kept.append(l)
        kept, fn = split_footnotes(kept)
        if fn:
            notes.append((i, " ".join(x.strip() for x in fn if x.strip())))
            stats["footnote_blocks"] += 1
        body.append((i, kept))
    return body, notes, stats


# ---------------------------------------------------------------- reflow into paragraphs

_ORD = r"(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH)"
_CONT_RE = re.compile(
    r"^\s*(?:THE\s+)?(?P<ord>" + _ORD + r"\s+)?(?P<kind>CHAPTER|PART|SCHEDULE|ORDER|APPENDIX|ANNEXURE)\b"
    r"\s*(?P<id>[IVXLC]+\b|\d+(?:\.\d+)?[A-Z]?\b|[A-Z]\b)?\s*(?P<rest>.*)$", re.I)


class _Container:
    """Callable like a compiled regex: returns a match-like object for genuine container headings."""

    def match(self, line: str):
        l = line.strip()
        if not l or len(l) > 70 or l.endswith((";", ",")):
            return None
        m = _CONT_RE.match(l)
        if not m:
            return None
        kind = m.group("kind")
        if kind != kind.upper() and not (m.group("id") and not (m.group("rest") or "").strip()):
            return None                                   # prose such as "Part II of the First Schedule"
        rest = (m.group("rest") or "").strip()
        if rest and not (rest[0] in "-–—:(" or rest.isupper()):
            return None
        if kind.upper() in ("CHAPTER", "PART", "ORDER") and not m.group("id"):
            return None
        if kind.upper() in ("SCHEDULE", "APPENDIX", "ANNEXURE") and not (m.group("ord") or m.group("id") or l.isupper()):
            return None
        return m


CONTAINER = _Container()
_NUM_ONLY = re.compile(r"^\s*(\d{1,3}[A-Z]{0,2}(-[A-Z]{1,2})?)\.?\s*$")
_CLAUSE_ONLY = re.compile(r"^\s*\(\w{1,5}\)\s*$")
_NEW_PARA = re.compile(
    r"^\s*(\(\w{1,5}\)|\[?\d{1,3}[A-Z]{0,2}(-[A-Z]{1,2})?\.\s+[A-Z\[“\"(]|"
    r"(Provided|Explanation|Illustration|Exception|Note|Preamble|WHEREAS)\b)")


@dataclass
class Para:
    text: str
    page_start: int
    page_end: int
    kind: str = "text"      # text | container | container_title


def build_paragraphs(body: list[tuple[int, list[str]]]) -> list[Para]:
    """Flatten page lines into paragraphs. Section-number-only lines and clause markers are glued
    to the following line; container headings (CHAPTER/PART/SCHEDULE/ORDER) stay isolated."""
    flat: list[tuple[int, str]] = []
    for pg, ls in body:
        for l in ls:
            flat.append((pg, l.strip()))

    # 1) glue "57." / "(a)" onto the next non-empty line
    glued: list[tuple[int, str]] = []
    i = 0
    while i < len(flat):
        pg, l = flat[i]
        if l and (_NUM_ONLY.match(l) or _CLAUSE_ONLY.match(l)):
            j = i + 1
            while j < len(flat) and not flat[j][1]:
                j += 1
            if j < len(flat) and not (_NUM_ONLY.match(flat[j][1]) or CONTAINER.match(flat[j][1])):
                marker = l if l.endswith(")") or l.endswith(".") else l + "."
                glued.append((pg, marker + " " + flat[j][1]))
                i = j + 1
                continue
        glued.append((pg, l))
        i += 1

    # 2) reflow
    paras: list[Para] = []
    cur: list[str] = []
    cur_s = cur_e = 0
    prev_kind = "text"

    def flush(kind="text"):
        nonlocal cur, prev_kind
        if cur:
            paras.append(Para(re.sub(r"\s+", " ", " ".join(cur)).strip(), cur_s, cur_e, kind))
        cur = []
        prev_kind = kind

    for pg, l in glued:
        if not l:
            if cur and re.search(r"[.;:—]\s*$", cur[-1]):
                flush()
            continue
        m = CONTAINER.match(l)
        short_container = bool(m) and len(l) <= 60 and not re.search(r"[a-z]{4,}.*[a-z]{4,}.*[a-z]{4,}", m.group("rest") or "")
        if short_container:
            flush()
            paras.append(Para(l, pg, pg, "container"))
            prev_kind = "container"
            continue
        if prev_kind == "container" and len(l) <= 90 and not _NEW_PARA.match(l) and not l.endswith("."):
            paras.append(Para(l, pg, pg, "container_title"))
            prev_kind = "container_title"
            continue
        if cur and _NEW_PARA.match(l):
            flush()
        if not cur:
            cur_s = pg
        cur_e = pg
        # A line ending in "-" is almost always a real compound ("house-" / "trespass", "sub-" / "section"):
        # these PDFs break lines at existing hyphens, not mid-word. Keep the hyphen, drop the space.
        if cur and cur[-1].endswith("-") and l[:1].islower():
            cur[-1] = cur[-1] + l
        else:
            cur.append(l)
        prev_kind = "text"
    flush()
    return paras
