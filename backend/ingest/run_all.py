"""Run the whole corpus pipeline: PDFs -> chunks.jsonl + QA report.

    python -m ingest.run_all            # everything
    python -m ingest.run_all --from s2  # re-run from a later stage (extraction/OCR are slow)
"""
from __future__ import annotations

import argparse
import time

from . import s1_extract, s1b_ocr, s2_manifest, s3_chunk, s4_qa

STAGES = [("s1", s1_extract), ("s1b", s1b_ocr), ("s2", s2_manifest), ("s3", s3_chunk), ("s4", s4_qa)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="s1", choices=[n for n, _ in STAGES])
    start = ap.parse_args().start
    go = False
    for name, mod in STAGES:
        go = go or name == start
        if go:
            t = time.time()
            print(f"\n=== {name} ({mod.__name__}) ===")
            mod.main()
            print(f"[{name}] {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()
