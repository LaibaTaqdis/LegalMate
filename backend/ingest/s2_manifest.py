"""Stage 2 - clean every document and build the manifest (one record per PDF).

* cleans text -> data/interim/paras/<doc_id>.json
* detects the REAL title/year/type from the content (filenames are unreliable)
* jurisdiction, source tier, legal status (merged with the curated CSV)
* near-duplicate detection (word-shingle Jaccard) and amendment/repeal linking
Output: data/interim/manifest.json
Run:  python -m ingest.s2_manifest
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import sys
import zlib
from collections import Counter, defaultdict

from tqdm import tqdm

from .config import CURATED_CSV, EXTRACT_DIR, INTERIM_DIR
from .textclean import build_paragraphs, clean_pages

PARAS_DIR = INTERIM_DIR / "paras"
PARAS_DIR.mkdir(parents=True, exist_ok=True)

TYPE_WORDS = r"(?:ACT|ORDINANCE|ORDER|CODE|RULES|CONSTITUTION|REGULATIONS)"
SMALL = {"of", "and", "the", "in", "for", "to", "on", "by", "with", "or", "a", "an", "at", "from"}
KEEP_UPPER = {"ICT", "AJK", "NADRA", "PECA", "PPC", "CPC", "HEC", "NAB", "FIA", "SECP", "FBR", "WAPDA", "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII"}
BAD_START = re.compile(r"^(an?\s+act|whereas|it\s+is|this\s+act|no\.|the\s+following|extraordinary|acts,|part\s)", re.I)


# ---------------------------------------------------------------- title / meta detection

def smart_title(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip(" ,.-—")
    if uppercase_ratio(s) < 0.6 and not s.islower():
        return s
    out = []
    for i, w in enumerate(s.split(" ")):
        core = w.strip("(),")
        if core.upper() in KEEP_UPPER and core.isupper():
            out.append(w)
        elif i > 0 and core.lower() in SMALL:
            out.append(w.lower())
        else:
            out.append(re.sub(r"[A-Za-z][A-Za-z’']*", lambda m: m.group(0)[:1].upper() + m.group(0)[1:].lower(), w))
    return " ".join(out)


def first_lines(pages_clean, n_lines=90) -> list[str]:
    ls = []
    for _, lines in pages_clean[:3]:
        for l in lines:
            l = re.sub(r"^\d{1,2}(?=[A-Z])", "", l.strip())      # footnote digit glued to a title: "1THE PUNJAB..."
            if l:
                ls.append(l)
    return ls[:n_lines]


_TITLE = re.compile(
    r"^(?:THE\s+)?(?P<name>[A-Z(][A-Za-z0-9’'()&,./\- ]{3,150}?\b" + TYPE_WORDS + r")\b(?:\s*\([^)]{0,40}\))?[\s,.]*(?P<year>(?:19|20)\d{2})?\b", re.I)


def uppercase_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in letters) / len(letters) if letters else 0


def _balanced(s: str) -> bool:
    return s.count("(") == s.count(")")


def content_title(pages_clean) -> tuple[str | None, int | None]:
    """Best title-looking window in the first lines (may be wrong: the caller cross-checks)."""
    lines = first_lines(pages_clean)
    best = None
    for i in range(len(lines)):
        for w in (1, 2, 3):
            cand = " ".join(lines[i:i + w]).strip()
            if not (8 <= len(cand) <= 175) or BAD_START.match(cand) or "assent" in cand.lower():
                continue
            if not cand[0].isupper() or not _balanced(cand):
                continue
            m = _TITLE.match(cand)
            if not m:
                continue
            tail = cand[m.end("name"):]
            if len(tail) > 60 and not m.group("year"):
                continue
            if uppercase_ratio(cand) < 0.6 and not m.group("year"):
                continue
            year = int(m.group("year")) if m.group("year") else None
            score = (2 if year else 0) + (1 if uppercase_ratio(cand) > 0.7 else 0) - 0.01 * i
            title = cand[: m.end("year")] if year else cand[: m.end("name")]
            if best is None or score > best[0]:
                best = (score, title, year)
            break
    if not best:
        return None, None
    year = best[2]
    if year is None:
        for l in lines[:40]:
            m = re.search(r"\bof\s+((?:18|19|20)\d{2})\b", l)
            if m:
                year = int(m.group(1)); break
    return best[1], year


def filename_title(filename: str) -> str:
    t = re.sub(r"(\.pdf)+(\s*\(\d+\))?$", "", filename, flags=re.I).strip()
    if " " not in t and t.count("-") >= 3 or t.count("_") >= 2:          # slug style
        t = re.sub(r"^\d+[-_]", "", t)
        t = re.sub(r"[-_](docx\d*[-_])?pdf$", "", t, flags=re.I)
        t = re.sub(r"[-_](?:[ivxl]+[-_]of[-_]\d{4})$", "", t, flags=re.I)
        t = re.sub(r"[-_.]+", " ", t)
    return re.sub(r"\s+", " ", t.replace("_", " ")).strip()


def plausible(c: str | None, year: int | None) -> bool:
    if not (c and year and uppercase_ratio(c) >= 0.7 and len(c.split()) <= 16 and re.match(r"(THE\s+)?[A-Z]", c)):
        return False
    return bool(re.search(r"(?:18|19|20)\d{2}", c)) and not re.search(r"\bNO\b\.?|\bAN ACT\b|^ACR\b", c, re.I)


def tidy_title(t: str) -> str:
    t = smart_title(t)
    t = re.sub(r"^The\s+", "", t)
    t = re.sub(r"\s*,?\s*(\(?(?:18|19|20)\d{2}\)?)$", lambda m: ", " + m.group(1).strip("()"), t)
    return t.strip()


def choose_title(pages_clean, filename: str) -> tuple[str, int | None, str]:
    c, cy = content_title(pages_clean)
    f = filename_title(filename)
    fy = re.search(r"((?:18|19|20)\d{2})", f)
    fy = int(fy.group(1)) if fy else None
    sim = difflib.SequenceMatcher(None, norm_key(c or ""), norm_key(f)).ratio() if c else 0.0
    if c and sim >= 0.5:
        return tidy_title(f if len(f) >= 8 else c), cy or fy, "agree"
    if c and plausible(c, cy):
        return tidy_title(c), cy, "content-conflict"        # filename disagrees with a believable title
    return tidy_title(f), fy or cy, "filename"


def norm_key(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\b(the|of|and)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def base_name(title: str) -> str:
    """Title stripped of '(... Amendment)', '(Repeal)', year and type word -> comparable base name."""
    t = re.sub(r"\([^)]*(amend|repeal)[^)]*\)", " ", title, flags=re.I)
    t = re.sub(r"\b(second|third)?\s*amendment\b", " ", t, flags=re.I)
    t = re.sub(r",?\s*\(?(?:18|19|20)\d{2}\)?", " ", t)
    t = re.sub(r"\b(act|ordinance|order|code|rules|regulations)\b", " ", t, flags=re.I)
    return norm_key(t)


def classify(title: str) -> tuple[str, bool, bool]:
    up = title.upper()
    is_repeal = "REPEAL)" in up and "AMEND" not in up
    is_amend = bool(re.search(r"AMEND(MENT|ED)?\)|\(AMEND|VALIDATION\)|REPEAL\)", up))
    if "CONSTITUTION" in up and "AMENDMENT" not in up:
        t = "constitution"
    else:
        kinds = [(m.start(), m.group(1)) for m in re.finditer(r"\b(ACT|ORDINANCE|ORDER|CODE|RULES|REGULATIONS)\b", up)]
        t = kinds[-1][1].lower() if kinds else "act"
    return t, is_amend, is_repeal


def jurisdiction(path: str, title: str) -> str:
    up = title.upper()
    if "ISLAMABAD" in up or re.search(r"\bICT\b", up):
        return "ICT"
    if path.startswith("Punjab/") or "PUNJAB" in up:
        return "Punjab"
    return "Federal"


def tier_of(path: str) -> str:
    if "/gazettes_and_amendments/" in path:
        return "gazette"
    if path.startswith("pdfs/"):
        return "curated"
    return "publisher"


# ---------------------------------------------------------------- near-duplicate detection

def shingles(text: str, k: int = 6) -> set[int]:
    w = re.findall(r"[a-z0-9]+", text.lower())
    out = set()
    for i in range(len(w) - k + 1):
        h = zlib.crc32(" ".join(w[i:i + k]).encode())
        if h % 4 == 0:               # sample 1/4 of shingles
            out.add(h)
    return out


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------- main

def load_curated() -> dict[str, dict]:
    out = {}
    if not CURATED_CSV.exists():
        return out
    csv.field_size_limit(10**9)
    for r in csv.DictReader(open(CURATED_CSV, encoding="utf-8-sig", newline="")):
        out[r["original_pdf_filename"].strip().lower()] = {
            "legal_status": r["legal_status"].strip().lower(), "legal_status_scope": r["legal_status_scope"],
            "citation": r["citation"], "source_urls": json.loads(r["source_urls_json"] or "[]"),
        }
    return out


def main() -> None:
    curated = load_curated()
    recs = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(EXTRACT_DIR.glob("*.json"))]
    docs, sh = [], {}
    for r in tqdm(recs, desc="clean+meta"):
        body, notes, stats = clean_pages(r["pages"])
        paras = build_paragraphs(body)
        path = r["paths"][0]
        fname = path.split("/")[-1]
        title, year, tsrc = choose_title(body, fname)
        dtype, is_amend, is_repeal = classify(title)
        n_chars = sum(len(p.text) for p in paras)
        cur = curated.get(fname.lower()) or curated.get(re.sub(r"\.pdf$", "", fname, flags=re.I).lower())
        # curated CSV keys are PDF names without the extension in a few rows
        if cur is None:
            for k, v in curated.items():
                if k.replace(".pdf", "") == re.sub(r"\.pdf$", "", fname, flags=re.I).lower():
                    cur = v
                    break
        fname_norm = norm_key(re.sub(r"(\.pdf)+(\s*\(\d+\))?$", "", fname, flags=re.I))
        sim = difflib.SequenceMatcher(None, norm_key(title), fname_norm).ratio()
        docs.append({
            "doc_id": r["doc_id"], "paths": r["paths"], "filename": fname, "title": title, "title_source": tsrc,
            "year": year, "doc_type": dtype, "is_amendment": is_amend, "is_repeal": is_repeal,
            "jurisdiction": jurisdiction(path, title), "tier": tier_of(path),
            "n_pages": r["n_pages"], "n_chars": n_chars, "needs_ocr_pages": r["needs_ocr_pages"],
            "legal_status": (cur or {}).get("legal_status", "unverified"),
            "status_note": (cur or {}).get("legal_status_scope", ""),
            "source_urls": (cur or {}).get("source_urls", []), "citation_csv": (cur or {}).get("citation", ""),
            "title_matches_filename": round(sim, 2),
            "duplicate_of": None, "applies_to": [], "amends": [], "amended_by": [], "repealed_by": None,
            "clean_stats": dict(stats),
        })
        (PARAS_DIR / f"{r['doc_id']}.json").write_text(json.dumps({
            "paras": [[p.text, p.page_start, p.page_end, p.kind] for p in paras],
            "notes": notes}, ensure_ascii=False), encoding="utf-8")
        sh[r["doc_id"]] = shingles(" ".join(p.text for p in paras))

    by_id = {d["doc_id"]: d for d in docs}
    for d in docs:
        d["applies_to"] = [d["jurisdiction"]]
        # Where does the legal status apply? The curated CSV says e.g. "Punjab; historical rights ..." for the two
        # repealed records: the repeal is Punjab-only even though the text is the Federal Act.
        first = d["status_note"].split(";")[0].strip()
        d["status_scope"] = first if first in ("Punjab", "Federal", "ICT") else d["jurisdiction"]

    # ---- near-duplicates: compare docs whose years match (or are both unknown)
    buckets = defaultdict(list)
    for d in docs:
        buckets[d["year"]].append(d)
    parent = {d["doc_id"]: d["doc_id"] for d in docs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    pair_log = []
    for yr, ds in buckets.items():
        for i in range(len(ds)):
            for j in range(i + 1, len(ds)):
                a, b = ds[i], ds[j]
                s = jaccard(sh[a["doc_id"]], sh[b["doc_id"]])
                if s < 0.6:
                    continue
                same_j = a["jurisdiction"] == b["jurisdiction"]
                dup = s >= 0.97 or (same_j and s >= 0.80)
                pair_log.append({"a": a["doc_id"], "b": b["doc_id"], "jaccard": round(s, 3),
                                 "same_jurisdiction": same_j, "action": "duplicate" if dup else "variant"})
                if dup:
                    parent[find(a["doc_id"])] = find(b["doc_id"])
    clusters = defaultdict(list)
    for d in docs:
        clusters[find(d["doc_id"])].append(d)
    rank = {"curated": 0, "gazette": 1, "publisher": 2}
    for members in clusters.values():
        if len(members) == 1:
            continue
        members.sort(key=lambda d: (rank[d["tier"]], -d["n_chars"]))
        canon = members[0]
        for m in members[1:]:
            m["duplicate_of"] = canon["doc_id"]
            m["kept_path"] = canon["paths"][0]
            canon["applies_to"] = sorted(set(canon["applies_to"]) | set(m["applies_to"]))
            canon["paths"] = sorted(set(canon["paths"]) | set(m["paths"]))

    # ---- amendment / repeal linking (only to canonical, non-amendment base laws)
    bases = [d for d in docs if not d["is_amendment"] and not d["duplicate_of"]]
    unresolved = []
    for d in docs:
        if not d["is_amendment"] or d["duplicate_of"]:
            continue
        bn = base_name(d["title"])
        best, best_s = None, 0.0
        hm = re.match(r"(.*?)\s*\([^)]*(?:amend|repeal)", d["title"], re.I)
        tw = re.findall(r"\b(act|ordinance|order|code)\b", hm.group(1).lower()) if hm else []
        head_type = tw[-1] if tw else None          # type word written *before* "(... Amendment)"
        for b in bases:
            bb = base_name(b["title"])
            if not bn or not bb:
                continue
            s = difflib.SequenceMatcher(None, bn, bb).ratio()
            if (bn.startswith(bb) or bb.startswith(bn)) and min(len(bn), len(bb)) >= 8:
                s = max(s, 0.9)
            if b["jurisdiction"] == d["jurisdiction"]:
                s += 0.03
            # "Police Order (Second Amendment) Act" amends an Order, not the Police Act; Rules are rarely the target;
            # a law cannot amend a later law.
            if head_type and b["doc_type"] != head_type:
                s -= 0.15
            if b["doc_type"] in ("rules", "regulations"):
                s -= 0.10
            if b["year"] and d["year"] and b["year"] > d["year"]:
                s -= 0.25
            if s > best_s:
                best, best_s = b, s
        d["link_score"] = round(best_s, 2)
        if best and best_s >= 0.86:
            d["amends"] = [best["doc_id"]]
            best["amended_by"].append(d["doc_id"])
            if d["is_repeal"]:
                best["legal_status"] = "repealed"
                best["repealed_by"] = d["doc_id"]
                best["status_scope"] = d["jurisdiction"]
                best["status_note"] = f"Repealed by {d['title']} (per database text; verify)"
        else:
            unresolved.append(d["doc_id"])

    manifest = {"docs": docs, "pair_log": pair_log, "unresolved_amendments": unresolved}
    (INTERIM_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    n_dup = sum(1 for d in docs if d["duplicate_of"])
    print(f"docs: {len(docs)}  duplicates folded: {n_dup}  unique laws: {len(docs) - n_dup}")
    print("title source:", Counter(d["title_source"] for d in docs))
    print("tiers:", Counter(d["tier"] for d in docs), " jurisdictions:", Counter(d["jurisdiction"] for d in docs))
    print("types:", Counter(d["doc_type"] for d in docs))
    print(f"amendments: {sum(d['is_amendment'] for d in docs)} (unresolved: {len(unresolved)})")
    print("repealed:", [d["title"] for d in docs if d["legal_status"] == "repealed"])
    print("filename/title mismatches (<0.5):", sum(1 for d in docs if d["title_matches_filename"] < 0.5))


if __name__ == "__main__":
    sys.exit(main())
