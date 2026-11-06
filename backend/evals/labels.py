"""Resolve gold relevance specs to chunk indexes, and verify the labels against the corpus.

    python -m evals.labels            # prints, per question, how many chunks are relevant (0 = broken label)
"""
from __future__ import annotations

import json
import re
import sys

from ingest.config import PROCESSED_DIR

from .gold import GOLD


def norm(s: str) -> str:
    s = s.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", s)


def load_chunks() -> list[dict]:
    return [json.loads(l) for l in open(PROCESSED_DIR / "chunks.jsonl", encoding="utf-8")]


class Labeler:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.act = [norm(c["act_title"]) for c in chunks]
        self.head = [norm(c["heading"] + " " + c["section_label"]) for c in chunks]
        self.skip = [c["unit_type"] == "preamble" for c in chunks]
        self.text = [norm(c["text"]) for c in chunks]

    def match(self, spec: dict) -> set[int]:
        a, h, has = norm(spec["act"]), norm(spec["head"]), [norm(x) for x in spec["has"]]
        out = set()
        for i in range(len(self.chunks)):
            if not self.skip[i] and a in self.act[i] and (not h or h in self.head[i]) and all(x in self.text[i] for x in has):
                out.add(i)
        return out

    def relevant(self, gold_item: dict) -> set[int]:
        rel: set[int] = set()
        for spec in gold_item["rel"]:
            rel |= self.match(spec)
        return rel


def main() -> None:
    chunks = load_chunks()
    lab = Labeler(chunks)
    bad = broad = 0
    for g in GOLD:
        if g["neg"]:
            continue
        rel = lab.relevant(g)
        per_spec = [len(lab.match(s)) for s in g["rel"]]
        flag = "  <-- NO MATCH" if not rel else ("  <-- very broad" if len(rel) > 30 else "")
        bad += not rel
        broad += len(rel) > 30
        first = sorted(rel)[:2]
        shown = " | ".join(chunks[i]["header"][-60:] for i in first)
        print(f"{g['id']:4} rel={len(rel):>3} specs={per_spec}{flag}   {shown}")
    print(f"\n{sum(not g['neg'] for g in GOLD)} labelled questions; broken: {bad}; very broad: {broad}")


if __name__ == "__main__":
    sys.exit(main())
