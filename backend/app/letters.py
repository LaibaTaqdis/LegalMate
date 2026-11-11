"""Draft letters from fill-in templates.

The letters are built by code from the user's own facts: no model is called, so nothing is invented, nothing leaves the server and a letter costs
nothing. The wording is careful and general (no section numbers except the one checked in the law library, see `payment_notice`) and every letter
says it is a draft to be checked by a lawyer. English only; the PDF uses Latin letters.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from .errors import ApiError

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MAX_TEXT, MAX_LONG = 160, 1500


def _err(msg: str, field: str | None = None) -> ApiError:
    return ApiError(422, "UNPROCESSABLE", msg, {"field": field} if field else None)


def pkr(n: float) -> str:
    return f"PKR {round(n):,}"


def fdate(s: str) -> str:
    d = date.fromisoformat(s)
    return f"{d.day} {d.strftime('%B %Y')}"


# ---------------------------------------------------------------------------------------------- fields
def F(key, label, type="text", *, required=True, options=None, default=None, help=None, placeholder=None, lo=None, hi=None) -> dict:
    return {"key": key, "label": label, "type": type, "required": required, "options": options, "default": default, "help": help, "placeholder": placeholder, "lo": lo, "hi": hi}


def common(recipient_label: str, recipient_hint: str) -> list[dict]:
    return [
        F("senderName", "Your full name"), F("senderAddress", "Your address", "textarea", help="Printed under your name."),
        F("recipientName", recipient_label, placeholder=recipient_hint), F("recipientAddress", "Their address", "textarea", required=False),
        F("letterDate", "Date of the letter", "date", default="today"),
    ]


def clean_fields(spec: list[dict], raw: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    out: dict[str, Any] = {}
    for f in spec:
        k, v = f["key"], raw.get(f["key"])
        if v is None or (isinstance(v, str) and not v.strip()):
            if f["default"] == "today" and f["type"] == "date":
                v = today.isoformat()
            elif f["default"] is not None and f["default"] != "today":
                v = f["default"]
            elif f["required"]:
                raise _err(f"{f['label']}: this field is required.", k)
            else:
                out[k] = None
                continue
        if f["type"] in ("text", "textarea", "select"):
            s = _CTRL.sub("", str(v)).strip()
            if len(s) > (MAX_LONG if f["type"] == "textarea" else MAX_TEXT):
                raise _err(f"{f['label']}: please keep this shorter.", k)
            if f["type"] == "select" and s not in f["options"]:
                raise _err(f"{f['label']}: choose one of the options.", k)
            out[k] = s
        elif f["type"] == "number":
            try:
                n = float(str(v).replace(",", ""))
            except ValueError:
                raise _err(f"{f['label']}: enter a number.", k)
            if not (f["lo"] if f["lo"] is not None else 0) <= n <= (f["hi"] if f["hi"] is not None else 1e12):
                raise _err(f"{f['label']}: enter a number between {f['lo'] or 0:,.0f} and {f['hi'] or 1e12:,.0f}.", k)
            out[k] = n
        elif f["type"] == "date":
            try:
                d = date.fromisoformat(str(v))
            except ValueError:
                raise _err(f"{f['label']}: enter the date as year-month-day.", k)
            if not (date(1990, 1, 1) <= d <= date(today.year + 2, 12, 31)):
                raise _err(f"{f['label']}: this date does not look right.", k)
            out[k] = d.isoformat()
    return out


# ---------------------------------------------------------------------------------------------- templates
def _lines(items: list[str | None]) -> list[str]:
    return [i for i in items if i]


def build_tenant_reply(v: dict) -> dict:
    paid = {"Rent is paid up to date": f"I have paid the rent up to date{', at ' + pkr(v['monthlyRent']) + ' a month' if v.get('monthlyRent') else ''}, and I can show receipts or proof of payment.",
            "Some rent is unpaid": "I accept that some rent is outstanding and I am willing to settle it. Please send me a written statement of the amount you claim, so that I can pay it or discuss a fair plan.",
            "I dispute the rent claimed": "I do not agree with the rent you claim. Please send me a written statement showing how the amount is calculated, and I will answer it."}[v["rentStatus"]]
    return {"subject": f"Reply to your notice dated {fdate(v['noticeDate'])} about the premises at {v['propertyAddress']}", "paragraphs": _lines([
        f"I am the tenant of the premises at {v['propertyAddress']}" + (f", where I have lived since {fdate(v['tenancyStart'])}" if v.get("tenancyStart") else "") + f". I received your notice dated {fdate(v['noticeDate'])} asking me to leave the premises. The reason given is: \"{v['reasonInNotice']}\".",
        paid,
        "I have not agreed to leave. To my understanding, a landlord who wants a tenant to leave must follow the procedure that the law provides and cannot simply require the tenant to go. I therefore ask you to withdraw the notice, or to tell me in writing the legal grounds on which you rely and the law under which you are acting.",
        "Please do not cut off water, electricity or gas, and please do not enter the premises without reasonable notice. I remain willing to pay the rent and to talk about a fair solution in writing.",
        "If this cannot be settled between us, I will take legal advice and protect my rights before the proper forum.",
    ]), "enclosures": ["Copy of your notice", "Rent receipts or proof of payment (if any)", "Copy of the tenancy agreement (if any)"]}


def build_deposit_demand(v: dict) -> dict:
    days = int(v["deadlineDays"])
    return {"subject": f"Demand for return of my security deposit of {pkr(v['depositAmount'])}", "paragraphs": _lines([
        f"I paid you a security deposit of {pkr(v['depositAmount'])} on {fdate(v['paidOn'])} for the premises at {v['propertyAddress']}. I handed the premises back to you on {fdate(v['vacatedOn'])}.",
        f"You have not returned the deposit. " + (f"You have said that it is being kept for: \"{v['deductionsClaimed']}\". If you claim any deduction, please send me an itemised written statement with proof of the cost, so that I can answer it." if v.get("deductionsClaimed") else "You have not given me any written reason for keeping it."),
        f"I request you to pay me {pkr(v['depositAmount'])} (less any deduction you can show in writing to be proper) within {days} days of the date of this letter.",
        "If I do not receive the amount or a written reply within that time, I will take legal advice and recover the amount and my costs through the proper forum.",
    ]), "enclosures": ["Proof of payment of the deposit (receipt or bank transfer)", "Tenancy agreement (if any)", "Proof that the premises were handed back (if any)"]}


def build_payment_notice(v: dict) -> dict:
    days = int(v["deadlineDays"])
    reason = v["reason"]
    why = {"Money lent": f"I lent you {pkr(v['amountOwed'])}, which you agreed to repay by {fdate(v['dateDue'])}.",
           "Goods or services supplied": f"I supplied goods or services to you, and {pkr(v['amountOwed'])} became due for payment on {fdate(v['dateDue'])}.",
           "Bounced cheque": f"You gave me a cheque for {pkr(v['amountOwed'])}" + (f", number {v['chequeNo']}" if v.get("chequeNo") else "") + (f", drawn on {v['bank']}" if v.get("bank") else "") + (f", dated {fdate(v['chequeDate'])}" if v.get("chequeDate") else "") + ". When it was presented to the bank it was not honoured.",
           "Unpaid rent": f"{pkr(v['amountOwed'])} of rent became due on {fdate(v['dateDue'])} and has not been paid."}[reason]
    paras = _lines([
        why,
        f"Despite my requests, the amount of {pkr(v['amountOwed'])} remains unpaid." + (f" {v['details']}" if v.get("details") else ""),
        f"I call upon you to pay {pkr(v['amountOwed'])} within {days} days of the date of this letter.",
        "I reserve the right to take civil action to recover the amount with costs" + (", and to take action under section 489-F of the Pakistan Penal Code, 1860 (dishonestly issuing a cheque)" if reason == "Bounced cheque" else "") + ", if it is not paid within that time. This letter may be produced as evidence of my demand.",
    ])
    return {"subject": f"Notice demanding payment of {pkr(v['amountOwed'])}", "paragraphs": paras,
            "enclosures": _lines(["Copy of the cheque and the bank's return memo" if reason == "Bounced cheque" else None, "Agreement, invoice or messages showing the debt", "Any proof of payment already received"])}


def build_employer_grievance(v: dict) -> dict:
    reason = {"No reason given": "No reason was given to me for the termination.", "Misconduct alleged": "I was told that the reason was misconduct. I was not given a fair chance to answer the allegation.",
              "Poor performance": "I was told that the reason was my performance. I was not given a written warning or a chance to improve.",
              "Retrenchment / closure": "I was told that my post was ended because of retrenchment or closure."}.get(v["reasonGiven"], f"The reason I was given is: {v['reasonGiven']}.")
    return {"subject": f"Written grievance about the termination of my employment on {fdate(v['terminationDate'])}", "paragraphs": _lines([
        f"I worked for you as {v['designation']} from {fdate(v['joiningDate'])}. My employment was ended on {fdate(v['terminationDate'])}" + (" without a written order." if v["writtenOrder"] == "No" else ", by a written order."),
        reason,
        "I am sending this letter as my written grievance about the termination. I request you to: (1) give me, in writing, the reasons for ending my employment; (2) pay my wages up to the last day, the notice pay or wages in lieu of notice, gratuity for my years of service and any unused leave, as the law and my contract provide, with a statement of how each amount is worked out; (3) if misconduct is alleged, give me the allegation in writing and a fair chance to answer it; and (4) reconsider the termination.",
        "Please reply in writing within 14 days. If the matter is not settled I will take advice and use the remedies the law gives me before the proper labour forum, which may have short time limits.",
    ]), "enclosures": ["Appointment letter or contract (if any)", "Salary slips or bank statements", "Termination letter or messages about the termination"]}


def build_harassment_complaint(v: dict) -> dict:
    return {"subject": "Formal complaint of harassment", "paragraphs": _lines([
        f"I am writing to make a formal complaint against {v['respondentName']}" + (f", {v['respondentRole']}" if v.get("respondentRole") else "") + f", at {v['place']}.",
        f"The behaviour took place {v['whenItHappened']}. What happened: {v['description']}",
        (f"Witnesses: {v['witnesses']}." if v.get("witnesses") else None),
        (f"Evidence I have: {v['evidence']}." if v.get("evidence") else None),
        "I ask that the complaint be taken up under the harassment law that applies to your organisation and its code of conduct, that an inquiry be started without delay, that it be handled confidentially, and that I be protected from any retaliation while it is pending. Please confirm in writing that you have received this complaint and tell me the next steps.",
    ]), "enclosures": _lines(["Messages, emails or screenshots" if v.get("evidence") else None, "Any earlier complaint and the reply"])}


def build_consumer_notice(v: dict) -> dict:
    ask = {"Refund": "refund the price I paid", "Replacement": "replace it with a product or service that works", "Repair": "repair it free of charge", "Refund or replacement, as I choose": "refund the price or replace it, as I choose"}[v["demand"]]
    return {"subject": f"Notice about a defective {v['item']}", "paragraphs": _lines([
        f"On {fdate(v['purchaseDate'])} I bought {v['item']} from you for {pkr(v['price'])}.",
        f"The problem is: {v['defect']}",
        f"I request you to {ask} within {int(v['deadlineDays'])} days of the date of this letter.",
        "If you do not reply or do not fix the problem in that time, I will make a complaint under the consumer protection law that applies in my province and take the other steps the law allows.",
    ]), "enclosures": ["Receipt, invoice or proof of payment", "Photographs of the problem", "Earlier messages with the seller (if any)"]}


LETTERS: dict[str, dict] = {
    "tenant_reply": {
        "title": "Reply to a landlord's eviction notice", "summary": "Say in writing that you have not agreed to leave and ask for the legal grounds.",
        "who": "Tenant", "build": build_tenant_reply,
        "fields": common("Landlord's name", "As in the notice") + [
            F("propertyAddress", "Address of the rented property", "textarea"), F("noticeDate", "Date of the landlord's notice", "date"),
            F("reasonInNotice", "Reason the landlord gave", "textarea", help="If it was only said out loud, write what was said."),
            F("rentStatus", "Your rent", "select", options=["Rent is paid up to date", "Some rent is unpaid", "I dispute the rent claimed"], default="Rent is paid up to date"),
            F("monthlyRent", "Monthly rent (PKR)", "number", required=False, lo=1), F("tenancyStart", "Date the tenancy began", "date", required=False)]},
    "deposit_demand": {
        "title": "Demand for your security deposit", "summary": "Ask the landlord to return the deposit, or to explain any deduction in writing.",
        "who": "Tenant", "build": build_deposit_demand,
        "fields": common("Landlord's name", "The person you paid the deposit to") + [
            F("propertyAddress", "Address of the property", "textarea"), F("depositAmount", "Deposit paid (PKR)", "number", lo=1), F("paidOn", "Date you paid it", "date"),
            F("vacatedOn", "Date you handed the property back", "date"),
            F("deductionsClaimed", "Reason the landlord gave for keeping it", "textarea", required=False), F("deadlineDays", "Days you give to pay", "number", default=14, lo=7, hi=60)]},
    "payment_notice": {
        "title": "Notice demanding payment of money owed", "summary": "A written demand for money lent, an unpaid bill, unpaid rent or a bounced cheque.",
        "who": "Anyone owed money", "build": build_payment_notice,
        "fields": common("Name of the person who owes you", "The debtor") + [
            F("reason", "Why the money is owed", "select", options=["Money lent", "Goods or services supplied", "Bounced cheque", "Unpaid rent"], default="Money lent"),
            F("amountOwed", "Amount owed (PKR)", "number", lo=1), F("dateDue", "Date it was due", "date"),
            F("chequeNo", "Cheque number (bounced cheque)", required=False), F("bank", "Bank the cheque was drawn on", required=False), F("chequeDate", "Date on the cheque", "date", required=False),
            F("details", "Anything else to add", "textarea", required=False), F("deadlineDays", "Days you give to pay", "number", default=15, lo=7, hi=60)]},
    "employer_grievance": {
        "title": "Written grievance after losing a job", "summary": "Ask for the reasons in writing, your dues, and a fair chance to answer.",
        "who": "Employee", "build": build_employer_grievance,
        "fields": common("Employer's name", "Company or owner") + [
            F("designation", "Your job title"), F("joiningDate", "Date you joined", "date"), F("terminationDate", "Date your job ended", "date"),
            F("reasonGiven", "Reason given", "select", options=["No reason given", "Misconduct alleged", "Poor performance", "Retrenchment / closure"], default="No reason given"),
            F("writtenOrder", "Did you get a written termination order?", "select", options=["No", "Yes"], default="No")]},
    "harassment_complaint": {
        "title": "Complaint of harassment at work or campus", "summary": "A formal complaint to the employer or institution, asking for an inquiry and protection.",
        "who": "Employee or student", "build": build_harassment_complaint,
        "fields": common("Addressed to (committee, HR or head)", "For example: The Inquiry Committee") + [
            F("respondentName", "Name of the person you are complaining about"), F("respondentRole", "Their position", required=False), F("place", "Where it happened (office, department, campus)"),
            F("whenItHappened", "When it happened", placeholder="For example: between March and June 2026"),
            F("description", "What happened", "textarea", help="Facts only: what was said or done, and how often."),
            F("witnesses", "Witnesses", required=False), F("evidence", "Evidence you have (messages, photos)", required=False)]},
    "consumer_notice": {
        "title": "Notice about a faulty product or service", "summary": "Tell the seller what is wrong and what you want, with a deadline.",
        "who": "Buyer", "build": build_consumer_notice,
        "fields": common("Seller's or shop's name", "Who you bought it from") + [
            F("item", "What you bought", placeholder="For example: a washing machine"), F("purchaseDate", "Date of purchase", "date"), F("price", "Price paid (PKR)", "number", lo=1),
            F("defect", "What is wrong", "textarea"),
            F("demand", "What you want", "select", options=["Refund", "Replacement", "Repair", "Refund or replacement, as I choose"], default="Refund"),
            F("deadlineDays", "Days you give them", "number", default=14, lo=7, hi=60)]},
}
def catalog() -> list[dict]:
    return [{"id": k, "title": t["title"], "summary": t["summary"], "who": t["who"]} for k, t in LETTERS.items()]


def spec(letter_id: str) -> dict:
    t = LETTERS.get(letter_id)
    if t is None:
        raise ApiError(404, "NOT_FOUND", "That letter does not exist.")
    return {"id": letter_id, "title": t["title"], "summary": t["summary"], "who": t["who"], "fields": t["fields"],
            "note": "This is a draft made from what you typed, for information. Have a lawyer read it before you send an important letter. Keep a copy and proof of delivery."}


def render(letter_id: str, raw: dict[str, Any], today: date | None = None) -> dict:
    t = LETTERS.get(letter_id)
    if t is None:
        raise ApiError(404, "NOT_FOUND", "That letter does not exist.")
    v = clean_fields(t["fields"], raw, today)
    body = t["build"](v)
    out = [fdate(v["letterDate"]), "", "To:", v["recipientName"]] + ([v["recipientAddress"]] if v.get("recipientAddress") else []) + ["", f"Subject: {body['subject']}", "", "Dear Sir or Madam,", ""]
    for p in body["paragraphs"]:
        out += [p, ""]
    out += ["Yours faithfully,", "", "", v["senderName"], v["senderAddress"]]
    if body.get("enclosures"):
        out += ["", "Enclosures:"] + [f"  {i}. {e}" for i, e in enumerate(body["enclosures"], start=1)]
    return {"id": letter_id, "title": t["title"], "subject": body["subject"], "text": "\n".join(out), "fields": v, "createdAt": datetime.now().isoformat(timespec="seconds")}


def letter_pdf(text: str) -> bytes:
    import pymupdf

    wrapped: list[str] = []
    for ln in text.split("\n"):
        ln = ln.encode("latin-1", "replace").decode("latin-1")                  # the built-in PDF font is Latin-1 only
        while len(ln) > 92:
            cut = ln.rfind(" ", 0, 92)
            cut = cut if cut > 30 else 92
            wrapped.append(ln[:cut])
            ln = ln[cut:].lstrip()
        wrapped.append(ln)
    doc = pymupdf.open()
    rect = pymupdf.Rect(64, 64, 531, 780)
    per_page = 50
    for i in range(0, max(len(wrapped), 1), per_page):
        page = doc.new_page(width=595, height=842)
        page.insert_textbox(rect, "\n".join(wrapped[i:i + per_page]), fontsize=11, fontname="helv")
    doc.set_metadata({"title": "Draft letter", "producer": "LegalMate"})
    out = doc.tobytes()
    doc.close()
    return out
