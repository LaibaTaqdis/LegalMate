"""API settings from environment variables (backend/.env locally, the host's settings when deployed)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from chat.settings import load_env


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class AppSettings:
    database_url: str
    jwt_secret: str
    access_ttl_minutes: int = 15
    refresh_days_remember: int = 30
    refresh_days_session: int = 1
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    trust_proxy: bool = False             # only behind a proxy you control (Cloudflare tunnel, Render): then X-Forwarded-For is trusted
    enable_engine: bool = True            # False: auth/profile/conversations only (no knowledge base, no DeepSeek)
    warm_engine: bool = True              # load the knowledge base in the background at start-up
    max_msgs_per_hour: int = 30           # per user
    max_msgs_per_day: int = 100           # per user
    engine_concurrency: int = 4           # answers computed at the same time (CPU + DeepSeek)
    history_messages: int = 6             # earlier messages shown to the model
    db_pool_max: int = 5
    extra: dict = field(default_factory=dict)


def get_app_settings() -> AppSettings:
    load_env()
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < 32 or secret.lower().startswith("change-me"):
        raise RuntimeError("JWT_SECRET must be a random string of at least 32 characters (backend/.env). "
                           "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\"")
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (Supabase session-pooler connection string in backend/.env)")
    origins = tuple(o.strip().rstrip("/") for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()) or AppSettings.cors_origins
    return AppSettings(
        database_url=url, jwt_secret=secret,
        access_ttl_minutes=_int("ACCESS_TOKEN_MINUTES", 15),
        cors_origins=origins,
        trust_proxy=_bool("TRUST_PROXY", False),
        enable_engine=_bool("ENABLE_ENGINE", True),
        warm_engine=_bool("WARM_ENGINE", True),
        max_msgs_per_hour=_int("CHAT_MSGS_PER_HOUR", 30),
        max_msgs_per_day=_int("CHAT_MSGS_PER_DAY", 100),
        engine_concurrency=_int("ENGINE_CONCURRENCY", 4),
        db_pool_max=_int("DB_POOL_MAX", 5),
    )
