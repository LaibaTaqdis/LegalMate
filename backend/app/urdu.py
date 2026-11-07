"""Urdu / Arabic-script helpers: tidy extracted text, tell how Urdu a piece of text is, and compare text the way a reader would.

Why this exists. Digital Urdu PDFs hand back old-style "presentation form" letters (ﮐﺭﺍﻳﮧ) that look the same on screen but are different
characters from normal Urdu (کرایہ), so quotes and searches would never match. OCR of Urdu uses Arabic letter shapes (ك ي ه) where Urdu
writes ک ی ہ, and documents use three different sets of digits (1 ١ ۱). All of that is folded here, in one place.

Runtime module: it must not import `ingest/`.
"""
from __future__ import annotations

import re
import unicodedata

# digits: Arabic-Indic (U+0660..) and Extended / Persian-Urdu (U+06F0..) -> ASCII
_DIGITS = {**{0x0660 + i: ord("0") + i for i in range(10)}, **{0x06F0 + i: ord("0") + i for i in range(10)}}
# letters: Arabic forms -> the Urdu letter a Pakistani reader expects
_VARIANTS = str.maketrans({"ك": "ک", "ي": "ی", "ى": "ی", "ئ": "ئ", "ه": "ہ", "ة": "ہ", "ۀ": "ہ", "ﻩ": "ہ", "ۃ": "ہ"})
_MARKS = re.compile("[​-‏‪-‮⁦-⁩ً-ٰٟۖ-ۭـ]")     # joiners, direction marks, vowel signs, tatweel
_PRIVATE = re.compile("[-�]")
_ARABIC_LETTER = re.compile("[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
_URDU_ONLY = re.compile("[ٹڈڑںھہےۓگچپژکی]")                                                         # letters Arabic does not use the Urdu way


def to_ascii_digits(text: str) -> str:
    return text.translate(_DIGITS)


def fold_presentation_forms(text: str) -> str:
    """ﮐﺭﺍﻳﮧ -> کرایہ. Only the Arabic presentation blocks are folded, so other text (m², fractions) is left exactly as written."""
    if not any("ﭐ" <= c <= "﷿" or "ﹰ" <= c <= "﻿" for c in text):
        return text
    return "".join(unicodedata.normalize("NFKC", c) if ("ﭐ" <= c <= "﷿" or "ﹰ" <= c <= "﻿") else c for c in text)


def arabic_fraction(text: str) -> float:
    """Share of the letters in `text` that are Arabic-script (Urdu, Arabic, Persian)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if _ARABIC_LETTER.match(c)) / len(letters)


def looks_urdu(text: str) -> bool:
    """True for text that is mostly Arabic script AND uses at least a few letters that Urdu writes its own way."""
    return arabic_fraction(text) > 0.3 and len(_URDU_ONLY.findall(text)) >= 3


# ordinary punctuation (English and Urdu: ، ۔ ؟), bullets, and the invisible joiners / direction marks that Urdu text legitimately contains
_NORMAL_SYMBOLS = set(".,;:!?()[]{}'\"-/\\&%$#@*+=_<>|") | set("\u2013\u2014\u2022\u00b0\u2026\u060c\u06d4\u061f") | {chr(c) for c in range(0x200B, 0x2010)}


def garbled_fraction(text: str) -> float:
    """Share of characters that are private-use / replacement characters or unusual symbols: what a broken text layer (old legacy-font
    Urdu files such as InPage, or a font with no mapping to real letters) looks like. Letters, digits and ordinary punctuation are fine."""
    body = re.sub(r"\s", "", text)
    if not body:
        return 0.0
    odd = sum(1 for c in body if not (c.isalnum() or c in _NORMAL_SYMBOLS))
    return min(1.0, odd / len(body) + (0.5 if "(cid:" in body else 0.0))


def urduize(text: str) -> str:
    """Arabic letter forms -> Urdu forms, but only for text that is really Urdu (so genuine Arabic quotations are left alone)."""
    text = fold_presentation_forms(text)
    return text.translate(_VARIANTS) if looks_urdu(text.translate(_VARIANTS)) else text


def normalize_for_match(text: str) -> str:
    """Comparison form: same letters, digits, case; no vowel signs, joiners, direction marks, punctuation or spacing differences."""
    s = unicodedata.normalize("NFKC", fold_presentation_forms(text)).translate(_VARIANTS).translate(_DIGITS).lower()
    s = _MARKS.sub("", s).replace("’", "'").replace("‘", "'")
    return re.sub(r"[^\w']+", " ", s).strip()
