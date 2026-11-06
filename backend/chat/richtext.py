"""Convert the model's lightly-marked text into the frontend's rich-text arrays.

Model writes:   "Your landlord cannot **evict you without notice** [[1]] unless ..."
Frontend wants: ["Your landlord cannot ", {"b": "evict you without notice"}, " ", {"cite": 1}, " unless ..."]
"""
from __future__ import annotations

import re

_TOKEN = re.compile(r"(\*\*.+?\*\*|\[\[\d+\]\])")
_CITE = re.compile(r"\[\[(\d+)\]\]")


def to_segments(text: str, valid_ids: set[int] | None = None) -> list:
    out: list = []
    for part in _TOKEN.split(text or ""):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append({"b": part[2:-2]})
        elif part.startswith("[[") and part.endswith("]]"):
            n = int(part[2:-2])
            if valid_ids is None or n in valid_ids:
                out.append({"cite": n})
        else:
            out.append(part)
    # merge adjacent plain strings
    merged: list = []
    for seg in out:
        if isinstance(seg, str) and merged and isinstance(merged[-1], str):
            merged[-1] += seg
        else:
            merged.append(seg)
    return merged


def cited_ids(text: str) -> list[int]:
    return [int(x) for x in _CITE.findall(text or "")]


def strip_markup(text: str) -> str:
    """Plain text version (no bold markers, no cite markers) for chat history and titles."""
    t = re.sub(r"\s+", " ", _CITE.sub("", (text or "").replace("**", ""))).strip()
    return re.sub(r"\s+([.,;:!?])", r"\1", t)          # "position [[1]]." must not become "position ."
