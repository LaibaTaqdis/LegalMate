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


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def load_doc_settings() -> "DocSettings":
    d = DocSettings()
    return DocSettings(
        max_upload_mb=max(1, _int("MAX_UPLOAD_MB", d.max_upload_mb)), max_pages=max(1, _int("MAX_PAGES", d.max_pages)),
        max_text_chars=max(1000, _int("MAX_TEXT_CHARS", d.max_text_chars)),
        docx_max_uncompressed_mb=max(1, _int("DOCX_MAX_UNCOMPRESSED_MB", d.docx_max_uncompressed_mb)),
        ocr_enabled=_bool("OCR_ENABLED", d.ocr_enabled), ocr_dpi=min(400, max(72, _int("OCR_DPI", d.ocr_dpi))),
        ocr_min_page_chars=_int("OCR_MIN_PAGE_CHARS", d.ocr_min_page_chars), ocr_concurrency=max(1, _int("OCR_CONCURRENCY", d.ocr_concurrency)),
        ocr_langs=tuple(x.strip().lower() for x in os.environ.get("OCR_LANGS", ",".join(d.ocr_langs)).split(",") if x.strip()) or d.ocr_langs,
        ocr_urdu_model=("v4" if os.environ.get("OCR_URDU_MODEL", "").strip().lower() == "v4" else "v5"),
        ocr_urdu_min_score=min(1.0, max(0.0, _float("OCR_URDU_MIN_SCORE", d.ocr_urdu_min_score))), ocr_urdu_trigger=min(1.0, max(0.0, _float("OCR_URDU_TRIGGER", d.ocr_urdu_trigger))),
        ocr_script_min=min(1.0, max(0.0, _float("OCR_SCRIPT_MIN", d.ocr_script_min))),
        ocr_min_confidence=_float("OCR_MIN_CONFIDENCE", d.ocr_min_confidence), max_image_pixels=max(1_000_000, _int("MAX_IMAGE_PIXELS", d.max_image_pixels)),
        docs_per_user=_int("DOCS_PER_USER", d.docs_per_user), uploads_per_hour=_int("UPLOADS_PER_HOUR", d.uploads_per_hour),
        doc_retention_days=_int("DOC_RETENTION_DAYS", d.doc_retention_days),
        attachments_per_message=max(1, min(5, _int("ATTACHMENTS_PER_MESSAGE", d.attachments_per_message))),
        chat_doc_chars=max(500, _int("CHAT_DOC_CHARS", d.chat_doc_chars)),
        analysis_stale_minutes=max(1, _int("ANALYSIS_STALE_MINUTES", d.analysis_stale_minutes)),
    )


@dataclass(frozen=True)
class DocSettings:
    """Everything about uploaded documents and their analysis. Every value can be changed with an environment variable (see .env.example)."""
    max_upload_mb: int = 10               # MAX_UPLOAD_MB      largest accepted file
    max_pages: int = 10                   # MAX_PAGES          PDF pages accepted (images count as one page)
    max_text_chars: int = 200_000         # MAX_TEXT_CHARS     extracted text kept per document (the rest is cut, the user is told)
    docx_max_uncompressed_mb: int = 50    # DOCX_MAX_UNCOMPRESSED_MB  zip-bomb guard for Word files
    ocr_enabled: bool = True              # OCR_ENABLED        read scanned pages and photos (needs rapidocr-onnxruntime)
    ocr_dpi: int = 200                    # OCR_DPI            resolution a scanned PDF page is rendered at before reading
    ocr_min_page_chars: int = 40          # OCR_MIN_PAGE_CHARS a PDF page with less text than this is treated as a scan
    ocr_concurrency: int = 1              # OCR_CONCURRENCY    OCR jobs at once (each uses a lot of CPU and memory)
    ocr_langs: tuple[str, ...] = ("en", "ur")  # OCR_LANGS     scripts the OCR reads: en = English and digits, ur = Urdu (Arabic script). "en" alone switches Urdu off
    ocr_urdu_model: str = "v5"            # OCR_URDU_MODEL     recognition model generation for Urdu: v5 (measured better) or v4
    ocr_urdu_min_score: float = 0.50      # OCR_URDU_MIN_SCORE a line read as Urdu must score at least this to be kept
    ocr_urdu_trigger: float = 0.20        # OCR_URDU_TRIGGER   run the Urdu reader when more than this share of the page's ink was not read as English
    ocr_script_min: float = 0.40          # OCR_SCRIPT_MIN     share of Arabic-script letters a line needs to count as Urdu
    ocr_min_confidence: float = 0.60      # OCR_MIN_CONFIDENCE below this average the user is warned that the scan is hard to read
    max_image_pixels: int = 40_000_000    # MAX_IMAGE_PIXELS   photos larger than this are refused (decompression-bomb guard)
    docs_per_user: int = 25               # DOCS_PER_USER      stored documents per user (0 = no limit)
    uploads_per_hour: int = 30            # UPLOADS_PER_HOUR   per user (0 = no limit)
    doc_retention_days: int = 30          # DOC_RETENTION_DAYS extracted text is deleted after this many days (0 = keep until the user deletes it)
    attachments_per_message: int = 3      # ATTACHMENTS_PER_MESSAGE  files attached to one chat question
    chat_doc_chars: int = 6000            # CHAT_DOC_CHARS     characters of a document shown to the assistant for one chat question
    analysis_stale_minutes: int = 15      # ANALYSIS_STALE_MINUTES   a job still "running" after this long (server restarted) is marked failed

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


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
    max_msgs_per_hour: int = 0            # per user; 0 = no limit
    max_msgs_per_day: int = 0             # per user; 0 = no limit
    engine_concurrency: int = 4           # answers computed at the same time (CPU + DeepSeek)
    history_messages: int = 6             # earlier messages shown to the model
    db_pool_max: int = 5
    docs: DocSettings = field(default_factory=DocSettings)
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
        max_msgs_per_hour=_int("CHAT_MSGS_PER_HOUR", 0),
        max_msgs_per_day=_int("CHAT_MSGS_PER_DAY", 0),
        engine_concurrency=_int("ENGINE_CONCURRENCY", 4),
        db_pool_max=_int("DB_POOL_MAX", 5),
        docs=load_doc_settings(),
    )
