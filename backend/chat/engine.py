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
from typing import Callable

from . import lang as langmod
from . import prompts
from .confidence import score as confidence_score
from .llm import BudgetExceeded, CacheMiss, DeepSeek, LLMError, parse_json
from .pii import scrub
from .plainspeak import plain, plain_answer
from .richtext import cited_ids, strip_markup, to_segments
from .strings import tr
from .verify import verify

DISCLAIMER = tr("disclaimer", "en")          # the English texts, kept as constants; every message uses tr(key, language)
EMERGENCY = tr("emergency", "en")
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


BUSY_TEXT = tr("busy", "en")


def _failure_text(e: Exception, fallback_key: str, lang: str = "en") -> tuple[str, str]:
    """(reason, text) for a failed model call: a spent budget is reported as 'busy', anything else as 'error'."""
    if isinstance(e, BudgetExceeded):
        return "busy", tr("busy", lang)
    return "error", tr(fallback_key, lang)


def _has_urdu(text: str) -> bool:
    return bool(langmod._URDU_LETTER.search(text or ""))


def _in_language(text: str, lang: str) -> bool:
    """Is a short model-written text in the script the user asked for? (Urdu script for 'ur', Latin letters otherwise.)"""
    return _has_urdu(text) == (lang == "ur")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ChatEngine:
    def __init__(self, kb, llm: DeepSeek, *, n_passages: int = 10, per_doc_cap: int = 4, per_section_cap: int = 1, max_clarify_rounds: int = 1,
                 route_acts: bool = False, rescue: bool = False, doc_chars: int = 6000):   # rescue: measured 0 of 2 on hard cases, +8 s: off until proven   # measured: no gain on the gold set (see reports/analyser_eval.md notes), kept as an option
        self.kb, self.llm = kb, llm
        self.n_passages, self.per_doc_cap, self.per_section_cap, self.max_clarify_rounds = n_passages, per_doc_cap, per_section_cap, max_clarify_rounds
        self.route_acts, self._router, self.rescue_enabled, self.doc_chars = route_acts, None, rescue, doc_chars

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
            act = r["act_title"].lower()          # by Act title, so a Federal and a Punjab copy (or two parts) of one section count once
            sec = (act, r["section_label"])
            if per_doc.get(act, 0) >= self.per_doc_cap or per_section.get(sec, 0) >= self.per_section_cap:
                continue
            per_doc[act] = per_doc.get(act, 0) + 1
            per_section[sec] = per_section.get(sec, 0) + 1
            out.append(r)
            if len(out) >= self.n_passages:
                break
        return out

    # ------------------------------------------------------------------ the whole turn
    def respond(self, text: str, *, history: list[dict] | None = None, profile: dict | None = None, language: str = "auto",
                attachment_text: str | None = None, on_status: Callable[[str], None] | None = None) -> dict:
        """`on_status` (optional) is called with 'understanding', 'searching_sources', 'writing_answer' as the turn progresses.
        `language`: "auto" (answer in the language the user wrote in), or "en" / "ur" / "ur-roman" to force one."""
        status = on_status or (lambda s: None)
        t0 = time.time()
        history = history or []
        meta: dict = {"calls_live_before": self.llm.live_calls}
        clean, removed = scrub(text)
        if removed:
            meta["pii_removed"] = removed
        hist = [{"role": h["role"], "content": scrub(h["content"])[0], "kind": h.get("kind")} for h in history]
        lang = langmod.resolve(language, clean, hist)               # by code, from what was typed; the analyser's guess refines it below

        if GREETING.match(clean) and not attachment_text:
            return self._done(self._info("greeting", tr("greeting", lang), lang=lang), meta, t0, None)
        status("understanding")
        try:
            analysis = self.analyse(clean, hist, profile, lang, bool(attachment_text))
        except (BudgetExceeded, CacheMiss, LLMError) as e:
            reason, text = _failure_text(e, "error", lang)
            return self._done(self._info(reason, text, lang=lang), meta, t0, None, error=f"{type(e).__name__}: {e}")
        lang = langmod.resolve(language, clean, hist, analysis.get("language"))
        meta["language"] = lang
        meta["analysis"] = {k: analysis[k] for k in ("intent", "language", "jurisdiction", "emergency", "needs_clarification", "search_queries", "tag")}
        conv = {"title": analysis["title"], "tag": analysis["tag"]}
        emergency = tr("emergency", lang) if analysis["emergency"] else None

        if analysis["intent"] in ("greeting", "out_of_scope", "unclear"):
            reply = plain(analysis.get("reply") or "")
            if not reply or not _in_language(reply, lang):         # the model answered in another language than the user's: use the fixed text
                reply = tr("greeting" if analysis["intent"] == "greeting" else "out_of_scope", lang)
            return self._done(self._info(analysis["intent"], reply, emergency, lang=lang), meta, t0, conv)
        if analysis["needs_clarification"]:
            return self._done(self._clarify(analysis["questions"], lang), meta, t0, conv)

        jur = norm_jurisdiction(analysis["jurisdiction"]) or norm_jurisdiction((profile or {}).get("province")) \
            or norm_jurisdiction((profile or {}).get("city"))
        status("searching_sources")
        t1 = time.time()
        passages = self.retrieve(analysis["search_queries"], jur)
        meta["retrieval_seconds"] = round(time.time() - t1, 3)
        if not passages:
            return self._done(self._info("no_source", tr("no_source", lang), lang=lang), meta, t0, conv)
        answer_lang = lang
        doc_note = scrub(attachment_text or "")[0][: self.doc_chars]          # identity numbers in a document never leave
        msgs = prompts.answer_messages(clean, history=hist, profile_line=profile_line(profile), answer_language=answer_lang,
                                       passages=passages, document_note=doc_note)
        status("writing_answer")
        try:
            ans = parse_json(self.llm.complete(msgs, tag="answer", max_tokens=1400).text)
        except (BudgetExceeded, CacheMiss, LLMError, ValueError) as e:
            reason, text = _failure_text(e, "error_answer", lang)
            return self._done(self._info(reason, text, lang=lang), meta, t0, conv, error=f"{type(e).__name__}: {e}")
        if self.rescue_enabled and not bool(ans.get("sufficient", True)):
            ans, passages = self._second_look(clean, ans, passages, analysis, hist, profile, answer_lang, jur, doc_note, status, meta)
        message = self._build_answer(ans, passages, answer_lang, emergency, meta)
        return self._done(message, meta, t0, conv)

    def _second_look(self, question, ans, passages, analysis, hist, profile, answer_lang, jur, doc_note, status, meta):
        """The first answer said the law was not found. Ask the model which Act really governs the step described, search again with
        that and answer again. Two more model calls, only on this failure path; falls back to the first answer if it does not help."""
        status("searching_deeper")
        try:
            found = [f"{p['act_title']} {p['section_label']}" for p in passages]
            r = parse_json(self.llm.complete(prompts.rescue_messages(question, tried=analysis["search_queries"], found=found,
                                                                    profile_line=profile_line(profile)), tag="rescue", max_tokens=250).text)
            qs = [q for q in (r.get("search_queries") or []) if isinstance(q, str) and q.strip()][:3] if isinstance(r, dict) else []
            if not qs:
                return ans, passages
            p2 = self.retrieve(qs, jur)
            if not p2:
                return ans, passages
            status("writing_answer")
            ans2 = parse_json(self.llm.complete(prompts.answer_messages(question, history=hist, profile_line=profile_line(profile),
                                                                       answer_language=answer_lang, passages=p2, document_note=doc_note),
                                                tag="answer", max_tokens=1400).text)
        except (BudgetExceeded, CacheMiss, LLMError, ValueError):
            return ans, passages
        meta["second_look"] = {"queries": qs, "helped": bool(ans2.get("sufficient", True))}
        return (ans2, p2) if ans2.get("sufficient", True) else (ans, passages)

    # ------------------------------------------------------------------ message builders
    def _build_answer(self, ans: dict, passages: list[dict], lang: str, emergency: str | None, meta: dict) -> dict:
        ans = plain_answer(ans)                  # no talk about databases, passages or 'the text available to me'
        rep = verify(ans, passages)
        meta["verify"] = {"issues": rep.issues, "cited_fraction": round(rep.cited_fraction, 2), "quote_rate": round(rep.quote_rate, 2),
                          "unverified_sections": rep.unverified_sections, "unverified_numbers": rep.unverified_numbers}
        body = f"{ans.get('intro', '')} {ans.get('law', '')}"
        if body.strip() and not _in_language(body, lang):            # recorded, so a drift from the user's language shows in the logs
            meta["language_mismatch"] = lang
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
                note = tr("note_repealed", lang, scope=p.get("status_scope") or tr("some_places", lang))
            elif p.get("amended_by_titles"):
                note = tr("note_amended", lang, titles="; ".join(p["amended_by_titles"][:3]))
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
            "intro": to_segments(fix(ans.get("intro", "")), ids), "lawTitle": tr("law_title", lang),
            "law": to_segments(fix(ans.get("law", "")), ids),
            "steps": [to_segments(fix(s), ids) for s in (ans.get("steps") or [])][:5],
            "important": important, "outro": strip_markup(fix(ans.get("outro", ""))),
            "sources": sources, "confidence": conf, "followUps": [str(x) for x in (ans.get("follow_ups") or [])][:2],
            "disclaimer": tr("disclaimer", lang), "feedback": None,
            "content": strip_markup(fix(ans.get("intro", "") + " " + ans.get("law", ""))),
        }

    @staticmethod
    def _info(reason: str, text: str, emergency: str | None = None, lang: str = "en") -> dict:
        return {"role": "assistant", "kind": "info", "reason": reason, "createdAt": _now(), "language": lang,
                "text": ((emergency + " ") if emergency else "") + text, "content": text, "confidence": None}

    @staticmethod
    def _clarify(questions: list[dict], lang: str = "en") -> dict:
        intro = tr("clarify_intro", lang)
        return {"role": "assistant", "kind": "clarify", "createdAt": _now(), "language": lang, "intro": intro, "questions": questions, "confidence": None,
                "content": intro + " " + " ".join(q["text"] for q in questions)}

    def _done(self, message: dict, meta: dict, t0: float, conv: dict | None, error: str | None = None) -> dict:
        meta["llm_calls_this_turn"] = self.llm.live_calls - meta.pop("calls_live_before", 0)
        meta["seconds"] = round(time.time() - t0, 2)
        if error:
            meta["error"] = error[:200]
        return {"message": message, "conversation": conv, "meta": meta}
