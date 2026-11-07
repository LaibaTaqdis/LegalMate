"""Loads the OCR readers once so their models are downloaded and cached BEFORE the first user upload (the first run of the Urdu reader
downloads its model, about 10 MB, from the RapidOCR model repository). Run it at deploy time, or after changing OCR_LANGS / OCR_URDU_MODEL:

    python -m app.ocr_warmup
"""
from __future__ import annotations

import sys
import time

from chat.settings import load_env

from .config import load_doc_settings


def main() -> int:
    from PIL import Image, ImageDraw

    from . import extract as ex

    load_env()
    cfg = load_doc_settings()
    img = Image.new("RGB", (600, 120), "white")
    ImageDraw.Draw(img).text((20, 40), "LegalMate OCR warm-up 123", fill="black")
    t0 = time.time()
    ex.ocr_image(img, cfg)
    print(f"English reader ready ({time.time() - t0:.1f}s)")
    if "ur" in cfg.ocr_langs:
        t0 = time.time()
        if ex.urdu_available(cfg):
            print(f"Urdu reader ready ({time.time() - t0:.1f}s, model {cfg.ocr_urdu_model})")
        else:
            print(f"Urdu reader NOT available: {ex._urdu_error}")
            return 1
    else:
        print("Urdu reader switched off (OCR_LANGS has no 'ur').")
    return 0


if __name__ == "__main__":
    sys.exit(main())
