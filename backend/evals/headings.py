"""Print section headings of an Act, to help write precise gold labels:  python -m evals.headings "Islamabad Rent" [filter]"""
import sys
from .labels import load_chunks, norm

act = norm(sys.argv[1]); flt = norm(sys.argv[2]) if len(sys.argv) > 2 else ""
seen = set()
for c in load_chunks():
    if act in norm(c["act_title"]) and c["unit_type"] not in ("preamble", "tail"):
        key = (c["act_title"], c["section_label"], c["heading"][:50])
        if key in seen: continue
        seen.add(key)
        line = f'{c["section_label"][:24]:24} {c["heading"][:70]}'
        if not flt or flt in norm(line): print(f'[{c["act_title"][:28]}] {line}')
