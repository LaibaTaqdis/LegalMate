"""The chat engine: one user message in, one frontend-shaped message out. At most TWO DeepSeek calls per message:

    greeting / thanks ............ 0 calls (answered locally)
    vague question ............... 1 call  (analyser -> clarifying questions with tappable options)
    out of scope ................. 1 call  (analyser -> polite redirect)
    legal question ............... 2 calls (analyser -> retrieval -> answerer -> code verification)

Retrieval and verification are plain code (no LLM). The engine never raises for ordinary failures: it returns an `info`
message instead, so the UI always has something sensible to show.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone

from . import prompts
from .confidence import score as confidence_score
from .llm import BudgetExceeded, CacheMiss, DeepSeek, LLMError, parse_json
from .pii import scrub
from .richtext import cited_ids, strip_markup, to_segments
from .verify import verify

DISCLAIMER = "This is general legal information based on the texts in our database, not legal advice. Laws change: please verify with a qualified lawyer."
EMERGENCY = ("If you or someone else is in immediate danger, call Police on 15 or Rescue on 1122 now. "
             "(Numbers shown for Pakistan; confirm local helplines in the Emergency section.)")
GREETING = re.compile(r"^\s*(hi|hello|hey|salam|salaam|assalam[\w\s\-']*|aoa|good\s(morning|afternoon|evening)|thanks?(\s+you)?|thank\s*you|shukriya|jazak\w*)\W*$", re.I)
INTENTS = {"legal_question", "follow_up", "document_question", "greeting", "out_of_scope", "unclear"}
TAGS = {"Property Law", "Family Law", "Criminal Law", "Labour & Employment", "Contract Law", "Consumer Rights",
        "Constitutional Rights", "Civil Procedure", "Cyber Law", "Other"}


def profile_line(profile: dict | None) -> str:
    """Only non-identifying facts reach the model: never name, CNIC, phone, email or address."""
    if not profile:
        return ""
    keys = ("province", "city", "userType", "employmentStatus", "role", "ageBand", "maritalStatus", "preferredLanguage")
    return "; ".join(f"{k}={profile[k]}" for k in keys if profile.get(k))


def norm_jurisdiction(value: str | None) -> str | None:
    """Map free text from the profile or the analyser to the knowledge base's jurisdictions. 'Federal' means no preference."""
    v = (value or "").strip().lower()
    if not v:
        return None
    if "islamabad" in v or v in ("ict", "ict (islamabad)"):
        return "ICT"
    if "punjab" in v or v in ("lahore", "faisalabad", "rawalpindi", "multan", "gujranwala", "sialkot", "bahawalpur", "sargodha"):
        return "Punjab"
    return None


def _alias_norm(t: str) -> str:
    t = re.sub(r"[^a-z0-9 ]+", " ", t.lower().replace("-", " "))
    return re.sub(r"\s+", " ", t).strip()


class ActRouter:
    """Finds which Acts a query talks about. The analyser usually names the Act ("Court Fees Act 1870 ad valorem ..."); when
    that Act is in our database we also search *inside* it, so passages from other Acts cannot crowd it out."""

    def __init__(self, docs: list[tuple]):
        self.aliases: list[tuple[str, str]] = []
        for doc_id, title, jur, is_amendment in docs:
            if is_amendment:
                continue
            base = re.sub(r",?\s*\(?(?:18|19|20)\d{2}\)?\s*$", "", title).strip()
            names = {_alias_norm(base)}
            names.add(_alias_norm(re.sub(r"^(?:punjab|islamabad capital territory|pakistan|west pakistan)\s+", "", base, flags=re.I)))
            for n in names:
                if len(n) >= 10 and len(n.split()) >= 2:              # "contract act", not a lone generic word
                    self.aliases.append((" " + n + " ", doc_id))

    def match(self, text: str) -> list[str]:
        t = " " + _alias_norm(text) + " "
        return sorted({d for alias, d in self.aliases if alias in t})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ChatEngine:
    def __init__(self, kb, llm: DeepSeek, *, n_passages: int = 8, per_doc_cap: int = 3, per_section_cap: int = 2, max_clarify_rounds: int = 1,
                 route_acts: bool = False):   # measured: no gain on the gold set (see reports/analyser_eval.md notes), kept as an option
        self.kb, self.llm = kb, llm
        self.n_passages, self.per_doc_cap, self.per_section_cap, self.max_clarify_rounds = n_passages, per_doc_cap, per_section_cap, max_clarify_rounds
        self.route_acts, self._router = route_acts, None

    # ------------------------------------------------------------------ step 1
    def analyse(self, message: str, history: list[dict], profile: dict | None, ui_language: str, has_document: bool) -> dict:
        msgs = prompts.analyser_messages(message, history=history, profile_line=profile_line(profile),
                                         ui_language=ui_language, has_document=has_document)
        try:
            a = parse_json(self.llm.complete(msgs, tag="analyse", max_tokens=500).text)
        except (ValueError, KeyError):
            a = {}
        a["intent"] = a.get("intent") if a.get("intent") in INTENTS else "legal_question"
        qs = [q for q in (a.get("search_queries") or []) if isinstance(q, str) and q.strip()][:3]
        a["search_queries"] = qs or [message[:200]]
        a["tag"] = a.get("tag") if a.get("tag") in TAGS else "Other"
        a["title"] = (a.get("title") or message[:40]).strip()[:60]
        a["jurisdiction"] = a.get("jurisdiction") if a.get("jurisdiction") in ("Punjab", "ICT", "Federal") else None
        a["emergency"] = bool(a.get("emergency"))
        rounds = sum(1 for h in history if h.get("kind") == "clarify")
        qs_ok = []
        for q in (a.get("questions") or [])[:2]:
            if isinstance(q, dict) and q.get("text"):
                opts = [str(o) for o in (q.get("options") or [])][:4]
                qs_ok.append({"id": f"q{len(qs_ok) + 1}", "text": str(q["text"]), "options": opts})
        a["questions"] = qs_ok
        a["needs_clarification"] = bool(a.get("needs_clarification")) and bool(qs_ok) and rounds < self.max_clarify_rounds \
            and a["intent"] in ("legal_question", "follow_up", "document_question")
        return a

    # ------------------------------------------------------------------ retrieval (code only)
    def retrieve(self, queries: list[str], jur: str | None) -> list[dict]:
        merged: dict[str, dict] = {}
        lists = [self.kb.search(q, jur, k=12) for q in queries]
        if self.route_acts:
            if self._router is None:
                self._router = ActRouter(self.kb.docs)
            act_docs = self._router.match(" ".join(queries))
            if act_docs:                                              # the analyser named an Act we hold: search inside it too
                for q in queries[1:3]:
                    lists.append(self.kb.search_in_docs(q, act_docs, k=5))
        for rows in lists:
            for rank, row in enumerate(rows, start=1):
                m = merged.setdefault(row["chunk_id"], {**row, "rrf": 0.0})
                m["rrf"] += 1.0 / (60 + rank)
                m["cosine"] = max(m["cosine"], row["cosine"])
        ranked = sorted(merged.values(), key=lambda r: -r["rrf"])
        out, per_doc, per_section = [], {}, {}
        for r in ranked:
            sec = (r["doc_id"], r["section_label"])
            if per_doc.get(r["doc_id"], 0) >= self.per_doc_cap or per_section.get(sec, 0) >= self.per_section_cap:
                continue
            per_doc[r["doc_id"]] = per_doc.get(r["doc_id"], 0) + 1
            per_section[sec] = per_section.get(sec, 0) + 1
            out.append(r)
            if len(out) >= self.n_passages:
                break
        return out

    # ------------------------------------------------------------------ the whole turn
    def respond(self, text: str, *, history: list[dict] | None = None, profile: dict | None = None, language: str = "en",
                attachment_text: str | None = None) -> dict:
        t0 = time.time()
        history = history or []
        meta: dict = {"calls_live_before": self.llm.live_calls}
        clean, removed = scrub(text)
        if removed:
            meta["pii_removed"] = removed
        hist = [{"role": h["role"], "content": scrub(h["content"])[0], "kind": h.get("kind")} for h in history]

        if GREETING.match(clean) and not attachment_text:
            return self._done(self._info("greeting", "Hello! I can explain Pakistani law in plain language, with the sources I used. "
                                                      "Ask me about tenancy, family, criminal, labour, contract or property matters, or upload a document."), meta, t0, None)
        try:
            analysis = self.analyse(clean, hist, profile, language, bool(attachment_text))
        except (BudgetExceeded, CacheMiss, LLMError) as e:
            return self._done(self._info("error", f"I can't answer right now ({type(e).__name__}). Please try again later."), meta, t0, None, error=str(e))
        meta["analysis"] = {k: analysis[k] for k in ("intent", "language", "jurisdiction", "emergency", "needs_clarification", "search_queries", "tag")}
        conv = {"title": analysis["title"], "tag": analysis["tag"]}
        emergency = EMERGENCY if analysis["emergency"] else None

        if analysis["intent"] in ("greeting", "out_of_scope", "unclear"):
            reply = analysis.get("reply") or "I can only help with questions about Pakistani law. Could you tell me about your legal question?"
            return self._done(self._info(analysis["intent"], reply, emergency), meta, t0, conv)
        if analysis["needs_clarification"]:
            return self._done(self._clarify(analysis["questions"]), meta, t0, conv)

        jur = norm_jurisdiction(analysis["jurisdiction"]) or norm_jurisdiction((profile or {}).get("province")) \
            or norm_jurisdiction((profile or {}).get("city"))
        t1 = time.time()
        passages = self.retrieve(analysis["search_queries"], jur)
        meta["retrieval_seconds"] = round(time.time() - t1, 3)
        if not passages:
            return self._done(self._info("no_source", "I could not find a law in my database that matches this question. "
                                                      "Please rephrase it, or consult a qualified lawyer."), meta, t0, conv)
        answer_lang = "ur" if (language == "ur" or analysis.get("language") == "ur") else "en"
        doc_note = (attachment_text or "")[:3000]
        msgs = prompts.answer_messages(clean, history=hist, profile_line=profile_line(profile), answer_language=answer_lang,
                                       passages=passages, document_note=doc_note)
        try:
            ans = parse_json(self.llm.complete(msgs, tag="answer", max_tokens=1400).text)
        except (BudgetExceeded, CacheMiss, LLMError, ValueError) as e:
            return self._done(self._info("error", "I could not prepare an answer just now. Please try again."), meta, t0, conv, error=str(e))
        message = self._build_answer(ans, passages, answer_lang, emergency, meta)
        return self._done(message, meta, t0, conv)

    # ------------------------------------------------------------------ message builders
    def _build_answer(self, ans: dict, passages: list[dict], lang: str, emergency: str | None, meta: dict) -> dict:
        rep = verify(ans, passages)
        meta["verify"] = {"issues": rep.issues, "cited_fraction": round(rep.cited_fraction, 2), "quote_rate": round(rep.quote_rate, 2),
                          "unverified_sections": rep.unverified_sections, "unverified_numbers": rep.unverified_numbers}
        valid = set(rep.cited_ids)
        order: list[int] = []                                   # renumber sources by first appearance: 1, 2, 3...
        for f in [ans.get("intro", ""), ans.get("law", "")] + list(ans.get("steps") or []) + [ans.get("important", ""), ans.get("outro", "")]:
            for i in cited_ids(f):
                if i in valid and i not in order:
                    order.append(i)
        remap = {old: new for new, old in enumerate(order, start=1)}

        def fix(t: str) -> str:
            return re.sub(r"\[\[(\d+)\]\]", lambda m: f"[[{remap[int(m.group(1))]}]]" if int(m.group(1)) in remap else "", t or "")

        ids = set(remap.values())
        cited = [passages[i - 1] for i in order]
        sources = []
        for old in order:
            p = passages[old - 1]
            q = rep.quotes.get(old, {"quote": "", "verified": False})
            note = None
            if p.get("legal_status") == "repealed":
                note = f"Marked repealed in {p.get('status_scope') or 'some jurisdictions'} in our database. Verify before relying on it."
            elif p.get("amended_by_titles"):
                note = "Amended later by " + "; ".join(p["amended_by_titles"][:3]) + ". Amendments are not merged into this text."
            sources.append({
                "id": remap[old], "title": p["act_title"],
                "section": (p["section_label"] + (f" - {p['heading']}" if p.get("heading") else ""))[:110],
                "type": "Rule" if p.get("doc_type") == "rules" else "Act",
                "quote": f"“{q['quote']}”", "quoteVerified": q["verified"],
                "url": (p.get("source_urls") or [None])[0], "pages": f"pp. {p['page_start']}-{p['page_end']}" if p["page_start"] != p["page_end"] else f"p. {p['page_start']}",
                "jurisdiction": p["jurisdiction"], "status": p["legal_status"], "note": note})
        sufficient = bool(ans.get("sufficient", True))
        conf = confidence_score(cited, rep, sufficient, len(passages))
        important = strip_markup(fix(ans.get("important", "")))
        if emergency:
            important = (emergency + " " + important).strip()
        return {
            "role": "assistant", "kind": "answer", "createdAt": _now(), "language": lang, "sufficient": sufficient,
            "intro": to_segments(fix(ans.get("intro", "")), ids), "lawTitle": ans.get("law_title") or "What the law says",
            "law": to_segments(fix(ans.get("law", "")), ids),
            "steps": [to_segments(fix(s), ids) for s in (ans.get("steps") or [])][:5],
            "important": important, "outro": strip_markup(fix(ans.get("outro", ""))),
            "sources": sources, "confidence": conf, "followUps": [str(x) for x in (ans.get("follow_ups") or [])][:2],
            "disclaimer": DISCLAIMER, "feedback": None,
            "content": strip_markup(fix(ans.get("intro", "") + " " + ans.get("law", ""))),
        }

    @staticmethod
    def _info(reason: str, text: str, emergency: str | None = None) -> dict:
        return {"role": "assistant", "kind": "info", "reason": reason, "createdAt": _now(),
                "text": ((emergency + " ") if emergency else "") + text, "content": text, "confidence": None}

    @staticmethod
    def _clarify(questions: list[dict]) -> dict:
        intro = "To give you accurate guidance I need a little more information. Tap an option or type your own answer:"
        return {"role": "assistant", "kind": "clarify", "createdAt": _now(), "intro": intro, "questions": questions, "confidence": None,
                "content": intro + " " + " ".join(q["text"] for q in questions)}

    def _done(self, message: dict, meta: dict, t0: float, conv: dict | None, error: str | None = None) -> dict:
        meta["llm_calls_this_turn"] = self.llm.live_calls - meta.pop("calls_live_before", 0)
        meta["seconds"] = round(time.time() - t0, 2)
        if error:
            meta["error"] = error[:200]
        return {"message": message, "conversation": conv, "meta": meta}
