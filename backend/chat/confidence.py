"""Confidence indicator for the UI (0-100 each). A HEURISTIC, not a probability: it combines how well the sources match the
question, how well the answer is backed by checked citations, and how current the cited law is likely to be.

  relevance : mean cosine of the CITED passages, mapped 0.60 -> 0 and 0.82 -> 100 (real questions scored ~0.77 median)
  agreement : 50% share of legal sentences with a citation, 30% share of verbatim-verified quotes, 20% no unverified
              section numbers / figures
  recency   : repealed 20; amended later (amendments are not merged) 65; otherwise by age of the Act (newer = higher)
  overall   : 0.5 relevance + 0.3 agreement + 0.2 recency, capped at 45 when the model says the sources are insufficient
The UI shows 80+ as High and 60-79 as Medium.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .verify import Report


def _clip(x: float) -> float:
    return max(0.0, min(100.0, x))


def recency_of(p: dict, current_year: int | None = None) -> float:
    if p.get("legal_status") == "repealed":
        return 20.0
    if p.get("amended_by_titles"):
        return 65.0
    y = p.get("year") or 0
    if y >= 2000:
        return 92.0
    if y >= 1947:
        return 85.0
    return 78.0 if y else 70.0


def score(cited: list[dict], report: Report, sufficient: bool, n_checked: int) -> dict:
    if not cited:
        return {"score": 0, "relevance": 0, "agreement": 0, "recency": 0, "checked": n_checked,
                "verifiedAt": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    cos = sum(p.get("cosine", 0.0) for p in cited) / len(cited)
    relevance = _clip((cos - 0.60) / (0.82 - 0.60) * 100)
    clean = 1.0 if not (report.unverified_sections or report.unverified_numbers) else (0.5 if len(report.unverified_sections) + len(report.unverified_numbers) <= 2 else 0.0)
    agreement = _clip(100 * (0.5 * report.cited_fraction + 0.3 * report.quote_rate + 0.2 * clean))
    rs = [recency_of(p) for p in cited]
    recency = 0.5 * min(rs) + 0.5 * (sum(rs) / len(rs))
    overall = 0.5 * relevance + 0.3 * agreement + 0.2 * recency
    if not sufficient:
        overall = min(overall, 45.0)
    return {"score": round(overall), "relevance": round(relevance), "agreement": round(agreement), "recency": round(recency),
            "checked": n_checked, "verifiedAt": datetime.now(timezone.utc).isoformat(timespec="seconds")}
