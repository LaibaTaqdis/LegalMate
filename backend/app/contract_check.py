"""A quick contract check: which usual clauses are there, and which warning phrases does the text contain.

It is a plain wording check (no model, no law lookup), so it is instant, free, and cannot invent anything: every finding is a phrase that is
(or is not) in the text, shown with its surroundings. It reads English wording; a mostly Urdu text is refused with a pointer to the full analysis.
It is NOT a legal review: a clause can be present and still be unfair, and a contract can be fine without every clause.
"""
from __future__ import annotations

import re

_FLAGS = re.I | re.S

# clause key -> (label, pattern, why it matters, question to ask the chat)
CLAUSES: dict[str, tuple[str, str, str, str]] = {
    "parties": ("Who the parties are", r"\bbetween\b|\bparty of the (first|second)\b|\b(first|second) party\b|hereinafter|\bthe parties\b",
                "A contract should name each side clearly, with full names and addresses, so it is clear who is bound.",
                "What should a contract in Pakistan say about who the parties are, and why does it matter?"),
    "scope": ("What is being provided (scope or duties)", r"scope of (work|services)|\bservices\b|deliverables|description of (goods|work|services)|job description|duties|the premises",
              "Without a clear description of the work, goods or duties, each side can later say the other did not do what was agreed.",
              "Why should a contract describe the work or goods clearly, and what can I do if it does not?"),
    "payment": ("Price and payment terms", r"payment|\bfees?\b|\bprice\b|invoice|remuneration|salary|\brent\b|consideration|\bpkr\b|\brs\.?\s*\d",
                "The amount, the due date and the way of paying should be written down. Missing payment terms are the most common source of disputes.",
                "What should the payment terms of a contract include, and what can I do if payment terms are missing?"),
    "term": ("How long it lasts (term and start date)", r"term of|effective date|commenc|duration|period of|valid for|expire|\bfrom\b.{0,40}\bto\b",
             "A start date and an end date (or how long it runs) tell both sides when the duties begin and finish.",
             "Why should a contract state its start date and duration?"),
    "termination": ("How it can be ended (termination and notice)", r"terminat|notice period|cancel|end this agreement",
                    "Each side should know how to end the contract and how much notice to give. Without it, ending a contract can become a dispute.",
                    "What should a contract say about termination and notice, and what applies if it says nothing?"),
    "liability": ("Responsibility for loss (liability or damages)", r"liabilit|indemnif|damages|compensat",
                  "This says who pays if something goes wrong. A missing or one-sided clause can leave you carrying the whole risk.",
                  "How does liability for loss work in a contract in Pakistan, and what is a fair limit?"),
    "confidentiality": ("Keeping information private (confidentiality)", r"confidential|non-?disclosure|\bnda\b|proprietary information",
                        "Important if you share business information, prices, customers or ideas.",
                        "When should a contract include a confidentiality clause?"),
    "dispute": ("How disputes are settled", r"arbitrat|dispute|jurisdiction|mediation|\bcourts?\b",
                "A contract should say how a disagreement is handled (talks, arbitration, or which court) so you do not argue about that as well.",
                "How should a contract say disputes will be settled, and how does arbitration work in Pakistan?"),
    "law": ("Which law applies", r"governing law|governed by|laws? of pakistan|applicable law|laws? of the islamic republic",
            "It should say that Pakistani law applies, so there is no argument about which country's law decides the dispute.",
            "Why should a contract say which law governs it?"),
    "force_majeure": ("Events beyond anyone's control (force majeure)", r"force majeure|act of god|beyond (the )?(reasonable )?control",
                      "Covers floods, strikes or other events that stop a side from performing. Useful for supply and service contracts.",
                      "What is a force majeure clause and when does a contract need one?"),
    "ip": ("Who owns the work (intellectual property)", r"intellectual property|copyright|ownership of|work product|all rights",
           "Matters for content, software, designs or anything created for you. Without it, the creator may keep the rights.",
           "Who owns the copyright in work made for a client or employer in Pakistan, and how should a contract deal with it?"),
    "amendment": ("How changes are made", r"amend|variation|modif|alteration",
                  "Changes should be agreed in writing by both sides, so nobody can change the deal alone.",
                  "How can a contract be changed after it is signed, and should changes be in writing?"),
    "stamp": ("Stamp paper or stamp duty", r"stamp paper|stamp duty|stamped|non-?judicial|e-?stamp",
              "Some agreements need stamp duty to be paid to be accepted as evidence. Check which applies to yours.",
              "Which agreements need stamp paper in Pakistan, and what happens if it is not used?"),
    "signatures": ("Signatures and witnesses", r"signature|signed|in witness whereof|witness(es)?\b|cnic",
                   "Both sides should sign, and important agreements are usually witnessed. An unsigned draft is hard to enforce.",
                   "How should a contract be signed and witnessed in Pakistan so it can be proved?"),
}

# which clauses a kind of contract is expected to have (the rest are shown as 'good to have')
TYPES: dict[str, dict] = {
    "general": {"label": "General business agreement", "expected": ["parties", "scope", "payment", "term", "termination", "dispute", "law", "signatures"]},
    "employment": {"label": "Job or internship contract", "expected": ["parties", "scope", "payment", "term", "termination", "confidentiality", "dispute", "signatures"]},
    "rental": {"label": "Rental or lease agreement", "expected": ["parties", "scope", "payment", "term", "termination", "stamp", "dispute", "signatures"]},
    "service": {"label": "Supplier, customer or service contract", "expected": ["parties", "scope", "payment", "term", "termination", "liability", "dispute", "law", "signatures"]},
    "partnership": {"label": "Partnership or loan agreement", "expected": ["parties", "scope", "payment", "term", "termination", "liability", "dispute", "law", "stamp", "signatures"]},
}

# warning phrases: key -> (label, pattern, severity, why it matters, question)
FLAGS: dict[str, tuple[str, str, str, str, str]] = {
    "one_sided_exit": ("One side can end it at will", r"sole discretion|at any time (and )?without (prior )?(notice|cause|reason)|terminat\w+ (this agreement )?(at any time )?without (any )?(notice|cause|reason)",
                       "high", "If only one side can end the contract without notice or reason, the other side has no security.",
                       "My contract says the other side can end it at its sole discretion or without notice. Is that allowed under Pakistani law and what can I do?"),
    "unilateral_change": ("One side can change the terms", r"reserves? the right to (amend|change|modify|vary|alter)|may (amend|modify|vary|change) .{0,60}(unilaterally|at any time|without)",
                          "high", "A deal one side can rewrite alone is not really a deal. Changes should need both sides' written agreement.",
                          "My contract lets the other side change its terms at any time. Is that valid in Pakistan and what are my options?"),
    "waiver": ("You give up your rights or claims", r"waive[sd]? (all|any) (right|claim|remed)|irrevocabl\w+ waive|renounce\w* (all|any) (right|claim)",
               "high", "Giving up all claims in advance can leave you without a remedy even if the other side breaks the contract.",
               "My contract says I waive all my rights or claims. Is such a clause valid in Pakistan?"),
    "blank_cheque": ("Blank, undated or security cheque", r"blank cheque|undated cheque|security cheque|post-?dated cheque",
                     "high", "Handing over a blank or security cheque can be misused. Be very careful with what you sign and hand over.",
                     "What are the risks of giving a blank or security cheque in Pakistan?"),
    "one_sided_arbitrator": ("Arbitrator chosen by one side", r"arbitrat\w+.{0,80}(appointed|nominated|chosen|selected) by (the )?(company|employer|first party|lessor|landlord|owner)",
                             "high", "If one side picks the arbitrator, the process may not be fair.",
                             "My contract lets the other side choose the arbitrator. Is that fair and what can I do?"),
    "auto_renew": ("Renews by itself", r"automatic\w* renew|auto-?renew|renew\w* automatically|deemed (to be )?renewed",
                   "medium", "You may be bound for another period unless you cancel in time. Note the notice date.",
                   "My contract renews automatically. How can I end it and what notice do I need to give?"),
    "penalty": ("Penalty, forfeiture or late fee", r"penalt|forfeit|liquidated damages|late (fee|charge|payment)|per day of delay",
                "medium", "Check that the amount is fair and that it applies to both sides.",
                "My contract has a penalty or forfeiture clause. How does the law treat penalty clauses in Pakistan?"),
    "non_compete": ("Restriction on working elsewhere", r"non-?compete|restraint of trade|shall not (engage|work|be employed).{0,80}(competitor|similar|same)",
                    "medium", "Check how long it lasts, where it applies and what it covers. Wide restrictions may not be enforceable.",
                    "Is a non-compete clause enforceable in Pakistan?"),
    "foreign_law": ("Foreign law or courts", r"laws? of (england|the uk|united kingdom|the uae|dubai|singapore|new york|california|delaware)|courts? of (london|dubai|singapore|england|new york)",
                    "medium", "A foreign law or court makes a dispute costly and hard for you. Ask whether Pakistani law can apply instead.",
                    "My contract says a foreign law or court applies. What are the risks and can Pakistani law apply instead?"),
    "non_refundable": ("Non-refundable payment", r"non-?refundable|advance payment|payment in advance",
                       "medium", "Money paid up front and not returnable is lost if the other side does not deliver. Check what you get in return.",
                       "My contract says an advance payment is non-refundable. Is that valid and how can I protect myself?"),
    "blanks": ("Blanks or unfinished terms", r"_{4,}|\[\s*\]|\btbd\b|to be (decided|determined|agreed|filled)",
               "medium", "Fill every blank before you sign. Unfinished terms are a common cause of disputes.",
               "What should I do about blanks or 'to be agreed' terms in a contract?"),
}


def _snippet(text: str, m: re.Match, width: int = 90) -> str:
    a, b = max(0, m.start() - width), min(len(text), m.end() + width)
    s = re.sub(r"\s+", " ", text[a:b]).strip()
    return ("…" if a > 0 else "") + s + ("…" if b < len(text) else "")


def _urdu_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if "؀" <= c <= "ۿ") / len(letters)


def meta() -> dict:
    return {"types": [{"key": k, "label": v["label"]} for k, v in TYPES.items()],
            "limits": "A wording check only: it shows which usual clauses and warning phrases are in the text. It does not tell you whether the contract is fair or legal."}


def check(text: str, contract_type: str = "general") -> dict:
    if contract_type not in TYPES:
        contract_type = "general"
    words = len(text.split())
    if words < 40:
        return {"ok": False, "reason": "short", "message": "There is too little text to check. Upload the full contract (a PDF, Word file or clear photo)."}
    if _urdu_share(text) > 0.3:
        return {"ok": False, "reason": "urdu", "message": "This check reads English wording. For a contract in Urdu, use the full AI analysis, which reads Urdu."}
    expected = TYPES[contract_type]["expected"]
    clauses = []
    for key, (label, pat, why, question) in CLAUSES.items():
        m = re.search(pat, text, _FLAGS)
        clauses.append({"key": key, "label": label, "found": bool(m), "expected": key in expected, "snippet": _snippet(text, m) if m else None,
                        "why": why, "question": question})
    flags = []
    for key, (label, pat, sev, why, question) in FLAGS.items():
        m = re.search(pat, text, _FLAGS)
        if m:
            flags.append({"key": key, "label": label, "severity": sev, "snippet": _snippet(text, m), "why": why, "question": question})
    missing = [c for c in clauses if c["expected"] and not c["found"]]
    score = len(missing) + sum(3 if f["severity"] == "high" else 2 for f in flags)
    level = "Low" if score <= 2 else "Medium" if score <= 6 else "High"
    return {"ok": True, "type": contract_type, "typeLabel": TYPES[contract_type]["label"], "words": words, "level": level, "score": score,
            "clauses": clauses, "flags": flags,
            "summary": {"expected": len(expected), "foundExpected": len(expected) - len(missing), "missingExpected": len(missing), "flags": len(flags)},
            "limits": meta()["limits"]}
