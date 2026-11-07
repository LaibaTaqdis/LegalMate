"""Which Pakistani laws deal with which kind of document and clause, for the "Related laws" box of a document analysis.

Why a reviewed table and not a search. Searching the law library from a loosely worded clause is not reliable enough to show people
(measured: about 1 question in 9 misses the right section even with good queries, and a wrong law presented next to someone's contract
is worse than none). So the model only CLASSIFIES each clause into a fixed list of topics; a person reviewed which Act and section
governs each topic; and code then looks up the REAL text of that section in the law library and shows it, with the province it applies in
and any warning (amended later, repealed). Nothing in a reference is written by the model.

Each entry was checked against the stored law text (`python -m app.law_refs --check` resolves every entry and prints the heading it found;
a unit test fails if an entry stops resolving). Where no section governs a topic (for example the Punjab Rented Premises Act has no rent
increase or security deposit section) the topic has NO entry for that province: showing nothing is correct.

The shown texts describe what the law says. They never say whether the user's document follows it.

Runtime module: it must not import `ingest/`.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

log = logging.getLogger("legalmate.lawrefs")

ALL = "ALL"      # applies wherever the document is


@dataclass(frozen=True)
class Ref:
    act: str                     # exact title as stored in the law library
    sections: tuple[str, ...]    # section / article / rule numbers to show (each resolved separately)
    applies: tuple[str, ...] = (ALL,)    # "ALL", or the jurisdictions ("Punjab", "ICT") this reference is for


C = "Contract act, 1872"
TPA = "Transfer of Property Act, 1882"
REG = "Registration Act, 1908"
STAMP = "Stamp Act, 1899"
SRA = "Specific Relief Act, 1877"
PART = "Partnership Act, 1932"
PWA = "Payment of Wages Act, 1936"
QSO = "Qanun-e-Shahadat Order, 1984"
ARB = "Arbitration Act, 1940"
PRPA = "Punjab Rented Premises Act, 2009"
RRO = "Islamabad Rent Restriction Ordinance, 2001"
SO = "Industrial and Commercial Employment (Standing Orders) Ordinance, 1968"
PLC = "Punjab Labour Code, 2026"
PIL_P = "Punjab Prohibition of Interest on Private Loans Act, 2022"
PIL_I = "Islamabad Capital Territory Prohibition of Interest on Private Loans Act, 2023"
PREEMPT = "Punjab Pre Emption Act, 1991 Doc"
PMW = "Punjab Minimum Wages Act, 2019"
PDW = "Punjab Domestic Workers Act, 2019"

P, I = ("Punjab",), ("ICT",)

# topic key -> (label shown to the user, hint for the model, references)
TOPICS: dict[str, tuple[str, str, tuple[Ref, ...]]] = {
    "contract_basics":      ("Valid agreements", "what makes an agreement a valid, enforceable contract (consent, lawful purpose)", (Ref(C, ("10", "23")),)),
    "penalty_clause":       ("Penalty or fixed damages", "a fixed sum or penalty payable if a party breaks the agreement, or forfeiture of money paid", (Ref(C, ("74",)),)),
    "breach_compensation":  ("Compensation for breach", "what a party can claim when the other breaks the contract", (Ref(C, ("73",)),)),
    "non_compete":          ("Restraint of trade", "a clause stopping someone from working or trading in a profession or business after the contract ends (non-compete)", (Ref(C, ("27",)),)),
    "forced_consent":       ("Free consent", "an agreement signed under pressure, fraud or misrepresentation", (Ref(C, ("19",)),)),
    "dispute_resolution":   ("Arbitration and courts", "who decides disputes: arbitration, a named arbitrator, or a clause that bars going to court", (Ref(C, ("28",)), Ref(ARB, ("2",)))),
    "guarantee":            ("Guarantee", "one person guaranteeing another's debt or performance", (Ref(C, ("126",)),)),
    "witnesses_attestation": ("Witnesses", "signatures, witnesses or attestation of the document", (Ref(QSO, ("17",)),)),
    "stamp_duty":           ("Stamp duty", "stamp paper, stamp duty or whether the document is properly stamped", (Ref(STAMP, ("3", "35")),)),
    "specific_performance": ("Forcing performance", "a party's right to make the other complete a sale or contract", (Ref(SRA, ("12",)),)),
    # ---- property sale and mortgage
    "property_sale":        ("Sale of property", "sale or transfer of ownership of land, a house or a plot", (Ref(TPA, ("54",)), Ref(REG, ("17",)))),
    "preemption":           ("Right of pre-emption", "a neighbour's or co-owner's right to buy the property first (Punjab)", (Ref(PREEMPT, ("5", "13"), P),)),
    "mortgage":             ("Mortgage", "property pledged for a loan, or getting it back after repayment", (Ref(TPA, ("58", "60")),)),
    # ---- tenancy
    "lease_form":           ("Lease form and registration", "the length of a lease, putting it in writing, registering it", (Ref(TPA, ("107",)), Ref(REG, ("17",)), Ref(STAMP, ("3",)))),
    "tenancy_agreement":    ("Tenancy agreement", "what the tenancy agreement must contain and that it be in writing", (Ref(PRPA, ("5", "6"), P), Ref(RRO, ("5",), I))),
    "rent_payment":         ("Paying rent", "when and how rent is paid, receipts, or depositing rent when the landlord refuses it", (Ref(PRPA, ("7", "20"), P),)),
    "rent_increase":        ("Rent increase", "increasing the rent during or after the tenancy", (Ref(RRO, ("9", "10"), I),)),
    "subletting":           ("Subletting", "the tenant letting the property to someone else", (Ref(PRPA, ("11",), P),)),
    "repairs_maintenance":  ("Repairs and upkeep", "who pays for repairs, maintenance, taxes or bills of the rented property", (Ref(PRPA, ("12", "13"), P), Ref(TPA, ("108",)))),
    "eviction":             ("Eviction and ending a tenancy", "the landlord ending the tenancy, notice to leave, grounds for eviction", (Ref(PRPA, ("15",), P), Ref(RRO, ("17",), I), Ref(TPA, ("106", "111")))),
    "rent_disputes":        ("Rent disputes", "where a landlord-tenant dispute is filed and decided", (Ref(PRPA, ("16", "19"), P), Ref(RRO, ("7",), I))),
    # ---- employment
    "employment_terms":     ("Terms of employment", "written terms of service, probation, the employment card or letter", (Ref(PLC, ("144",), P), Ref(SO, ("2A",), I))),
    "employment_termination": ("Ending employment", "firing, resignation, notice period, termination pay or redundancy", (Ref(PLC, ("146", "150"), P), Ref(SO, ("12",), I))),
    "wages_deductions":     ("Deductions from pay", "deductions, fines or recoveries taken out of salary", (Ref(PWA, ("7",)),)),
    "wage_payment":         ("Payment of wages", "when and how salary is paid", (Ref(PWA, ("5",)),)),
    "minimum_wage":         ("Minimum wage", "pay at or below the legal minimum wage", (Ref(PMW, ("11",), P), Ref(PLC, ("167",), P))),
    "working_hours":        ("Working hours", "daily or weekly working hours and overtime", (Ref(PLC, ("176", "179"), P),)),
    "domestic_work":        ("Domestic workers", "work as a maid, driver, cook or other household worker", (Ref(PDW, ("8", "13"), P),)),
    # ---- loans and business
    "interest_on_loan":     ("Interest on private loans", "interest, mark-up or profit charged on a loan between people or businesses that are not banks", (Ref(PIL_P, ("3", "7"), P), Ref(PIL_I, ("3", "7"), I))),
    "partnership_dissolution": ("Ending a partnership", "closing a partnership or a partner leaving", (Ref(PART, ("39",)),)),
}

# document category -> references that usually apply to the whole document (shown in addition to the clause topics)
CATEGORIES: dict[str, tuple[str, str, tuple[Ref, ...]]] = {
    "tenancy":     ("Tenancy / rent agreement", "a lease, rent or tenancy agreement for a house, shop or other premises", (Ref(TPA, ("105",)),)),
    "employment":  ("Employment contract", "an employment contract, appointment letter, termination or resignation letter", ()),
    "property":    ("Property sale or transfer", "a sale deed, agreement to sell, gift deed or other property transfer", (Ref(TPA, ("54",)),)),
    "loan":        ("Loan or finance", "a loan agreement, promissory note, guarantee or finance document", ()),
    "business":    ("Business or partnership", "a partnership deed, shareholder, service or supply agreement between businesses", ()),
    "contract":    ("Other contract", "any other agreement, including NDAs and service agreements", ()),
    "notice":      ("Legal notice", "a legal notice, demand letter or summons", ()),
    "court":       ("Court document", "a court order, petition, plaint or judgment", ()),
    "other":       ("Other", "anything else", ()),
}
CONTRACT_LIKE = {"tenancy", "employment", "property", "loan", "business", "contract"}
BASE_REFS = (Ref(C, ("10",)),)          # shown for any agreement


def topic_prompt() -> str:
    return "\n".join(f"  {k}: {hint}" for k, (_label, hint, _refs) in TOPICS.items())


def category_prompt() -> str:
    return "\n".join(f"  {k}: {hint}" for k, (_label, hint, _refs) in CATEGORIES.items())


# ------------------------------------------------------------------------------------------------ resolving
_SECTION_END = re.compile(r"\n\s*\d{1,3}[A-Z]?\.\s+[A-Z“\"(\[]")


def _quote(body: str, section: str, limit: int, heading: str = "") -> str:
    """The wording of ONE section from a stored chunk (a chunk can hold several sections, e.g. "Section 26 to 27"), cut at a sentence end."""
    m = re.search(rf"(?m)^\s*\[?{re.escape(section)}\.\s", body)
    text = body[m.start():] if m else body
    end = _SECTION_END.search(text, 40)
    if end:
        text = text[:end.start()]
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^\[?" + re.escape(section) + r"\.\s*", "", text)           # the section number is shown separately
    if heading and text.lower().startswith(heading.lower()):                      # ... and so is the heading
        text = text[len(heading):].lstrip(" .\u2013\u2014-:")
    if len(text) > limit:
        cut = text[:limit]
        stop = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(": "))
        text = (cut[: stop + 1] if stop > limit * 0.5 else cut.rstrip()) + " …"
    return text


def _title(act: str) -> str:
    return re.sub(r"\s+Doc$", "", act)


def _heading(row: dict, section: str) -> str:
    """Heading of the requested section. A combined chunk ("Section 3 to 5") lists its headings as "A; B; C" in the order of its section numbers."""
    heading = (row.get("heading") or "").strip()
    nums = [str(n) for n in (row.get("section_nums") or [])]
    parts = [x.strip() for x in heading.split(";")] if heading else []
    if len(nums) > 1 and len(parts) == len(nums) and section in nums:
        heading = parts[nums.index(section)]
    elif len(nums) > 1 and parts and section in nums and len(parts) != len(nums):
        heading = parts[0] if nums.index(section) == 0 else heading
    heading = re.split(r"\.\s*\(\d", heading)[0]                       # a heading with the first sentence of the section glued on
    return heading[:110].strip(" .;:-")


def resolve(kb, *, category: str | None, clause_topics: list[tuple[str, list[str], str]], jurisdiction: str | None,
            max_total: int = 8, per_clause: int = 2, quote_chars: int = 260) -> tuple[list[dict], dict[str, list[str]], list[str]]:
    """-> (citations, clause_id -> [citation ids], notes).

    `clause_topics` is [(clause id, [topic keys], risk)]. `jurisdiction` is "Punjab", "ICT" or None (unknown): province-specific references are
    only used when it is known, and a note says so otherwise.
    """
    notes: list[str] = []
    order = [j for j in (jurisdiction, "Federal") if j]                                   # preferred copy of an Act first
    cache: dict[tuple[str, str], dict | None] = {}

    def lookup(ref: Ref, section: str) -> dict | None:
        if ref.applies != (ALL,) and (jurisdiction not in ref.applies):
            return None
        key = (ref.act, section)
        if key not in cache:
            try:
                cache[key] = kb.get_section(ref.act, section, order or ["Federal"])
            except Exception:                                                              # noqa: BLE001 - a lookup problem must never fail an analysis
                log.exception("law lookup failed: %s s.%s", ref.act, section)
                cache[key] = None
        return cache[key]

    cites: dict[tuple[str, str], dict] = {}
    skipped_province = False

    def cite(ref: Ref, section: str, topic_label: str | None, clause_id: str | None, risk: str = "Low") -> str | None:
        nonlocal skipped_province
        if ref.applies != (ALL,) and jurisdiction not in ref.applies:
            skipped_province = skipped_province or (jurisdiction is None)
            return None
        row = lookup(ref, section)
        if row is None:
            return None
        key = (ref.act, section)
        c = cites.get(key)
        if c is None:
            note = None
            if row.get("legal_status") == "repealed":
                note = f"Marked as repealed in {row.get('status_scope') or 'some jurisdictions'}. Check the current law before relying on it."
            elif row.get("amended_by_titles"):
                note = "Amended later by " + "; ".join(row["amended_by_titles"][:3]) + ". The wording below may have changed: check the current law."
            heading = _heading(row, section)
            c = {"id": f"l{len(cites) + 1}", "title": _title(row["act_title"]), "reference": f"Section {section}" + (f" - {heading}" if heading else ""),
                 "type": "Rule" if row.get("unit_type") == "rule" else "Act", "url": (row.get("source_urls") or [None])[0], "jurisdiction": row["jurisdiction"],
                 "quote": _quote(row["body"], section, quote_chars, heading), "note": note, "topics": [], "clauseIds": [], "_w": 0, "_n": len(cites)}
            cites[key] = c
        if topic_label and topic_label not in c["topics"]:
            c["topics"].append(topic_label)
        if clause_id and clause_id not in c["clauseIds"]:
            c["clauseIds"].append(clause_id)
        c["_w"] += {"High": 3, "Medium": 2}.get(risk, 1) if clause_id else 0
        return c["id"]

    by_clause: dict[str, list[str]] = {}
    for cid, topics, risk in clause_topics:
        got: list[str] = []
        for t in topics:
            if t not in TOPICS:                                                              # never trust a topic key from outside the table
                continue
            label, _hint, refs = TOPICS[t]
            for ref in refs:
                for section in ref.sections:
                    if len(got) >= per_clause * 2:
                        break
                    i = cite(ref, section, label, cid, risk)
                    if i and i not in got:
                        got.append(i)
        if got:
            by_clause[cid] = got[:per_clause * 2]

    # whole-document references (the category's own, and the basic contract law for any agreement)
    if category in CONTRACT_LIKE:
        for ref in BASE_REFS:
            for s in ref.sections:
                cite(ref, s, "Valid agreements", None)
    for ref in (CATEGORIES.get(category or "", ("", "", ()))[2]):
        for s in ref.sections:
            cite(ref, s, CATEGORIES[category][0], None)

    # Every clause that has a law keeps at least its main one (the cut must never leave a clause without the law that matches it), then the
    # box is filled by importance (clauses of higher risk, more clauses) up to `max_total`; a hard ceiling stops it growing without bound.
    must = []
    for cid, ids in sorted(by_clause.items(), key=lambda kv: -max(c["_w"] for c in cites.values() if kv[1][0] == c["id"])):
        if ids[0] not in must:
            must.append(ids[0])
    ceiling = min(len(cites), max(max_total, len(must)), 14)
    by_weight = sorted(cites.values(), key=lambda c: (-c["_w"], c["_n"]))
    chosen = list(must[:ceiling])
    for c in by_weight:
        if len(chosen) >= min(ceiling, max(max_total, len(must))):
            break
        if c["id"] not in chosen:
            chosen.append(c["id"])
    ranked = sorted((c for c in cites.values() if c["id"] in chosen), key=lambda c: (-c["_w"], c["_n"]))
    keep = {c["id"] for c in ranked}
    for i, c in enumerate(ranked, start=1):                                              # renumber l1, l2, ... in the order shown
        c["_new"] = f"l{i}"
    remap = {c["id"]: c["_new"] for c in ranked}
    out = []
    for c in ranked:
        out.append({k: v for k, v in c.items() if not k.startswith("_")} | {"id": c["_new"], "clauseIds": c["clauseIds"]})
    refs_by_clause = {cid: [remap[i] for i in ids if i in keep] for cid, ids in by_clause.items()}
    refs_by_clause = {k: v for k, v in refs_by_clause.items() if v}
    if skipped_province:
        notes.append("Some laws that depend on the province are not shown because the document does not say where it applies. "
                     "Add your province in your profile to see them.")
    return out, refs_by_clause, notes


# ------------------------------------------------------------------------------------------------ self-check against the real library
def check(kb) -> list[str]:
    """Resolve every entry of the table against the law library. Returns a list of problems (empty = all good). Prints what it found."""
    problems = []
    entries = [(t, ref) for t, (_l, _h, refs) in TOPICS.items() for ref in refs] + [(c, ref) for c, (_l, _h, refs) in CATEGORIES.items() for ref in refs] \
        + [("base", r) for r in BASE_REFS]
    for name, ref in entries:
        for s in ref.sections:
            juris = list(ref.applies) + ["Federal"] if ref.applies != (ALL,) else ["Punjab", "Federal", "ICT"]
            row = kb.get_section(ref.act, s, juris)
            if row is None:
                problems.append(f"{name}: {ref.act} s.{s} NOT FOUND")
                print(f"  MISSING  {name:24} {ref.act} s.{s}")
                continue
            print(f"  ok       {name:24} {row['jurisdiction']:8} {_title(ref.act)[:42]:42} s.{s:4} {_heading(row, s)[:60]}")
    return problems


def main() -> int:
    import sys

    from chat.settings import get_settings
    from retrieval.kb import KnowledgeBase

    if "--check" not in sys.argv:
        print(__doc__)
        return 0
    kb = KnowledgeBase(get_settings().database_url)
    problems = check(kb)
    print(f"\n{sum(len(r.sections) for _, (_l, _h, rs) in TOPICS.items() for r in rs)} topic entries checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
