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
        ocr_enabled=_bool("OCR_ENABLED", d.ocr_enabled), ocr_warm=_bool("OCR_WARM", d.ocr_warm), ocr_defer_chat=_bool("OCR_DEFER_CHAT", d.ocr_defer_chat),
        pending_hours=max(1, _int("PENDING_DOC_HOURS", d.pending_hours)), ocr_dpi=min(400, max(72, _int("OCR_DPI", d.ocr_dpi))),
        ocr_min_page_chars=_int("OCR_MIN_PAGE_CHARS", d.ocr_min_page_chars), ocr_concurrency=max(1, _int("OCR_CONCURRENCY", d.ocr_concurrency)),
        ocr_langs=tuple(x.strip().lower() for x in os.environ.get("OCR_LANGS", ",".join(d.ocr_langs)).split(",") if x.strip()) or d.ocr_langs,
        ocr_urdu_model=("v4" if os.environ.get("OCR_URDU_MODEL", "").strip().lower() == "v4" else "v5"),
        ocr_urdu_min_score=min(1.0, max(0.0, _float("OCR_URDU_MIN_SCORE", d.ocr_urdu_min_score))), ocr_urdu_trigger=min(1.0, max(0.0, _float("OCR_URDU_TRIGGER", d.ocr_urdu_trigger))),
        ocr_script_min=min(1.0, max(0.0, _float("OCR_SCRIPT_MIN", d.ocr_script_min))),
        ocr_min_confidence=_float("OCR_MIN_CONFIDENCE", d.ocr_min_confidence), max_image_pixels=max(1_000_000, _int("MAX_IMAGE_PIXELS", d.max_image_pixels)),
        docs_per_user=_int("DOCS_PER_USER", d.docs_per_user), uploads_per_hour=_int("UPLOADS_PER_HOUR", d.uploads_per_hour),
        doc_retention_days=_int("DOC_RETENTION_DAYS", d.doc_retention_days), analysis_retention_days=_int("ANALYSIS_RETENTION_DAYS", d.analysis_retention_days),
        attachments_per_message=max(1, min(5, _int("ATTACHMENTS_PER_MESSAGE", d.attachments_per_message))),
        chat_doc_chars=max(500, _int("CHAT_DOC_CHARS", d.chat_doc_chars)),
        analysis_quick_chars=max(1000, _int("ANALYSIS_QUICK_CHARS", d.analysis_quick_chars)),
        analysis_detailed_chars=max(1000, _int("ANALYSIS_DETAILED_CHARS", d.analysis_detailed_chars)),
        analysis_quick_tokens=max(300, _int("ANALYSIS_QUICK_TOKENS", d.analysis_quick_tokens)),
        analysis_detailed_tokens=max(300, _int("ANALYSIS_DETAILED_TOKENS", d.analysis_detailed_tokens)),
        analysis_max_docs=max(1, _int("ANALYSIS_MAX_DOCS", d.analysis_max_docs)), analysis_concurrency=max(1, _int("ANALYSIS_CONCURRENCY", d.analysis_concurrency)),
        analysis_per_user_running=max(1, _int("ANALYSIS_PER_USER_RUNNING", d.analysis_per_user_running)), analysis_per_day=_int("ANALYSIS_PER_DAY", d.analysis_per_day),
        analysis_stale_minutes=max(1, _int("ANALYSIS_STALE_MINUTES", d.analysis_stale_minutes)),
        analysis_page_size=min(50, max(1, _int("ANALYSIS_PAGE_SIZE", d.analysis_page_size))),
        vault_trash_days=max(1, _int("VAULT_TRASH_DAYS", d.vault_trash_days)), vault_max_items=max(0, _int("VAULT_MAX_ITEMS", d.vault_max_items)),
        vault_page_size=min(100, max(1, _int("VAULT_PAGE_SIZE", d.vault_page_size))), vault_max_notes=max(1, _int("VAULT_MAX_NOTES", d.vault_max_notes)),
        vault_note_chars=min(5000, max(50, _int("VAULT_NOTE_CHARS", d.vault_note_chars))),
        law_refs_enabled=_bool("LAW_REFS_ENABLED", d.law_refs_enabled), law_refs_max=min(20, max(1, _int("LAW_REFS_MAX", d.law_refs_max))),
        law_refs_per_clause=min(4, max(1, _int("LAW_REFS_PER_CLAUSE", d.law_refs_per_clause))),
        law_refs_quote_chars=min(1200, max(80, _int("LAW_REFS_QUOTE_CHARS", d.law_refs_quote_chars))),
    )


@dataclass(frozen=True)
class DocSettings:
    """Everything about uploaded documents and their analysis. Every value can be changed with an environment variable (see .env.example)."""
    max_upload_mb: int = 10               # MAX_UPLOAD_MB      largest accepted file
    max_pages: int = 10                   # MAX_PAGES          PDF pages accepted (images count as one page)
    max_text_chars: int = 200_000         # MAX_TEXT_CHARS     extracted text kept per document (the rest is cut, the user is told)
    docx_max_uncompressed_mb: int = 50    # DOCX_MAX_UNCOMPRESSED_MB  zip-bomb guard for Word files
    ocr_enabled: bool = True              # OCR_ENABLED        read scanned pages and photos (needs rapidocr-onnxruntime)
    ocr_warm: bool = True                 # OCR_WARM          load and prime the OCR readers when the server starts, so the first photo is not slow
    ocr_defer_chat: bool = True           # OCR_DEFER_CHAT    a photo attached in chat is accepted at once and read while the answer is prepared (0 = read at upload)
    pending_hours: int = 24               # PENDING_DOC_HOURS a photo that was attached but never sent with a question is removed after this long
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
    analysis_retention_days: int = 90     # ANALYSIS_RETENTION_DAYS (0 = keep)
    attachments_per_message: int = 3      # ATTACHMENTS_PER_MESSAGE  files attached to one chat question
    chat_doc_chars: int = 6000            # CHAT_DOC_CHARS     characters of a document shown to the assistant for one chat question
    analysis_quick_chars: int = 15_000    # ANALYSIS_QUICK_CHARS     document text read by a quick analysis
    analysis_detailed_chars: int = 40_000 # ANALYSIS_DETAILED_CHARS  document text read by a detailed analysis
    analysis_quick_tokens: int = 2800     # ANALYSIS_QUICK_TOKENS    longest answer the model may write (quick). Measured: 1,700-2,300 used; 1,800 cut an answer off
    analysis_detailed_tokens: int = 4800  # ANALYSIS_DETAILED_TOKENS (detailed)
    analysis_max_docs: int = 3            # ANALYSIS_MAX_DOCS        documents analysed together
    analysis_concurrency: int = 2         # ANALYSIS_CONCURRENCY     analyses running at once
    analysis_per_user_running: int = 2    # ANALYSIS_PER_USER_RUNNING
    analysis_per_day: int = 0             # ANALYSIS_PER_DAY         per user (0 = no limit)
    analysis_stale_minutes: int = 15      # ANALYSIS_STALE_MINUTES   a job still "running" after this long (server restarted) is marked failed
    analysis_page_size: int = 10          # ANALYSIS_PAGE_SIZE       rows per page in the analysis history (the browser may ask for fewer, never more than 50)
    law_refs_enabled: bool = True         # LAW_REFS_ENABLED         show "Related laws" (reviewed table, real text from the law library) on an analysis
    law_refs_max: int = 8                 # LAW_REFS_MAX            laws shown in the box at most
    law_refs_per_clause: int = 2          # LAW_REFS_PER_CLAUSE     laws linked from one clause (the table may allow a few more candidates)
    law_refs_quote_chars: int = 260       # LAW_REFS_QUOTE_CHARS    characters of the law's own wording shown for each
    vault_trash_days: int = 30            # VAULT_TRASH_DAYS        a saved item in the Trash is deleted for good after this many days
    vault_max_items: int = 500            # VAULT_MAX_ITEMS         saved items per user, Trash included (0 = no limit)
    vault_page_size: int = 24             # VAULT_PAGE_SIZE         items per page in the Vault list
    vault_max_notes: int = 50             # VAULT_MAX_NOTES         notes per saved item
    vault_note_chars: int = 2000          # VAULT_NOTE_CHARS        characters in one note

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
