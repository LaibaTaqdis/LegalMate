"""Stage 1 - extract raw per-page text from every PDF in the dataset.

Output: data/extract/<doc_id>.json   {doc_id, paths[], n_pages, pages[str], needs_ocr_pages[int]}
doc_id = first 12 hex chars of the file's SHA-256, so byte-identical files collapse to one id.
Run:  python -m ingest.s1_extract
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pymupdf
from tqdm import tqdm

from .config import DATASET_DIR, EXTRACT_DIR

SOURCES = ("Federal", "Punjab", "pdfs")


def list_pdfs() -> list[str]:
    out = []
    for sub in SOURCES:
        for dp, _, fs in os.walk(DATASET_DIR / sub):
            out += [os.path.join(dp, f) for f in fs if f.lower().endswith(".pdf")]
    return sorted(out)


def extract_one(path: str) -> dict:
    data = open(path, "rb").read()
    doc_id = hashlib.sha256(data).hexdigest()[:12]
    rel = os.path.relpath(path, DATASET_DIR).replace("\\", "/")
    out_file = EXTRACT_DIR / f"{doc_id}.json"
    pages, needs_ocr = [], []
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
        for i, page in enumerate(doc):
            text = page.get_text("text")
            pages.append(text)
            if len(text.strip()) < 30 and (page.get_images() or page.get_drawings()):
                needs_ocr.append(i)
        n_pages = doc.page_count
        err = None
    except Exception as e:  # corrupted / encrypted
        n_pages, err = 0, str(e)[:200]
    rec = {"doc_id": doc_id, "paths": [rel], "n_pages": n_pages, "pages": pages,
           "needs_ocr_pages": needs_ocr, "error": err, "size_bytes": len(data)}
    if out_file.exists():  # byte-identical duplicate: merge paths
        prev = json.loads(out_file.read_text(encoding="utf-8"))
        rec["paths"] = sorted(set(prev["paths"] + rec["paths"]))
    out_file.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return {"doc_id": doc_id, "path": rel, "n_pages": n_pages, "needs_ocr": len(needs_ocr), "error": err}


def main() -> None:
    for f in EXTRACT_DIR.glob("*.json"):
        f.unlink()
    paths = list_pdfs()
    print(f"{len(paths)} PDFs under {DATASET_DIR}")
    # Sequential merge of paths for identical bytes requires ordered writes; extraction itself is
    # CPU-bound and fast, so a small pool + a second pass for duplicates is simplest.
    with ProcessPoolExecutor(max_workers=max(2, (os.cpu_count() or 4) // 2)) as ex:
        results = list(tqdm(ex.map(extract_one, paths, chunksize=4), total=len(paths)))
    # fix up duplicate-path merging (race-free): rebuild paths lists from results
    by_id: dict[str, list[str]] = {}
    for r in results:
        by_id.setdefault(r["doc_id"], []).append(r["path"])
    for doc_id, ps in by_id.items():
        f = EXTRACT_DIR / f"{doc_id}.json"
        rec = json.loads(f.read_text(encoding="utf-8"))
        rec["paths"] = sorted(set(ps))
        f.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    dup = {k: v for k, v in by_id.items() if len(v) > 1}
    print(f"unique files: {len(by_id)}  byte-identical duplicates: {len(dup)}")
    print(f"errors: {sum(1 for r in results if r['error'])}  files needing OCR: {sum(1 for r in results if r['needs_ocr'])}")


if __name__ == "__main__":
    sys.exit(main())
