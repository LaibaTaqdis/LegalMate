"""In-memory sliding-window rate limiter (per process). Enough for one server; a multi-server deployment would need Redis.

Daily per-user chat limits do not rely on this: they are counted from the messages table, so they survive restarts.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from .errors import ApiError


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()

    def check(self, key: str, limit: int, window_s: float, message: str = "Too many attempts. Please wait a moment and try again.") -> None:
        """Count one hit for `key`; raise 429 if there were already `limit` hits in the last `window_s` seconds."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window_s:
                q.popleft()
            if len(q) >= limit:
                retry = max(1, int(q[0] + window_s - now) + 1)
                raise ApiError(429, "RATE_LIMITED", message, {"retryAfterSeconds": retry}, headers={"Retry-After": str(retry)})
            q.append(now)
            if now - self._last_sweep > 300:                      # forget idle keys so memory cannot grow without bound
                self._last_sweep = now
                for k in [k for k, v in self._hits.items() if not v or v[-1] <= now - 3600]:
                    del self._hits[k]

    def blocked(self, key: str, limit: int, window_s: float) -> int:
        """Seconds until `key` may try again (0 = not blocked). Does not count a hit; pair with add() to count failures only."""
        now = time.monotonic()
        with self._lock:
            q = self._hits.get(key)
            if not q:
                return 0
            while q and q[0] <= now - window_s:
                q.popleft()
            return max(1, int(q[0] + window_s - now) + 1) if len(q) >= limit else 0

    def add(self, key: str) -> None:
        with self._lock:
            self._hits[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request, trust_proxy: bool) -> str:
    """The caller's address. X-Forwarded-For is only believed when the app runs behind a proxy we control (TRUST_PROXY=1)."""
    if trust_proxy:
        fwd = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if fwd:
            return fwd
    return request.client.host if request.client else "unknown"
