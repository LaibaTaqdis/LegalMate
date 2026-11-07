"""Runtime settings for the chat engine. Reads environment variables, falling back to backend/.env.

Deliberately independent of the `ingest` package (a deployed server will not ship it).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def load_env(path: Path = BACKEND_DIR / ".env") -> None:
    """Minimal KEY=VALUE loader; real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.split("  #")[0].split("   #")[0].strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    thinking: bool                 # hidden reasoning tokens are billed as output: off by default
    max_calls_per_run: int         # hard cap of LIVE calls per process
    daily_call_cap: int            # hard cap of live calls per calendar day (from the ledger)
    mode: str                      # live | replay (replay never touches the network)
    cache_dir: Path
    ledger_path: Path
    # USD per 1M tokens. ESTIMATES from third-party reports (peak prices); confirm on DeepSeek's pricing page.
    price_in_miss: float
    price_in_hit: float
    price_out: float
    database_url: str
    cache_enabled: bool = True     # the API turns this off: the cache would keep (scrubbed) user questions on the server's disk


def get_settings() -> Settings:
    load_env()
    data = Path(os.environ.get("LEGALMATE_DATA_DIR", BACKEND_DIR / "data"))
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
    if model == "deepseek-v4-flash":          # retired alias (the API now lists deepseek-flash / deepseek-v4-pro)
        model = "deepseek-flash"
    return Settings(
        deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        deepseek_model=model,
        thinking=os.environ.get("DEEPSEEK_THINKING", "off").lower() == "on",
        max_calls_per_run=int(os.environ.get("LLM_MAX_CALLS_PER_RUN", "30")),
        daily_call_cap=int(os.environ.get("LLM_DAILY_CALL_CAP", "2000")),   # 0 = no ceiling
        mode=os.environ.get("LLM_MODE", "live").lower(),
        cache_dir=data / "llm_cache",
        ledger_path=data / "llm_ledger.jsonl",
        price_in_miss=float(os.environ.get("LLM_PRICE_IN", "0.30")),
        price_in_hit=float(os.environ.get("LLM_PRICE_IN_CACHED", "0.03")),
        price_out=float(os.environ.get("LLM_PRICE_OUT", "1.20")),
        database_url=os.environ.get("DATABASE_URL", ""),
        cache_enabled=os.environ.get("LLM_CACHE", "on").lower() != "off",
    )
