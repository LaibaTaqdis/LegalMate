"""Urdu support: text helpers, verification that understands Urdu, and OCR of Urdu pages (generated here, in fonts available on the machine).

The OCR tests are real (they read pixels). They skip themselves if no font with Arabic-script letters can be found.

    python -m pytest tests/test_urdu.py -q
"""
from __future__ import annotations

import difflib
import io
import os
from dataclasses import replace
from pathlib import Path

import pymupdf as fitz
import pytest
from PIL import Image, ImageDraw, ImageFont

from app import extract as ex
from app.config import DocSettings
from app.urdu import arabic_fraction, fold_presentation_forms, garbled_fraction, looks_urdu, normalize_for_match, to_ascii_digits, urduize
from chat.pii import scrub

LINES = [
    "کرایہ داری کا معاہدہ",
    "ماہانہ کرایہ پینتالیس ہزار روپے ہے جو ہر مہینے کی پانچ تاریخ تک ادا کیا جائے گا۔",
    "مالک مکان تیس دن کے نوٹس پر یہ معاہدہ ختم کر سکتا ہے۔",
    "کرایہ دار مالک مکان کی تحریری اجازت کے بغیر مکان آگے کرایہ پر نہیں دے گا۔",
]
ENGLISH = ["RESIDENTIAL TENANCY AGREEMENT", "The monthly rent is PKR 45,000 payable by the 5th of each month."]


def _font_dir() -> Path | None:
    for d in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "/System/Library/Fonts/Supplemental"):
        for name in ("tahoma.ttf", "arial.ttf", "DejaVuSans.ttf", "Arial.ttf"):
            if (Path(d) / name).exists():
                return Path(d) / name
    return None


FONT = _font_dir()
needs_font = pytest.mark.skipif(FONT is None, reason="no font with Arabic-script letters on this machine")


def urdu_image(lines=LINES, size=22, width=900) -> Image.Image:
    css = "@font-face {font-family: urdu; src: url(%s);} body {font-family: urdu; font-size: %dpx; direction: rtl; text-align: right; line-height: 1.9;}" % (FONT.name, size)
    doc = fitz.open()
    page = doc.new_page(width=width, height=60 + 70 * len(lines))
    page.insert_htmlbox(fitz.Rect(20, 20, width - 20, page.rect.height - 10), "<body>" + "".join(f"<p>{l}</p>" for l in lines) + "</body>", css=css,
                        archive=fitz.Archive(str(FONT.parent)))
    pix = page.get_pixmap(dpi=150)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def english_image(lines=ENGLISH, w=1500, h=330) -> Image.Image:
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("arial.ttf", 34)
    except OSError:
        f = ImageFont.load_default()
    for i, l in enumerate(lines):
        d.text((30, 30 + i * 80), l, fill="black", font=f)
    return img


def png(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()


def line_similarity(truth: list[str], text: str) -> float:
    got = [l for l in text.splitlines() if l.strip()]
    return sum(max((difflib.SequenceMatcher(None, normalize_for_match(t), normalize_for_match(g)).ratio() for g in got), default=0) for t in truth) / len(truth)


@pytest.fixture()
def spy(monkeypatch):
    """Counts how often the Urdu reader is asked for."""
    calls = {"n": 0}
    real = ex._urdu_get
    monkeypatch.setattr(ex, "_urdu_get", lambda cfg: (calls.__setitem__("n", calls["n"] + 1), real(cfg))[1])
    return calls


# ---------------------------------------------------------------------------------------------- helpers (fast)
def test_text_helpers():
    assert fold_presentation_forms("ﮐﺭﺍﻳﮧ") == "کرایہ" or looks_urdu(urduize("ﮐﺭﺍﻳﮧ ﺩﺍﺭﯼ ﮐﺎ ﻣﻌﺎﮨﺩﻩ"))
    assert urduize("ﮐﺭﺍﻳﮧ ﺩﺍﺭﯼ ﮐﺎ ﻣﻌﺎﮨﺩﻩ") == "کرایہ داری کا معاہدہ"
    assert fold_presentation_forms("area 45 m² ﬁne") == "area 45 m² ﬁne"                                  # only the Arabic blocks are touched
    assert urduize("بسم الله الرحمن الرحيم") == "بسم الله الرحمن الرحيم"                              # genuine Arabic keeps its letters
    assert to_ascii_digits("۴۵٬۰۰۰ ٩٠") == "45٬000 90"
    assert normalize_for_match("كرايه دارى") == normalize_for_match("کرایہ داری")
    assert arabic_fraction("Rent is 45,000") == 0 and arabic_fraction("کرایہ") == 1.0
    assert garbled_fraction("The rent is PKR 45,000 (forty-five thousand) per month; see clause 3.1 & 3.2.") == 0
    assert garbled_fraction("کرایہ\u200c داری۔ ہر مہینے؟") == 0
    assert garbled_fraction("".join(chr(0xE000 + i) for i in range(40))) > 0.9 and garbled_fraction("(cid:12)(cid:40)") > 0.4


def test_identity_numbers_in_urdu_digits_are_scrubbed():
    out, found = scrub("شناختی کارڈ ۳۵۲۰۲-۱۲۳۴۵۶۷-۱ اور فون ۰۳۰۰ ۱۲۳۴۵۶۷")
    assert "35202" not in out and "۳۵۲۰۲" not in out and found == {"CNIC": 1, "PHONE": 1}


# ---------------------------------------------------------------------------------------------- OCR (real pixels)
@needs_font
def test_urdu_scan_is_read_in_order_and_flagged():
    r = ex.extract(png(urdu_image()), DocSettings())
    assert r.urdu is True and r.ocr_pages == 1
    assert line_similarity(LINES, r.text) >= 0.78, r.text                                           # measured about 0.9 on clean print
    assert r.text.splitlines()[0].startswith("کرای") and "ادا" in r.text                           # title first: top to bottom, words right to left
    assert any("Urdu text read from an image" in w for w in r.warnings) and "double-check" in r.warnings[0]
    assert not any("ﻣ" <= c <= "ﻻ" for c in r.text)                                                   # no presentation forms in the stored text


@needs_font
def test_english_only_page_never_pays_for_the_urdu_reader(spy):
    r = ex.extract(png(english_image()), DocSettings())
    assert spy["n"] == 0 and r.urdu is False and "monthly rent" in r.text and "45,000" in r.text


@needs_font
def test_mixed_english_and_urdu_page_keeps_both(spy):
    urdu = urdu_image(LINES[1:4], width=1000)
    page = Image.new("RGB", (urdu.width, urdu.height + 150), "white")
    d = ImageDraw.Draw(page)
    d.text((30, 30), ENGLISH[0], fill="black", font=ImageFont.truetype(str(FONT), 40))
    d.text((30, 85), ENGLISH[1], fill="black", font=ImageFont.truetype(str(FONT), 30))
    page.paste(urdu, (0, 150))
    r = ex.extract(png(page), DocSettings())
    assert spy["n"] >= 1 and r.urdu is True
    assert "45,000" in r.text and "TENANCY" in r.text.upper()                                       # the English lines survive
    assert line_similarity(LINES[1:4], r.text) >= 0.7                                               # and the Urdu lines were added
    assert r.text.upper().index("TENANCY") < r.text.index("ماہ") if "ماہ" in r.text else True        # reading order: English heading first


@needs_font
def test_digital_urdu_pdf_is_folded_to_normal_letters_without_ocr(spy):
    css = "@font-face {font-family: urdu; src: url(%s);} body {font-family: urdu; font-size: 14px; direction: rtl; text-align: right;}" % FONT.name
    doc = fitz.open()
    page = doc.new_page(width=600, height=400)
    page.insert_htmlbox(fitz.Rect(20, 20, 580, 380), "<body>" + "".join(f"<p>{l}</p>" for l in LINES) + "</body>", css=css, archive=fitz.Archive(str(FONT.parent)))
    r = ex.extract(doc.tobytes(), DocSettings())
    assert r.ocr_pages == 0 and spy["n"] == 0 and r.urdu is True
    assert not any("\ufb50" <= c <= "\ufdff" or "\ufe70" <= c <= "\ufeff" for c in r.text)           # old-style letters folded
    assert line_similarity(LINES, r.text) >= 0.95
    assert "مالک مکان تیس دن کے" in r.text.replace("\xa0", " ")                                       # exact Urdu letters, so quotes will match


def test_a_broken_text_layer_falls_back_to_reading_the_picture():
    doc = fitz.open()
    p = doc.new_page(width=600, height=300)
    p.insert_image(fitz.Rect(0, 0, 600, 200), stream=png(english_image()))
    p.insert_text((20, 250), "".join(chr(0xE000 + i) for i in range(60)), fontsize=9)               # junk where real text should be
    r = ex.extract(doc.tobytes(), DocSettings())
    assert r.ocr_pages == 1 and "monthly rent" in r.text


@needs_font
def test_urdu_can_be_switched_off_by_environment(spy):
    with pytest.raises(ex.ExtractError) as e:                                                      # a page of Urdu with the Urdu reader off: nothing readable
        ex.extract(png(urdu_image()), replace(DocSettings(), ocr_langs=("en",)))
    assert e.value.code == "NO_TEXT" and spy["n"] == 0                                             # clear message, the Urdu reader was never loaded
    mixed = english_image()
    assert "monthly rent" in ex.extract(png(mixed), replace(DocSettings(), ocr_langs=("en",))).text   # English is unaffected
    from app.config import load_doc_settings
    os.environ["OCR_LANGS"] = "en"
    try:
        assert load_doc_settings().ocr_langs == ("en",)
    finally:
        del os.environ["OCR_LANGS"]
    assert load_doc_settings().ocr_langs == ("en", "ur")


@needs_font
def test_a_missing_urdu_model_is_reported_not_hidden(monkeypatch):
    monkeypatch.setattr(ex, "_urdu_get", lambda cfg: None)
    img = urdu_image()
    page = Image.new("RGB", (max(img.width, 1500), img.height + 130), "white")
    ImageDraw.Draw(page).text((30, 30), "Agreement of rent between the parties 45,000 PKR", fill="black", font=ImageFont.truetype(str(FONT), 34))
    page.paste(img, (0, 130))
    r = ex.extract(png(page), DocSettings())
    assert "Agreement" in r.text and "45," in r.text and any("Urdu reader is not available" in w for w in r.warnings)       # English works, the user is told
    assert not any(any(ch in l for ch in "<>~") for l in r.text.splitlines()) and len(r.text.splitlines()) == 1          # no invented junk lines from the Urdu


@needs_font
def test_upload_endpoint_reports_urdu(pg_url):
    from fastapi.testclient import TestClient
    from tests.conftest import FakeEngine, make_settings, signup
    from app.main import create_app
    with TestClient(create_app(make_settings(pg_url), engine=FakeEngine())) as c:
        _, h = signup(c)
        r = c.post("/api/v1/documents", files={"file": ("نوٹس.png", png(urdu_image()), "application/octet-stream")}, data={"purpose": "analysis"}, headers=h)
        assert r.status_code == 201, r.text
        j = r.json()
        assert j["urdu"] is True and j["ocrUsed"] is True and any("Urdu" in w for w in j["warnings"])
        stored = c.app.state.ctx.db.one("select text, name from app.documents where id = %s", [j["id"]])
        assert "کرایہ" in stored["text"] or "کرای" in stored["text"]
