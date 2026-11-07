"""DeepSeek client with the safety rails this project needs while developing:

  * disk CACHE keyed by the full request: an identical request is never paid for twice
  * LEDGER (data/llm_ledger.jsonl): every live call with tokens and estimated cost
  * HARD CAPS: max live calls per process and per calendar day; going over raises BudgetExceeded
  * replay mode: cache only, never touches the network (tests, demos)
  * thinking mode OFF by default (hidden reasoning tokens are billed as output)

Nothing here ever logs the API key or the request text beyond a short tag.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import httpx

from .settings import Settings, get_settings


class BudgetExceeded(RuntimeError):
    pass


class CacheMiss(RuntimeError):
    pass


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    usage: dict = field(default_factory=dict)
    cached: bool = False
    cost: float = 0.0
    seconds: float = 0.0


def parse_json(text: str) -> dict:
    """Parse a JSON object out of a model reply (tolerates ```json fences and stray prose)."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        a, b = t.find("{"), t.rfind("}")
        if a >= 0 and b > a:
            return json.loads(t[a:b + 1])
        raise


class DeepSeek:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()
        self.live_calls = 0
        self.cache_hits = 0
        self.cost = 0.0
        self.tokens_in = 0
        self.tokens_out = 0
        self.s.cache_dir.mkdir(parents=True, exist_ok=True)
        self.s.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ budget
    def _calls_today(self) -> int:
        if not self.s.ledger_path.exists():
            return 0
        today = date.today().isoformat()
        n = 0
        for line in self.s.ledger_path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            n += r.get("day") == today and r.get("status") == 200
        return n

    def _check_budget(self) -> None:
        if self.live_calls >= self.s.max_calls_per_run:
            raise BudgetExceeded(f"live call cap for this run reached ({self.s.max_calls_per_run}); raise LLM_MAX_CALLS_PER_RUN on purpose to continue")
        if self.s.daily_call_cap > 0 and self._calls_today() >= self.s.daily_call_cap:
            raise BudgetExceeded(f"daily live call cap reached ({self.s.daily_call_cap}); see data/llm_ledger.jsonl")

    # ------------------------------------------------------------------ the call
    def complete(self, messages: list[dict], *, tag: str, max_tokens: int = 800, temperature: float = 0.1,
                 json_mode: bool = True, thinking: bool | None = None) -> LLMResult:
        thinking = self.s.thinking if thinking is None else thinking
        body = {"model": self.s.deepseek_model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
                "thinking": {"type": "enabled" if thinking else "disabled"}}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        key = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        cache_file = self.s.cache_dir / f"{key}.json"
        if self.s.cache_enabled and cache_file.exists():
            c = json.loads(cache_file.read_text(encoding="utf-8"))
            self.cache_hits += 1
            return LLMResult(c["text"], c.get("usage", {}), cached=True, cost=0.0, seconds=0.0)
        if self.s.mode == "replay":
            raise CacheMiss(f"replay mode: no cached response for tag '{tag}'")
        if not self.s.deepseek_api_key:
            raise LLMError("DEEPSEEK_API_KEY is not set (backend/.env)")
        self._check_budget()

        headers = {"Authorization": f"Bearer {self.s.deepseek_api_key}", "Content-Type": "application/json"}
        t0 = time.time()
        r = None
        for attempt in (1, 2):                                  # one retry on rate limit / server error only
            r = httpx.post(f"{self.s.deepseek_base_url}/chat/completions", headers=headers, json=body, timeout=90)
            if r.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                break
            time.sleep(2.0)
        dt = time.time() - t0
        self._ledger({"tag": tag, "status": r.status_code, "seconds": round(dt, 2), "usage": (r.json().get("usage") if r.status_code == 200 else None)})
        if r.status_code != 200:
            raise LLMError(f"DeepSeek returned {r.status_code}: {r.text[:200]}")
        j = r.json()
        text = j["choices"][0]["message"].get("content") or ""
        usage = j.get("usage", {})
        self.live_calls += 1
        cost = self._cost(usage)
        self.cost += cost
        self.tokens_in += usage.get("prompt_tokens", 0)
        self.tokens_out += usage.get("completion_tokens", 0)
        if self.s.cache_enabled:
            cache_file.write_text(json.dumps({"text": text, "usage": usage, "tag": tag}, ensure_ascii=False), encoding="utf-8")
        return LLMResult(text, usage, cached=False, cost=cost, seconds=dt)

    # ------------------------------------------------------------------ bookkeeping
    def _cost(self, usage: dict) -> float:
        hit = usage.get("prompt_cache_hit_tokens", 0)
        miss = usage.get("prompt_cache_miss_tokens", max(0, usage.get("prompt_tokens", 0) - hit))
        out = usage.get("completion_tokens", 0)
        return (miss * self.s.price_in_miss + hit * self.s.price_in_hit + out * self.s.price_out) / 1e6

    def _ledger(self, rec: dict) -> None:
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "day": date.today().isoformat(),
               "model": self.s.deepseek_model, **rec}
        with open(self.s.ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")

    def summary(self) -> str:
        return (f"DeepSeek this run: {self.live_calls} live call(s), {self.cache_hits} cache hit(s), "
                f"{self.tokens_in} in / {self.tokens_out} out tokens, ~${self.cost:.4f} "
                f"(cap {self.s.max_calls_per_run}/run, {self.s.daily_call_cap}/day; today so far {self._calls_today()})")
