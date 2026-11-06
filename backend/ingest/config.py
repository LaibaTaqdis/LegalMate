"""Paths and tunables for the corpus pipeline.

Settings come from environment variables, optionally from backend/.env (a tiny built-in loader, no dependency):

    LEGALMATE_DATASET_DIR   folder holding Federal/, Punjab/, pdfs/ and For_AI_Chatbot.csv   (required)
    LEGALMATE_CHECKLIST     path to LegalMate_Law_Checklist_v2.xlsx                           (optional, QA report only)
    LEGALMATE_DATA_DIR      where generated files go (default: backend/data, gitignored)
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal KEY=VALUE loader; real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split("  #")[0].strip().strip('"').strip("'")     # allow trailing "  # comment"
        os.environ.setdefault(k.strip(), v)


_load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = Path(os.environ.get("LEGALMATE_DATA_DIR", BACKEND_DIR / "data")).resolve()
EXTRACT_DIR = DATA_DIR / "extract"      # one JSON per PDF: raw per-page text
INTERIM_DIR = DATA_DIR / "interim"      # manifest, cleaned docs
PROCESSED_DIR = DATA_DIR / "processed"  # chunks.jsonl (what gets embedded/loaded)
REPORTS_DIR = BACKEND_DIR / "reports"

_ds = os.environ.get("LEGALMATE_DATASET_DIR")
if not _ds:
    raise SystemExit(
        "LEGALMATE_DATASET_DIR is not set. Copy backend/.env.example to backend/.env and point it at the "
        "folder that contains Federal/, Punjab/ and pdfs/ (the dataset is not stored in git).")
DATASET_DIR = Path(_ds).resolve()
CURATED_CSV = DATASET_DIR / "For_AI_Chatbot.csv"
CHECKLIST_XLSX = Path(os.environ.get("LEGALMATE_CHECKLIST", DATASET_DIR.parent / "LegalMate_Law_Checklist_v2.xlsx"))

# Chunking (characters; legal English is ~4 chars/token). bge-small max is 512 tokens.
MAX_CHUNK_CHARS = 1800
TARGET_CHUNK_CHARS = 1300
MIN_CHUNK_CHARS = 350        # smaller sections get merged with neighbours
OVERLAP_CHARS = 150          # only used when a single section must be split

for d in (EXTRACT_DIR, INTERIM_DIR, PROCESSED_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)
