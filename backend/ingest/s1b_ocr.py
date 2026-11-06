"""Stage 1b - OCR where the PDF text layer is missing or garbled (RapidOCR, ONNX, CPU).

Pass 1: pages with no text layer (image-only scans) are always OCR'd.
Pass 2: pages whose embedded text looks like garbage ("Rcgbtndo! Omccrt, ctc- dcctrrd") are OCR'd too and the
        better of the two versions is kept per page. "Better" = share of recognisable words minus a penalty
        for run-together words (OCR sometimes drops spaces). Only gazette-tier documents (scanned and
        re-OCR'd by the publisher) and very badly garbled pages are tried, to keep runtime reasonable.

Run after s1_extract, before s2_manifest:   python -m ingest.s1b_ocr
"""
from __future__ import annotations

import collections
import json
import re
import sys

import numpy as np
import pymupdf
from rapidocr_onnxruntime import RapidOCR

from .config import DATASET_DIR, EXTRACT_DIR


def ocr_page(engine: RapidOCR, page: "pymupdf.Page") -> str:
    pix = page.get_pixmap(dpi=220)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    result, _ = engine(img)
    if not result:
        return ""
    # group boxes into lines by vertical position
    items = sorted(((b[0][1], b[0][0], t) for b, t, _ in result), key=lambda r: (round(r[0] / 14), r[1]))
    lines, cur_y, cur = [], None, []
    for y, x, t in items:
        if cur_y is None or abs(y - cur_y) <= 14:
            cur.append(t)
            cur_y = y if cur_y is None else cur_y
        else:
            lines.append(" ".join(cur)); cur, cur_y = [t], y
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines)


def build_vocab(recs: list[dict], min_docs: int = 8) -> set[str]:
    """Words used in at least `min_docs` different documents = 'recognisable' vocabulary."""
    df: collections.Counter = collections.Counter()
    for r in recs:
        df.update(set(re.findall(r"[a-z]{4,}", " ".join(r["pages"]).lower())))
    return {w for w, n in df.items() if n >= min_docs}


def known_fraction(text: str, vocab: set[str]) -> tuple[float, int]:
    ws = re.findall(r"[a-z]{4,}", text.lower())
    return (sum(w in vocab for w in ws) / len(ws) if ws else 1.0), len(ws)


def quality(text: str, vocab: set[str]) -> float:
    kf, _ = known_fraction(text, vocab)
    ws = re.findall(r"[A-Za-z]+", text)
    long_frac = sum(len(w) > 16 for w in ws) / max(1, len(ws))      # "seniortoothermembers"
    return kf - 0.5 * long_frac


def main() -> None:
    engine = RapidOCR()
    files = sorted(EXTRACT_DIR.glob("*.json"))
    recs = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    vocab = build_vocab(recs)
    n_blank = n_garbled_tried = n_replaced = 0
    for f, rec in zip(files, recs):
        is_gazette = "/gazettes_and_amendments/" in rec["paths"][0]
        todo_blank = [i for i in rec["needs_ocr_pages"] if i not in rec.get("ocr_pages", [])]
        todo_garbled = []
        for i, text in enumerate(rec["pages"]):
            if i in rec["needs_ocr_pages"] or i in rec.get("ocr_checked", []):
                continue
            kf, n = known_fraction(text, vocab)
            if n >= 40 and (kf < 0.50 or (is_gazette and kf < 0.80)):
                todo_garbled.append(i)
        if not todo_blank and not todo_garbled:
            continue
        doc = pymupdf.open(DATASET_DIR / rec["paths"][0])
        rec.setdefault("ocr_pages", [])
        rec.setdefault("ocr_checked", [])
        rec.setdefault("ocr_replaced", [])
        for i in todo_blank:
            rec["pages"][i] = ocr_page(engine, doc[i])
            rec["ocr_pages"].append(i)
            n_blank += 1
        for i in todo_garbled:
            o = ocr_page(engine, doc[i])
            n_garbled_tried += 1
            rec["ocr_checked"].append(i)
            if quality(o, vocab) > quality(rec["pages"][i], vocab) + 0.05:
                rec["pages"][i] = o
                rec["ocr_replaced"].append(i)
                n_replaced += 1
        f.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        print(f"{rec['paths'][0][-62:]}: blank={len(todo_blank)} garbled_tried={len(todo_garbled)} replaced={len(rec['ocr_replaced'])}", flush=True)
    print(f"image-only pages OCRed: {n_blank} | garbled pages re-OCRed: {n_garbled_tried} (better version kept on {n_replaced})")


if __name__ == "__main__":
    sys.exit(main())
