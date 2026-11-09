"""Legal calculators: every number comes from a rule that is written down with its source, never from the model.

Each result says how far it can be trusted:
    "law"       the rule is in the text of the law itself (checked against the law library: Limitation Act 1908 First Schedule and sections 4, 12;
                Industrial and Commercial Employment (Standing Orders) Ordinance 1968, Standing Order 12) or is the settled Hanafi law of inheritance
    "reported"  the rate was reported by news outlets or tax-firm commentary but the official gazette or FBR text could not be read (Punjab stamp duty
                after the April 2026 ordinance; FBR advance tax for tax year 2027). It can be out of date: the result says so and where to confirm.
What is NOT here: court fees (the scale differs by province and could not be verified), registration fees, capital value tax, local charges.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from typing import Any

from . import calendar_service
from .errors import ApiError

VERIFIED_ON = "2026-11-09"
PKR = lambda n: f"PKR {round(n):,}"                                        # noqa: E731


def _err(msg: str, field: str | None = None) -> ApiError:
    return ApiError(400, "VALIDATION_ERROR", msg, {"field": field} if field else None)


def _num(inputs: dict, key: str, *, lo: float = 0, hi: float = 1e13, integer: bool = False, required: bool = True, default: float = 0) -> float:
    v = inputs.get(key, None)
    if v is None or v == "":
        if required:
            raise _err(f"{key}: this field is required.", key)
        return default
    try:
        n = float(v)
    except (TypeError, ValueError):
        raise _err(f"{key}: enter a number.", key)
    if n != n or n < lo or n > hi:
        raise _err(f"{key}: enter a number between {lo:,.0f} and {hi:,.0f}.", key)
    if integer and int(n) != n:
        raise _err(f"{key}: enter a whole number.", key)
    return int(n) if integer else n


def _choice(inputs: dict, key: str, options: tuple | dict, *, default: str | None = None) -> str:
    v = inputs.get(key, default)
    if v not in options:
        raise _err(f"{key}: choose one of {', '.join(options)}.", key)
    return v


def _row(label: str, value: str) -> dict:
    return {"label": label, "value": value}


# =============================================================================================== limitation
# Limitation Act, 1908, First Schedule, checked against the text in the law library (Pakistan's version, not Azad Kashmir's, where 3 years became 6).
PROCEEDINGS: dict[str, dict] = {
    "contract_unregistered": dict(label="Suit for compensation for breach of a contract (not a registered written one)", period=("years", 3), article="Article 115",
                                  begins="the contract is broken (or, for a continuing breach, when it ends)"),
    "contract_registered": dict(label="Suit for compensation for breach of a registered written contract", period=("years", 6), article="Article 116",
                                begins="the period would begin to run on a similar unregistered contract"),
    "specific_performance": dict(label="Suit for specific performance of a contract", period=("years", 3), article="Article 113",
                                 begins="the date fixed for performance, or when the plaintiff learns performance is refused"),
    "movable_property": dict(label="Suit for specific movable property (theft, wrongful taking or detaining)", period=("years", 3), article="Article 48",
                             begins="the owner first learns in whose possession it is"),
    "possession_immovable": dict(label="Suit for possession of immovable property after dispossession", period=("years", 12), article="Article 142",
                                 begins="the date of the dispossession or discontinuance of possession"),
    "residuary": dict(label="Any other suit with no period given elsewhere in the Schedule", period=("years", 6), article="Article 120", begins="the right to sue accrues"),
    "appeal_district": dict(label="Civil appeal to the District Judge (Code of Civil Procedure)", period=("days", 30), article="Article 152",
                            begins="the date of the decree or order appealed from", appeal=True),
    "appeal_high_court": dict(label="Civil appeal to a High Court (Code of Civil Procedure)", period=("days", 90), article="Article 156",
                              begins="the date of the decree or order appealed from", appeal=True),
    "appeal_hc_original": dict(label="Appeal from a High Court's original-jurisdiction decree or order", period=("days", 20), article="Article 151",
                               begins="the date of the decree or order appealed from", appeal=True),
    "appeal_acquittal": dict(label="Criminal appeal from an order of acquittal", period=("months", 6), article="Article 157",
                             begins="the date of the order appealed from", appeal=True),
}
COURTS = {"lhc": "Lahore High Court / Punjab courts", "ihc": "Islamabad High Court / ICT courts", "sc": "Supreme Court of Pakistan", "fcc": "Federal Constitutional Court"}


def add_period(start: date, kind: str, n: int) -> date:
    if kind == "days":
        return start + timedelta(days=n)
    if kind == "years":
        try:
            return start.replace(year=start.year + n)
        except ValueError:                                                  # 29 February
            return start.replace(year=start.year + n, day=28)
    months = start.month - 1 + n
    y, m = start.year + months // 12, months % 12 + 1
    for day in (start.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            continue
    raise ValueError("bad date")


def limitation(inputs: dict, today: date) -> dict:
    kind = _choice(inputs, "kind", PROCEEDINGS)
    court = _choice(inputs, "court", COURTS, default="lhc")
    try:
        start = date.fromisoformat(str(inputs.get("date", "")))
    except ValueError:
        raise _err("date: enter the date as year-month-day.", "date")
    if not date(1900, 1, 1) <= start <= today + timedelta(days=366):
        raise _err("date: enter a date between 1900 and a year from now.", "date")
    p = PROCEEDINGS[kind]
    copy_days = int(_num(inputs, "copyDays", lo=0, hi=365, integer=True, required=False)) if p.get("appeal") else 0
    unit, n = p["period"]
    base = add_period(start, unit, n)                                       # section 12(1): the day the period is counted from is left out
    last = base + timedelta(days=copy_days)                                 # section 12(2): time taken to get the certified copy is left out too
    final, closed = calendar_service.next_open_day(last, court)             # section 4: a day the court is closed moves the last day to the next open day
    days_left = (final - today).days
    plural = f"{n} {unit if n != 1 else unit[:-1]}"
    rows = [_row("Proceeding", p["label"]), _row("Period", f"{plural} ({p['article']})"), _row("Counted from", start.strftime("%d %b %Y")),
            _row("Period ends", base.strftime("%d %b %Y"))]
    if copy_days:
        rows.append(_row(f"Plus {copy_days} day(s) for the certified copy", last.strftime("%d %b %Y")))
    if closed:
        rows.append(_row("Court closed on the last day", "; ".join(closed)))
    rows.append(_row("Days remaining" if days_left >= 0 else "Status", f"{days_left} days" if days_left >= 0 else f"Expired {-days_left} days ago"))
    notes = [f"Under the Schedule, time starts to run from: {p['begins']}. The day it starts from is not counted (Limitation Act, section 12(1)).",
             "If an earlier case was brought in good faith in a court with no jurisdiction, the time it took may be left out (section 14).",
             "A late appeal or application can be admitted if there was sufficient cause (section 5). A late suit cannot." if p.get("appeal") else
             "A suit filed after the period is dismissed, even if it is a good claim. The court cannot excuse the delay (section 3).",
             "Check the date the period starts from with a lawyer: it is the step people most often get wrong."]
    if closed:
        notes.insert(0, "The last day was moved because the court is closed that day (section 4: Sundays and public holidays). File on or before the earlier date to be safe.")
    vac = calendar_service.vacation_on(final, court)
    if vac:
        notes.append(f"The last day falls in the court's vacation ({vac['title']}, {vac['start']} to {vac['end']}). Offices usually stay open and urgent matters are heard, "
                     "but this does not move the deadline: ask the registry where to file.")
    return {"text": final.strftime("%d %b %Y"), "rows": rows, "notes": notes, "confidence": "law",
            "source": {"title": "Limitation Act, 1908", "reference": f"First Schedule, {p['article']}; sections 4, 5, 12 and 14", "url": "https://pakistancode.gov.pk/pdffiles/administrator3294e35255f255ea96b3356091fb4844.pdf"},
            "assumptions": [f"The court is: {COURTS[court]}.", "Court holidays come from the dashboard calendar, which is collected from news reports (see its notes)."],
            "details": {"lastDay": final.isoformat(), "periodEnds": base.isoformat(), "daysLeft": days_left, "movedBy": closed}}


# =============================================================================================== inheritance
def _frac(f: Fraction) -> str:
    return f"{f.numerator}/{f.denominator}" if f.denominator != 1 else str(f.numerator)


def faraid(husband: bool, wives: int, sons: int, daughters: int, father: bool, mother: bool) -> tuple[dict[str, Fraction], list[str]]:
    """Shares (as fractions of the whole estate) under Hanafi law for these heirs only. Returns ({heir: share}, notes). `wives` is the number of widows."""
    F = Fraction
    children = sons + daughters > 0
    notes: list[str] = []
    s: dict[str, Fraction] = {}
    if husband:
        s["husband"] = F(1, 4) if children else F(1, 2)
    if wives:
        s["wives"] = F(1, 8) if children else F(1, 4)
    spouse = s.get("husband", F(0)) + s.get("wives", F(0))
    if mother:
        if children:
            s["mother"] = F(1, 6)
        elif father and spouse:                                             # the two "Umariyyatayn" cases: mother takes a third of what is left after the spouse
            s["mother"] = (1 - spouse) / 3
            notes.append("Mother's share is one third of what remains after the spouse's share (the Umariyyatayn rule).")
        else:
            s["mother"] = F(1, 3)
    if father and sons:
        s["father"] = F(1, 6)
    elif father and daughters:
        s["father"] = F(1, 6)                                               # plus whatever is left (below)
    if daughters and not sons:
        s["daughters"] = F(1, 2) if daughters == 1 else F(2, 3)
    fixed = sum(s.values(), F(0))
    out: dict[str, Fraction] = dict(s)
    if fixed > 1:                                                           # 'awl: the fixed shares add up to more than the estate, so each is reduced in proportion
        out = {k: v / fixed for k, v in s.items()}
        notes.append(f"The fixed shares add up to {_frac(fixed)} of the estate, which is more than the whole, so each share is reduced in proportion ('awl).")
    else:
        rest = 1 - fixed
        if sons:
            units = 2 * sons + daughters
            out["sons"] = rest * (2 * sons) / units
            if daughters:
                out["daughters"] = rest * daughters / units
            if rest:
                notes.append("What remains after the fixed shares is shared between sons and daughters, each son taking twice a daughter's share.")
        elif father:
            out["father"] = out.get("father", F(0)) + rest
            if rest and daughters:
                notes.append("The father also takes what remains after the fixed shares, because there is no son.")
        elif rest:
            sharers = {k: v for k, v in s.items() if k in ("daughters", "mother")}   # radd: the remainder goes back to the sharers, but never to a spouse
            if sharers:
                total = sum(sharers.values(), F(0))
                for k, v in sharers.items():
                    out[k] = v + rest * v / total
                notes.append("There is no one to take the remainder as a residuary heir, so it goes back to the sharers other than the spouse in proportion to their shares (radd).")
            else:
                notes.append(f"{_frac(rest)} of the estate is left after the spouse's share and passes to other relatives, who this calculator does not cover. Ask a lawyer.")
    return out, notes


def inheritance(inputs: dict) -> dict:
    estate = _num(inputs, "amount", lo=1)
    spouse = _choice(inputs, "spouse", ("Wife", "Husband", "None"), default="None")
    wives = int(_num(inputs, "wives", lo=1, hi=4, integer=True, required=False, default=1)) if spouse == "Wife" else 0
    sons = int(_num(inputs, "sons", lo=0, hi=50, integer=True, required=False))
    daughters = int(_num(inputs, "daughters", lo=0, hi=50, integer=True, required=False))
    father = bool(inputs.get("father")) and inputs.get("father") not in ("No", "no", "false", "False", "0")
    mother = bool(inputs.get("mother")) and inputs.get("mother") not in ("No", "no", "false", "False", "0")
    if not (spouse != "None" or sons or daughters or father or mother):
        raise _err("Add at least one heir: a spouse, a child, or a parent.")
    if not (sons or daughters or father or mother):
        raise _err("With only a spouse surviving, the rest of the estate goes to other relatives (brothers, sisters, uncles...), which this calculator does not cover. "
                   "Ask a lawyer or the Family Court.")
    shares, notes = faraid(spouse == "Husband", wives, sons, daughters, father, mother)
    rows = [_row("Total estate (after debts and funeral costs)", PKR(estate))]
    order = ("husband", "wives", "mother", "father", "sons", "daughters")
    names = {"husband": "Husband", "wives": f"Widow{'s' if wives > 1 else ''}", "mother": "Mother", "father": "Father", "sons": "Sons", "daughters": "Daughters"}
    count = {"wives": wives, "sons": sons, "daughters": daughters}
    for k in order:
        if k not in shares or shares[k] == 0:
            continue
        share, n = shares[k], count.get(k, 1)
        rows.append(_row(f"{names[k]} ({_frac(share)} of the estate)", PKR(estate * float(share)) + (f", {PKR(estate * float(share / n))} each" if n > 1 else "")))
    check = sum(shares.values(), Fraction(0))
    leftover = 1 - check
    if leftover > 0:
        rows.append(_row("Left for other relatives", PKR(estate * float(leftover))))
    return {"total": estate, "rows": rows, "notes": notes, "confidence": "law",
            "source": {"title": "Muslim Family Laws Ordinance, 1961 (section 4) and the Hanafi law of succession (Quran 4:11, 4:12)", "reference": "Fixed shares and residuary heirs",
                       "url": "https://pakistancode.gov.pk/pdffiles/administratoreecaf3b490e2d43d2e3b50c0c068b5d7.pdf"},
            "assumptions": ["The deceased was a Muslim and the estate is what is left after funeral costs, debts and any lawful will (up to one third).",
                            "Only a spouse, sons, daughters, father and mother are counted. Grandchildren, brothers and sisters, grandparents and other relatives are not.",
                            "Hanafi rules apply (the usual position in Pakistan). Shia law divides some cases differently.",
                            "This is an estimate. A succession certificate or a court decides the real shares."],
            "details": {"shares": {k: _frac(v) for k, v in shares.items()}}}


# =============================================================================================== compensation (Standing Order 12)
def compensation(inputs: dict) -> dict:
    wage = _num(inputs, "salary", lo=1)
    years = int(_num(inputs, "years", lo=0, hi=60, integer=True))
    months = int(_num(inputs, "months", lo=0, hi=11, integer=True, required=False))
    reason = _choice(inputs, "reason", ("Termination without misconduct", "Retrenchment", "Resignation", "Retirement"), default="Termination without misconduct")
    kind = _choice(inputs, "workman", ("Permanent", "Temporary / probationer"), default="Permanent")
    pf = _choice(inputs, "providentFund", ("No", "Yes"), default="No")
    permanent = kind == "Permanent"
    notice = wage if (permanent and reason in ("Termination without misconduct", "Retrenchment")) else 0
    completed = years + (1 if months > 6 else 0)
    gratuity = 0 if pf == "Yes" else wage * completed
    rows = [_row("Monthly wage used", PKR(wage)), _row("Service", f"{years} year(s) {months} month(s)"),
            _row("Years counted for gratuity", f"{completed} (every completed year, plus a part-year of more than six months)")]
    rows.append(_row("Gratuity (30 days' wages per counted year)", PKR(gratuity) if pf == "No" else "PKR 0 (employer provident fund)"))
    rows.append(_row("Pay in lieu of one month's notice", PKR(notice)))
    notes = ["Gratuity is 30 days' wages for every completed year of service or any part in excess of six months, when a workman resigns or is terminated for any reason other than misconduct (Standing Order 12(6)).",
             "A permanent workman terminated for a reason other than misconduct gets one month's notice, or one month's wages in lieu, worked out on the average of the last three months (12(1)).",
             "A temporary workman, probationer or badli is not entitled to notice (12(2)).",
             "Wages and other dues, including unused leave, must be paid before the end of the second working day after termination (12(4)).",
             "If you were dismissed without a written order giving the reason, or you disagree with the termination, bring your grievance to your employer in writing within 90 days (Industrial Relations Act, 2012, section 33; the Punjab Industrial Relations Act, 2010, section 33 allows three months). Ask a labour lawyer or the labour department."]
    if pf == "Yes":
        notes.append("No gratuity is payable for the period covered by an employer provident fund to which the workman contributes and the employer pays at least as much (12(6) proviso). "
                     "You keep the provident fund balance. If the fund did not cover your whole service, ask for gratuity for the rest.")
    return {"total": gratuity + notice, "rows": rows, "notes": notes, "confidence": "law",
            "source": {"title": "Industrial and Commercial Employment (Standing Orders) Ordinance, 1968", "reference": "Standing Order 12 (Termination of employment)", "url": "https://pakistancode.gov.pk"},
            "assumptions": ["The workman works in an industrial or commercial establishment covered by the Standing Orders. Government employees, domestic workers and some others are not covered.",
                            "Wage = the last month's wage for a fixed-rate workman (the highest pay of the last twelve months for a piece-rated one).",
                            "A collective agreement, contract or custom can give more. This is the legal minimum."]}


# =============================================================================================== stamp duty and property transfer (Punjab): "reported"
PUNJAB_STAMP_PCT = 1.0                                                      # Stamp (Amendment) Ordinance 2026, signed 10 April 2026, uniform urban and rural
ADV_TAX_TY2027 = {                                                          # Finance Act 2026, tax year 2027 (1 July 2026 to 30 June 2027)
    "seller_filer": 2.75, "seller_nonfiler": 11.5,                          # section 236C
    "buyer_filer": 1.25, "buyer_nonfiler_bands": ((50_000_000, 10.5), (100_000_000, 14.5), (float("inf"), 18.5)),   # section 236K
}
REPORTED_SOURCES = ("Punjab stamp duty: ARY News 10 Apr 2026, Dawn 13 Apr 2026 and The News 11 Apr 2026 (news reports of the Stamp (Amendment) Ordinance 2026). "
                    "Advance tax: Profit (Pakistan Today) 12 Jun 2026 and ICT.edu.pk 14 Sep 2026 (commentary on the Finance Act 2026). The official gazette and FBR text were not available.")


def stamp(inputs: dict) -> dict:
    value = _num(inputs, "amount", lo=1)
    inst = _choice(inputs, "instrument", ("Sale / conveyance of immovable property",), default="Sale / conveyance of immovable property")
    duty = value * PUNJAB_STAMP_PCT / 100
    return {"total": duty, "rows": [_row("Value in the deed", PKR(value)), _row("Instrument", inst), _row(f"Stamp duty ({PUNJAB_STAMP_PCT:g}%)", PKR(duty))],
            "notes": ["Reported change: the Punjab Stamp (Amendment) Ordinance 2026 (signed 10 April 2026) made the rate 1% for urban and rural property alike. Before it, rural property paid 3%.",
                      "Some reports say the 1% applies for a 12-month window to 'assignable' deeds and 2% after that. The sources disagree, so check with the sub-registrar which applies to your deed.",
                      "Rates for gift deeds, leases, powers of attorney and exchanges after the ordinance were not found, so they are not offered here.",
                      "The duty is charged on the value in the deed, which the registrar can test against the district collector's valuation. Registration fees and local charges are extra."],
            "confidence": "reported",
            "source": {"title": "Stamp Act, 1899 as amended in Punjab (Stamp (Amendment) Ordinance, 2026)", "reference": "Reported by news outlets: " + REPORTED_SOURCES, "url": "https://www.dawn.com/news/1991242"},
            "assumptions": ["Punjab only. Other provinces and Islamabad are not offered because their current rates could not be confirmed.",
                            "The ordinance was still in force on the date this was checked (9 Nov 2026) and has not been replaced."]}


def property_transfer(inputs: dict) -> dict:
    value = _num(inputs, "amount", lo=1)
    filer_seller = _choice(inputs, "sellerStatus", ("Filer", "Non-filer"), default="Filer")
    filer_buyer = _choice(inputs, "buyerStatus", ("Filer", "Non-filer"), default="Filer")
    st = value * PUNJAB_STAMP_PCT / 100
    seller_pct = ADV_TAX_TY2027["seller_filer"] if filer_seller == "Filer" else ADV_TAX_TY2027["seller_nonfiler"]
    if filer_buyer == "Filer":
        buyer_pct = ADV_TAX_TY2027["buyer_filer"]
    else:
        buyer_pct = next(p for limit, p in ADV_TAX_TY2027["buyer_nonfiler_bands"] if value <= limit)
    t236c, t236k = value * seller_pct / 100, value * buyer_pct / 100
    buyer_total, seller_total = st + t236k, t236c
    rows = [_row("Property value", PKR(value)), _row(f"Stamp duty, Punjab ({PUNJAB_STAMP_PCT:g}%), paid by the buyer", PKR(st)),
            _row(f"Advance tax on purchase, section 236K ({buyer_pct:g}%, {filer_buyer.lower()})", PKR(t236k)),
            _row("Buyer's total", PKR(buyer_total)),
            _row(f"Advance tax on sale, section 236C ({seller_pct:g}%, {filer_seller.lower()}), paid by the seller", PKR(seller_total))]
    notes = ["Federal advance taxes for tax year 2027 (1 July 2026 to 30 June 2027), as reported for the Finance Act 2026: filers pay a flat 2.75% as seller (236C) and 1.25% as buyer (236K), and the value bands for filers were removed.",
             "'Filer' means on FBR's Active Taxpayers List. The non-filer rates come from one commentary source only; treat them as a rough guide and check with FBR or a tax adviser.",
             "These advance taxes are normally collected when the property is registered. For a filer they can be adjusted against the final income tax.",
             "Not included: registration fee, local government fees, society transfer fees, any capital gains or other income tax, and lawyer or typist charges."]
    return {"total": buyer_total, "rows": rows, "notes": notes, "confidence": "reported",
            "source": {"title": "Stamp Act, 1899 (Punjab) and Income Tax Ordinance, 2001, sections 236C and 236K as amended by the Finance Act 2026", "reference": "Reported by news and tax commentary: " + REPORTED_SOURCES,
                       "url": "https://profit.pakistantoday.com.pk/2026/06/12/government-slashes-property-transfer-taxes-in-finance-bill-2026-27"},
            "assumptions": ["Punjab property. The value is the fair market value or the value in the deed, whichever applies to the tax (they can differ).",
                            "Rates are for transfers registered from 1 July 2026 and can change with the next budget.",
                            "Section 7E (the deemed-income tax on property) is reported to have been removed and is not included."],
            "details": {"seller": seller_total, "buyer": buyer_total}}


# =============================================================================================== registry
CALCULATORS: dict[str, dict] = {
    "limitation": {"name": "Limitation Period", "confidence": "law"},
    "inheritance": {"name": "Inheritance Share", "confidence": "law"},
    "compensation": {"name": "Compensation", "confidence": "law"},
    "stamp": {"name": "Stamp Duty", "confidence": "reported"},
    "property": {"name": "Property Transfer", "confidence": "reported"},
}
UNAVAILABLE = [{"key": "court", "name": "Court Fee", "reason": "Court fee scales differ by province and are changed by provincial Finance Acts. The current Punjab, Sindh, KP and Balochistan scales could not be verified from an official source, so no figure is shown rather than a wrong one."}]


def meta() -> dict:
    return {"verifiedOn": VERIFIED_ON, "items": [{"key": k, **v} for k, v in CALCULATORS.items()], "unavailable": UNAVAILABLE,
            "options": {"limitation": [{"key": k, "label": v["label"], "appeal": bool(v.get("appeal"))} for k, v in PROCEEDINGS.items()], "courts": COURTS}}


def calculate(kind: str, inputs: dict[str, Any], today: date | None = None) -> dict:
    today = today or date.today()
    if kind == "limitation":
        r = limitation(inputs, today)
    elif kind == "inheritance":
        r = inheritance(inputs)
    elif kind == "compensation":
        r = compensation(inputs)
    elif kind == "stamp":
        r = stamp(inputs)
    elif kind == "property":
        r = property_transfer(inputs)
    elif kind in {u["key"] for u in UNAVAILABLE}:
        raise ApiError(422, "UNPROCESSABLE", next(u["reason"] for u in UNAVAILABLE if u["key"] == kind))
    else:
        raise ApiError(404, "NOT_FOUND", "That calculator does not exist.")
    r["calculatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    r["verifiedOn"] = VERIFIED_ON
    r["type"] = kind
    return r


# =============================================================================================== PDF summary of a saved calculation
def summary_pdf(title: str, result: dict, inputs: dict, saved_at: str | None) -> bytes:
    """A one-to-two page PDF of a saved calculation: result, breakdown, notes, source and how far to trust it."""
    import pymupdf

    trust = {"law": "Based on the text of the law, checked against the law library.", "reported": "Based on news reports of recent changes: confirm with the official source before relying on it."}
    headline = result.get("text") or (PKR(result["total"]) if result.get("total") is not None else "")
    lines = [title, "", f"Result: {headline}", f"Calculated on {result.get('calculatedAt', '')[:10] or (saved_at or '')[:10]}; data checked on {result.get('verifiedOn', VERIFIED_ON)}",
             f"How far to trust it: {trust.get(result.get('confidence'), '')}", "", "Breakdown"]
    lines += [f"  {r['label']}: {r['value']}" for r in result.get("rows", [])]
    if result.get("notes"):
        lines += ["", "Notes"] + [f"  - {n}" for n in result["notes"]]
    if result.get("assumptions"):
        lines += ["", "Assumptions"] + [f"  - {a}" for a in result["assumptions"]]
    src = result.get("source") or {}
    lines += ["", "Source", f"  {src.get('title', '')}", f"  {src.get('reference', '')}"] + ([f"  {src['url']}"] if src.get("url") else [])
    lines += ["", "Inputs: " + ", ".join(f"{k} = {v}" for k, v in inputs.items()), "", "This is an estimate for information only, not legal advice. LegalMate."]
    doc = pymupdf.open()
    rect = pymupdf.Rect(48, 48, 547, 794)
    wrapped: list[str] = []
    for ln in lines:                                                          # wrap long lines ourselves so every page holds a known number of lines
        while len(ln) > 98:
            cut = ln.rfind(" ", 0, 98)
            cut = cut if cut > 40 else 98
            wrapped.append(ln[:cut])
            ln = "    " + ln[cut:].lstrip()
        wrapped.append(ln)
    per_page = 58
    for i in range(0, len(wrapped), per_page):
        page = doc.new_page(width=595, height=842)
        page.insert_textbox(rect, "\n".join(wrapped[i:i + per_page]), fontsize=10, fontname="helv")
    out = doc.tobytes()
    doc.close()
    return out
