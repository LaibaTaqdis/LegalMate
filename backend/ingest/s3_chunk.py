"""Stage 3 - parse legal structure (Part/Chapter/Order > Section/Article/Rule) and chunk.

Chunks follow legal boundaries: one section = one chunk when it fits; long sections are split at
sub-clause boundaries; tiny neighbouring sections are merged. Every chunk carries a context header
("Act > Chapter > Section - Heading") that is prepended for embedding, plus page range, jurisdiction,
status, etc.  Documents whose structure cannot be recovered fall back to paragraph windows.

Output: data/processed/chunks.jsonl, data/interim/parse_stats.json
Run:  python -m ingest.s3_chunk
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
from dataclasses import dataclass, field

from tqdm import tqdm

from .config import (INTERIM_DIR, MAX_CHUNK_CHARS, MIN_CHUNK_CHARS, OVERLAP_CHARS, PROCESSED_DIR,
                     TARGET_CHUNK_CHARS)
from .textclean import CONTAINER

PARAS_DIR = INTERIM_DIR / "paras"

HEADER_RE = re.compile(r"^\[?(?P<num>\d{1,3})(?P<suf>(?:-?[A-Z]{1,2})?)\.\s+(?P<rest>\S.*)$", re.S)
FOOTNOTE_REST = re.compile(r"^(Subs\.|Ins\.|Rep\.|Added by|Inserted by|Substituted by|Omitted by)", re.I)
# A stub says it is repealed/omitted *by something*, or is just a bracketed [Repealed]/[Omitted] marker.
STUB_RE = re.compile(r"\b(?:Rep\.|Repealed|Omitted|Deleted)\s+(?:by|vide)\b|\[\s*\*?\s*(?:Repeal(?:ed)?|Omitted|Deleted)\.?\s*\]|^\[?\d{1,3}[A-Z]{0,2}\.\s*(?:\[?\*[\s*]*\]?|Omitted|Repealed)\.?\s*$", re.I)
TOC_WORD = re.compile(r"\bC\s?O\s?N\s?T\s?E\s?N\s?T\s?S\b|Updated till \d{1,2}\.\d{1,2}\.\d{4}")
SUBCLAUSE_RE = re.compile(r"^\s*\(\w{1,5}\)\s")
TAIL_SPLIT_CHARS = 12000


# ---------------------------------------------------------------- numbering-chain detection (DP)

@dataclass
class Cand:
    idx: int
    n: int
    suf: str
    rest: str
    bonus: float = 0.0


def find_candidates(paras: list[list]) -> list[Cand]:
    out = []
    for i, (text, _, _, kind) in enumerate(paras):
        if kind != "text":
            continue
        m = HEADER_RE.match(text)
        if not m:
            continue
        rest = m.group("rest")
        if FOOTNOTE_REST.match(rest) or not re.match(r"[A-Z\[“(\"‘]", rest):
            continue
        c = Cand(i, int(m.group("num")), m.group("suf").lstrip("-"), rest)
        head = re.search(r"[.—:]\s*—|\.\s+[A-Z\[(]|\.—", rest[:170])
        c.bonus = 0.25 if head else 0.0
        out.append(c)
    return out


def trans_cost(a: Cand, b: Cand) -> float | None:
    """Cost of b following a in a numbering chain (None = not allowed)."""
    if b.n == a.n + 1 and not b.suf:
        return 0.0
    if b.n == a.n and b.suf > a.suf:
        return 0.0                      # 9 -> 9A -> 9B
    if a.n + 2 <= b.n <= a.n + 16 and not b.suf:
        return 0.3 * (b.n - a.n - 1)     # numbers legitimately missing (repealed ranges, lost headers)
    if b.n <= 2 and a.n >= 3 and not b.suf:
        return 1.5                       # restart: new chapter/schedule/order, or TOC -> body
    return None


def _best_chain_once(cands: list[Cand]) -> tuple[list[Cand], list[bool]]:
    """Longest plausible numbering chain. Returns (chain, restart_flags)."""
    n = len(cands)
    if not n:
        return [], []
    best = [0.0] * n
    prev = [-1] * n
    restart = [False] * n
    for i in range(n):
        b = cands[i]
        start = 0.0 if b.n <= 3 else 3.0
        best[i] = 1.0 + b.bonus - start
        for j in range(max(0, i - 120), i):
            c = trans_cost(cands[j], b)
            if c is None:
                continue
            s = best[j] + 1.0 + b.bonus - c
            if s > best[i]:
                best[i], prev[i], restart[i] = s, j, (c == 1.5)
    k = max(range(n), key=lambda i: best[i])
    chain, flags = [], []
    while k != -1:
        chain.append(cands[k])
        flags.append(restart[k])
        k = prev[k]
    chain.reverse()
    flags.reverse()
    return chain, flags


def best_chain(cands: list[Cand]) -> tuple[list[Cand], list[bool]]:
    """Chain after chain: when numbering jumps too far to link (e.g. 265N -> 337 because the PDF omits
    266-336), keep going with the candidates that follow the previous chain."""
    chain, flags = [], []
    rest = cands
    while rest:
        c, f = _best_chain_once(rest)
        if len(c) < 3 and chain:
            break
        chain += c
        flags += f
        rest = [x for x in rest if x.idx > c[-1].idx]
    return chain, flags


# ---------------------------------------------------------------- units

@dataclass
class Unit:
    kind: str                       # section | article | rule | item | preamble
    num: str                        # "379", "9A", "" for preamble
    heading: str
    paras: list[list] = field(default_factory=list)
    part: str = ""
    chapter: str = ""
    order: str = ""
    schedule: str = ""
    run: int = 0
    stub: bool = False

    @property
    def text(self) -> str:
        return "\n".join(p[0] for p in self.paras)

    @property
    def pages(self) -> tuple[int, int]:
        return min(p[1] for p in self.paras), max(p[2] for p in self.paras)


def split_heading(rest: str) -> tuple[str, str]:
    # Heading ends at ".—", ".–", ".-" ("Short title.— (1) This Act...") or at an em-dash right after the heading.
    m = re.search(r"\.\s*[–—\-]+\s*|\s—\s*", rest[:200])
    if m:
        return rest[:m.start()].strip(" .[]"), rest[m.end():]
    m = re.search(r"\.\s+(?=[A-Z\[(“])", rest[:170])
    if m:
        return rest[:m.start()].strip(" .[]"), rest[m.end():]
    return rest[:100].strip(" .[]"), rest[100:]


def container_name(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _embedded_header_re(n: int) -> "re.Pattern[str]":
    """Section number n written inside a paragraph: after sentence-ending punctuation, with optional
    '*'/'[' markers and optionally a footnote digit glued on ('1500.' = footnote 1 + section 500)."""
    glue = r"[1-9]?" if n >= 10 else r""
    return re.compile(
        r"(?:(?<=^)|(?<=[\s\]\).;:,”\"’]))(?P<pre>[\[\*]*)(?P<glue>" + glue + r")(?P<num>" + str(n)
        + r"(?:-?[A-Z]{1,2})?)\.\s+(?=[A-Z\[“(])")


def repair_embedded_headers(paras: list[list]) -> tuple[list[list], int]:
    """Chain-guided repair: wherever the section numbering has a gap (a.n < n < b.n), look for the missing
    number inside the paragraphs between the two neighbours and split the paragraph there."""
    cands = find_candidates(paras)
    chain, flags = best_chain(cands)
    splits: dict[int, dict[int, tuple[int, str]]] = {}   # para idx -> {start: (end of header token, new prefix)}
    for (a, b), f in zip(zip(chain, chain[1:]), flags[1:]):
        if f or not (a.n + 1 < b.n <= a.n + 60):
            continue
        for n in range(a.n + 1, b.n):
            rx = _embedded_header_re(n)
            for i in range(a.idx, b.idx):
                if paras[i][3] != "text":
                    continue
                for m in rx.finditer(paras[i][0]):
                    # position 0 with no marker is already an ordinary candidate (the DP rejected it on purpose)
                    if m.start() == 0 and not m.group("pre") and not m.group("glue"):
                        continue
                    splits.setdefault(i, {})[m.start()] = (m.end(), ("[" if "[" in m.group("pre") else "") + m.group("num") + ". ")
                    break
                else:
                    continue
                break
    if not splits:
        return paras, 0
    out, n_split = [], 0
    for i, p in enumerate(paras):
        if i not in splits:
            out.append(p)
            continue
        text = p[0]
        starts = sorted(splits[i])
        head = text[:starts[0]].strip()
        if head:
            out.append([head, p[1], p[2], p[3]])
        bounds = starts[1:] + [len(text)]
        for st, nxt in zip(starts, bounds):
            end, prefix = splits[i][st]
            out.append([prefix + text[end:nxt].strip(), p[1], p[2], p[3]])
            n_split += 1
    return out, n_split


def build_units(paras: list[list], is_constitution: bool) -> tuple[list[Unit], dict]:
    n_repaired = 0
    for _ in range(2):                                   # second pass catches headers uncovered by the first
        paras, k = repair_embedded_headers(paras)
        n_repaired += k
        if not k:
            break
    cands = find_candidates(paras)
    chain, flags = best_chain(cands)
    stats = {"candidates": len(cands), "headers": len(chain), "runs": 0, "toc_runs_dropped": 0, "headers_repaired": n_repaired}
    if len(chain) < 3:
        return [], stats

    # runs = chain segments split at restarts
    runs: list[list[Cand]] = []
    for c, f in zip(chain, flags):
        if f or not runs:
            runs.append([])
        runs[-1].append(c)
    stats["runs"] = len(runs)

    # TOC detection: a run whose sections carry almost no text of their own
    header_idx = {c.idx: (ri, c) for ri, r in enumerate(runs) for c in r}
    all_hdr = sorted(header_idx)
    gap_len: dict[int, int] = {}
    for a, b in zip(all_hdr, all_hdr[1:] + [len(paras)]):
        gap_len[a] = sum(len(paras[k][0]) for k in range(a, b) if paras[k][3] == "text")
    skip_ranges = []
    for ri, r in enumerate(runs):
        lens = [gap_len[c.idx] for c in r]
        if len(r) >= 5 and statistics.median(lens) < 110:
            # A table of contents is followed by a body that repeats its numbers. If nothing later repeats
            # them, these are just short sections of a short Act, not a TOC.
            mine = {(c.n, c.suf) for c in r}
            later = {(c.n, c.suf) for r2 in runs[ri + 1:] for c in r2}
            if len(mine & later) < 0.5 * len(mine):
                continue
            stats["toc_runs_dropped"] += 1
            end = r[-1].idx + 1                       # up to the last TOC entry only: keep the preamble after it
            while end < len(paras) and paras[end][3] in ("container", "container_title"):
                end += 1                              # trailing "THE SCHEDULE" / repeated title lines of the TOC
            skip_ranges.append((r[0].idx, end))
    dropped_runs = {ri for ri, r in enumerate(runs) if any(s <= r[0].idx < e for s, e in skip_ranges)}

    def skipped(i: int) -> bool:
        return any(s <= i < e for s, e in skip_ranges)

    units: list[Unit] = []
    cur: Unit | None = None
    pre = Unit("preamble", "", "Preamble")
    ctx = {"part": "", "chapter": "", "order": "", "schedule": ""}
    last_container = None
    for i, p in enumerate(paras):
        text, ps, pe, kind = p
        if skipped(i):
            continue
        if kind == "container":
            m = CONTAINER.match(text)
            k = m.group("kind").upper() if m else "PART"
            name = container_name(text)
            if not units and k in ("SCHEDULE", "ORDER", "APPENDIX", "ANNEXURE"):
                last_container = "SKIP"      # a schedule cannot precede Section 1: leftover of the table of contents
                continue
            if k == "PART":
                ctx["part"], ctx["chapter"] = name, ""
            elif k == "CHAPTER":
                ctx["chapter"] = name
            elif k == "ORDER":
                ctx["order"], ctx["chapter"] = name, ""
            else:                                        # SCHEDULE / APPENDIX / ANNEXURE
                ctx["schedule"], ctx["order"], ctx["chapter"], ctx["part"] = name, "", "", ""
            last_container = k
            continue
        if kind == "container_title":
            if last_container == "SKIP":
                continue
            key = {"PART": "part", "CHAPTER": "chapter", "ORDER": "order"}.get(last_container, "schedule")
            ctx[key] = f"{ctx[key]} - {container_name(text)}" if ctx[key] else container_name(text)
            continue
        if i in header_idx and header_idx[i][0] not in dropped_runs:
            ri, c = header_idx[i]
            heading, body = split_heading(c.rest)
            ukind = "article" if is_constitution and not ctx["schedule"] else ("rule" if (ctx["order"] or ctx["schedule"]) else "section")
            cur = Unit(ukind, f"{c.n}{c.suf}", heading, [[text, ps, pe, kind]], ctx["part"], ctx["chapter"],
                       ctx["order"], ctx["schedule"], ri)
            units.append(cur)
            continue
        if cur is None:
            text = TOC_WORD.sub("", text).strip()
            if text:
                pre.paras.append([text, ps, pe, kind])
        else:
            cur.paras.append(p)

    # Stub = a section that is only "[Repealed]/[Omitted by ...]". Its *own* text is dropped, but anything
    # that follows it in the PDF (a Schedule, a table) must survive as separate "tail" material.
    final: list[Unit] = []
    for u in units:
        head = u.paras[0][0]
        if u.kind != "preamble" and STUB_RE.search(head[:300]):
            rest = u.paras[1:]
            if len(rest) == 0 or sum(len(p[0]) for p in rest) < 150:
                u.stub = True
                final.append(u)
            elif len(head) < 420:
                u.paras, u.stub = [u.paras[0]], True
                final.append(u)
                final.append(Unit("tail", "", f"Schedule/appendix material after {unit_label(u)}", rest,
                                  u.part, u.chapter, u.order, u.schedule, u.run))
            else:
                final.append(u)
        else:
            final.append(u)
    units = final
    if pre.paras and sum(len(p[0]) for p in pre.paras) >= 120:
        units.insert(0, pre)
    return units, stats


# ---------------------------------------------------------------- chunking

def nice(x: str) -> str:
    """Title-case ALL-CAPS headings but keep Roman numerals upper-case (ORDER VII -> Order VII)."""
    x = re.sub(r"\s+", " ", x).strip()
    if not x.isupper():
        return x
    return " ".join(w if re.fullmatch(r"[IVXLC]+", w.strip("(),.-")) else w.capitalize() for w in x.split(" "))


def unit_label(u: Unit) -> str:
    if u.kind == "preamble":
        return "Preamble"
    if u.kind == "tail":
        return u.heading
    if u.kind == "article":
        return f"Article {u.num}"
    if u.kind == "rule":
        scope = re.sub(r"\s*-\s.*$", "", u.order) if u.order else re.sub(r"\s*-\s.*$", "", u.schedule)
        return f"{nice(scope)}, Rule {u.num}" if scope else f"Rule {u.num}"
    return f"Section {u.num}"


def ctx_path(u: Unit) -> str:
    parts = [x for x in (u.schedule, u.part, u.order, u.chapter) if x]
    return " > ".join(nice(x) for x in parts)


def split_text(paras: list[list], max_chars: int, target: int) -> list[list[list]]:
    """Split a unit's paragraphs into groups <= max_chars, breaking at paragraph boundaries."""
    groups, cur, size = [], [], 0
    for p in paras:
        L = len(p[0])
        if L > max_chars:                                # one huge paragraph: split by sentence/semicolon
            if cur:
                groups.append(cur); cur, size = [], 0
            pieces = re.split(r"(?<=[.;:])\s+", p[0])
            buf = ""
            for s in pieces:
                if len(buf) + len(s) + 1 > target and buf:
                    groups.append([[buf, p[1], p[2], "text"]])
                    buf = buf[-OVERLAP_CHARS:].split(" ", 1)[-1] + " " + s
                else:
                    buf = (buf + " " + s).strip()
            if buf:
                groups.append([[buf, p[1], p[2], "text"]])
            continue
        if size + L > target and cur:
            groups.append(cur); cur, size = [], 0
        cur.append(p); size += L + 1
    if cur:
        if groups and sum(len(p[0]) for p in cur) < 150 and                 sum(len(p[0]) for p in groups[-1]) + sum(len(p[0]) for p in cur) <= int(max_chars * 1.3):
            groups[-1].extend(cur)      # don't leave a stranded stub as its own chunk
        else:
            groups.append(cur)
    return groups


def make_chunks(doc: dict, units: list[Unit], notes: list[list]) -> list[dict]:
    chunks: list[dict] = []
    title = doc["title"]
    disp = title if (doc["jurisdiction"] == "Federal" or doc["jurisdiction"].lower() in title.lower()) else f"{title} ({doc['jurisdiction']})"
    live = [u for u in units if not u.stub]
    notes_by_page: dict[int, str] = {}
    for pg, t in notes:
        notes_by_page[pg] = t

    def emit(label_units: list[Unit], paras: list[list], part_i=0, part_n=1):
        u0, u1 = label_units[0], label_units[-1]
        text = "\n".join(p[0] for p in paras).strip()
        if not text:
            return
        if len(label_units) > 1:
            label = f"{unit_label(u0)} to {u1.num}" if u0.kind == u1.kind != "preamble" else unit_label(u0)
            heading = "; ".join(x.heading for x in label_units[:3])[:140]
        else:
            label, heading = unit_label(u0), u0.heading
        path = ctx_path(u0)
        header = f"{disp}" + (f" > {path}" if path else "") + f" > {label}" + (f" - {heading}" if heading else "")
        if part_n > 1:
            header += f" (part {part_i + 1}/{part_n})"
        ps = min(p[1] for p in paras)
        pe = max(p[2] for p in paras)
        note = " ".join(notes_by_page[pg] for pg in range(ps, pe + 1) if pg in notes_by_page)[:700]
        ordinal = len(chunks)
        chunks.append({
            "chunk_id": f"{doc['doc_id']}-{ordinal:04d}", "doc_id": doc["doc_id"], "ordinal": ordinal,
            "act_title": title, "year": doc["year"], "doc_type": doc["doc_type"], "jurisdiction": doc["jurisdiction"],
            "applies_to": doc["applies_to"], "tier": doc["tier"], "legal_status": doc["legal_status"],
            "status_scope": doc.get("status_scope", doc["jurisdiction"]), "status_note": doc.get("status_note", "")[:200],
            "unit_type": u0.kind, "section_no": "" if u0.kind == "tail" else (u0.num if len(label_units) == 1 else f"{u0.num}-{u1.num}"),
            "section_nums": [x.num for x in label_units if x.num], "section_label": label, "heading": heading, "part": u0.part, "chapter": u0.chapter,
            "order": u0.order, "schedule": u0.schedule, "page_start": ps, "page_end": pe,
            "part_index": part_i + 1, "parts_total": part_n,
            "header": header, "text": text, "embed_text": header + "\n" + text, "n_chars": len(text),
            "amendment_notes": note, "source_urls": doc["source_urls"],
            "chunk_hash": hashlib.sha1(text.encode()).hexdigest()[:10],
        })

    expanded: list[Unit] = []
    for u in live:
        if len(u.text) > TAIL_SPLIT_CHARS and u.kind in ("section", "article", "rule"):
            cum, cut = 0, None
            for k, p in enumerate(u.paras):
                cum += len(p[0])
                if cum >= TAIL_SPLIT_CHARS:
                    cut = k + 1
                    break
            tail = u.paras[cut:] if cut else []
            clause_like = sum(bool(SUBCLAUSE_RE.match(p[0])) for p in tail) / max(1, len(tail))
            if len(tail) >= 3 and clause_like < 0.35:
                head = Unit(u.kind, u.num, u.heading, u.paras[:cut], u.part, u.chapter, u.order, u.schedule, u.run)
                expanded.append(head)
                expanded.append(Unit("tail", "", f"Schedule/appendix material after {unit_label(u)}", tail,
                                     u.part, u.chapter, u.order, u.schedule, u.run))
                continue
        expanded.append(u)
    live = expanded

    i = 0
    while i < len(live):
        u = live[i]
        L = len(u.text)
        if L > MAX_CHUNK_CHARS:
            groups = split_text(u.paras, MAX_CHUNK_CHARS, TARGET_CHUNK_CHARS)
            for gi, g in enumerate(groups):
                emit([u], g, gi, len(groups))
            i += 1
            continue
        # merge small neighbours that share context
        group, size = [u], L
        j = i + 1
        while (size < MIN_CHUNK_CHARS and j < len(live) and live[j].kind == u.kind and live[j].kind not in ("preamble", "tail")
               and (live[j].part, live[j].chapter, live[j].order, live[j].schedule) == (u.part, u.chapter, u.order, u.schedule)
               and size + len(live[j].text) <= MAX_CHUNK_CHARS):
            group.append(live[j]); size += len(live[j].text) + 1; j += 1
        emit(group, [p for x in group for p in x.paras])
        i = j
    return chunks


def window_chunks(doc: dict, paras: list[list], notes: list[list]) -> list[dict]:
    """Fallback for unstructured text (short gazettes, forms): paragraph windows."""
    body = [p for p in paras if p[3] == "text"]
    groups = split_text(body, MAX_CHUNK_CHARS, TARGET_CHUNK_CHARS)
    disp = doc["title"]
    chunks = []
    for gi, g in enumerate(groups):
        text = "\n".join(p[0] for p in g).strip()
        if len(text) < 40:
            continue
        header = f"{disp} > Passage {gi + 1}/{len(groups)}"
        ps, pe = min(p[1] for p in g), max(p[2] for p in g)
        note = " ".join(t for pg, t in notes if ps <= pg <= pe)[:700]
        chunks.append({
            "chunk_id": f"{doc['doc_id']}-{len(chunks):04d}", "doc_id": doc["doc_id"], "ordinal": len(chunks),
            "act_title": doc["title"], "year": doc["year"], "doc_type": doc["doc_type"], "jurisdiction": doc["jurisdiction"],
            "applies_to": doc["applies_to"], "tier": doc["tier"], "legal_status": doc["legal_status"],
            "status_scope": doc.get("status_scope", doc["jurisdiction"]), "status_note": doc.get("status_note", "")[:200],
            "unit_type": "passage", "section_no": "", "section_nums": [], "section_label": f"Passage {gi + 1}", "heading": "",
            "part": "", "chapter": "", "order": "", "schedule": "", "page_start": ps, "page_end": pe,
            "part_index": 1, "parts_total": 1, "header": header, "text": text, "embed_text": header + "\n" + text,
            "n_chars": len(text), "amendment_notes": note, "source_urls": doc["source_urls"],
            "chunk_hash": hashlib.sha1(text.encode()).hexdigest()[:10],
        })
    return chunks


def main() -> None:
    manifest = json.loads((INTERIM_DIR / "manifest.json").read_text(encoding="utf-8"))
    out_path = PROCESSED_DIR / "chunks.jsonl"
    stats_all = {}
    n_chunks = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for doc in tqdm([d for d in manifest["docs"] if not d["duplicate_of"]], desc="chunk"):
            pj = json.loads((PARAS_DIR / f"{doc['doc_id']}.json").read_text(encoding="utf-8"))
            paras, notes = pj["paras"], pj["notes"]
            total_chars = sum(len(p[0]) for p in paras if p[3] == "text")
            units, st = build_units(paras, doc["doc_type"] == "constitution")
            structured = len(units) >= 3
            chunks = make_chunks(doc, units, notes) if structured else window_chunks(doc, paras, notes)
            covered = sum(len(u.text) for u in units)
            st.update({
                "title": doc["title"], "structured": structured, "units": len(units),
                "stubs": sum(u.stub for u in units), "chunks": len(chunks),
                "coverage": round(covered / total_chars, 3) if total_chars else 0.0,
                "chars": total_chars,
                "nums": [u.num for u in units if u.kind != "preamble"][:3] + ["..."] + [u.num for u in units if u.kind != "preamble"][-3:],
            })
            # duplicate labels inside one run => likely false header detection
            seen, dup = set(), 0
            for u in units:
                k = (u.run, u.kind, u.num, u.order, u.schedule)
                dup += k in seen
                seen.add(k)
            st["duplicate_labels"] = dup
            stats_all[doc["doc_id"]] = st
            chunks = [c for c in chunks if c["n_chars"] >= 40]       # fragments such as "[133." carry no law
            for k, c in enumerate(chunks):                           # renumber after filtering
                c["ordinal"] = k
                c["chunk_id"] = f"{doc['doc_id']}-{k:04d}"
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
            n_chunks += len(chunks)
    (INTERIM_DIR / "parse_stats.json").write_text(json.dumps(stats_all, ensure_ascii=False, indent=1), encoding="utf-8")
    structured = sum(1 for s in stats_all.values() if s["structured"])
    print(f"docs chunked: {len(stats_all)}  structured: {structured}  fallback windows: {len(stats_all) - structured}")
    print(f"chunks: {n_chunks}  -> {out_path}")


if __name__ == "__main__":
    sys.exit(main())
