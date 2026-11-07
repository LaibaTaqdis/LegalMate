"""Objects shared by all requests (created once at start-up, reachable as request.app.state.ctx)."""
from __future__ import annotations

import dataclasses
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

from .config import AppSettings
from .db import Database
from .errors import ApiError
from .ratelimit import RateLimiter

log = logging.getLogger("legalmate.engine")


def build_engine(doc_chars: int = 6000):
    """The real chat engine: DeepSeek client + the Supabase knowledge base. Slow (loads the keyword index and the embedding model)."""
    from chat.engine import ChatEngine
    from chat.llm import DeepSeek
    from chat.settings import get_settings
    from retrieval.kb import KnowledgeBase

    s = get_settings()
    s = dataclasses.replace(
        s,
        # The disk cache would keep users' (scrubbed) questions on the server forever; off unless LLM_CACHE is set on purpose.
        cache_enabled=os.environ.get("LLM_CACHE", "off").lower() != "off",
        # A server runs for days: the per-run cap meant for scripts would stop it. The per-day cap (from the ledger) is the real guard.
        max_calls_per_run=s.max_calls_per_run if "LLM_MAX_CALLS_PER_RUN" in os.environ else (s.daily_call_cap or 10**9),
    )
    t0 = time.time()
    kb = KnowledgeBase(s.database_url)
    log.info("knowledge base ready in %.1fs (%d chunks)", time.time() - t0, len(kb.lex))
    return ChatEngine(kb, DeepSeek(s), doc_chars=doc_chars)


class EngineHolder:
    """Builds the engine on first use (or in the background at start-up) and hands out the same instance afterwards.
    If building fails (Supabase paused, no internet) the app keeps running and chat answers 503 until a retry succeeds."""

    RETRY_AFTER_S = 30

    def __init__(self, factory: Callable | None = None, engine=None, enabled: bool = True):
        self._engine, self._factory, self.enabled = engine, factory or build_engine, enabled
        self._lock = threading.Lock()
        self._failed_at = 0.0
        self.last_error: str | None = None

    @property
    def ready(self) -> bool:
        return self._engine is not None

    def get(self):
        if self._engine is not None:
            return self._engine
        if not self.enabled:
            raise ApiError(503, "UNAVAILABLE", "The legal assistant is switched off on this server.")
        with self._lock:
            if self._engine is not None:
                return self._engine
            if time.time() - self._failed_at < self.RETRY_AFTER_S:
                raise ApiError(503, "UNAVAILABLE", "LegalMate's law library is temporarily unavailable. Please try again in a minute.")
            try:
                self._engine = self._factory()
                self.last_error = None
            except Exception as e:                                   # noqa: BLE001 - reported, not hidden
                self._failed_at = time.time()
                self.last_error = f"{type(e).__name__}: {e}"[:300]
                log.exception("could not start the chat engine")
                raise ApiError(503, "UNAVAILABLE", "LegalMate's law library is starting up or temporarily unavailable. Please try again in a minute.")
        return self._engine

    def warm_in_background(self) -> None:
        def _go() -> None:
            try:
                self.get()
            except ApiError:
                pass
        threading.Thread(target=_go, name="engine-warmup", daemon=True).start()


@dataclass
class AppState:
    settings: AppSettings
    db: Database
    limiter: RateLimiter
    engine: EngineHolder
    executor: ThreadPoolExecutor
    analysis_executor: ThreadPoolExecutor
    inflight: set = field(default_factory=set)               # user ids with an answer being computed
    inflight_lock: threading.Lock = field(default_factory=threading.Lock)
