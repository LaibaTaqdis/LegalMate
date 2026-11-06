"""The LegalMate API.

    uvicorn app.asgi:app --port 8000          (from backend/, with backend/.env filled in)

`create_app()` takes optional overrides so tests can run it with a throw-away database and a fake chat engine.
"""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import AppSettings, get_app_settings
from .db import Database, migrate
from .errors import body, install_error_handlers
from .ratelimit import RateLimiter
from .routers import auth, chat, documents, users
from .state import AppState, EngineHolder

API_PREFIX = "/api/v1"
MAX_JSON_BYTES = 1_000_000          # nothing in this API sends more than a few KB of JSON; uploads (Phase 5) get their own limit
log = logging.getLogger("legalmate.api")


def create_app(settings: AppSettings | None = None, *, engine=None, db: Database | None = None) -> FastAPI:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = settings or get_app_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = db or Database(s.database_url, max_size=s.db_pool_max)
        database.open()
        applied = migrate(database)
        if applied:
            log.info("database migrated: %s", ", ".join(applied))
        holder = EngineHolder(engine=engine, enabled=s.enable_engine)
        app.state.ctx = AppState(settings=s, db=database, limiter=RateLimiter(), engine=holder,
                                 executor=ThreadPoolExecutor(max_workers=s.engine_concurrency, thread_name_prefix="chat"))
        if s.enable_engine and s.warm_engine and engine is None:
            holder.warm_in_background()
        try:
            yield
        finally:
            app.state.ctx.executor.shutdown(wait=False, cancel_futures=True)
            if db is None:
                database.close()

    production = os.environ.get("APP_ENV", "development").lower() == "production"
    app = FastAPI(title="LegalMate API", version="0.4.0", lifespan=lifespan, docs_url=None if production else "/docs",
                  redoc_url=None, openapi_url=None if production else "/openapi.json")
    install_error_handlers(app)

    app.add_middleware(CORSMiddleware, allow_origins=list(s.cors_origins), allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                       allow_headers=["Authorization", "Content-Type", "Accept", "Accept-Language"],
                       expose_headers=["Retry-After", "Content-Disposition"], max_age=600)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        size = request.headers.get("content-length")
        if size and size.isdigit() and int(size) > MAX_JSON_BYTES and "multipart/form-data" not in request.headers.get("content-type", ""):
            return JSONResponse(body("FILE_TOO_LARGE", "That request is too large."), status_code=413)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")             # API answers contain personal data: never cached
        return response

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def ready(request: Request):
        ctx: AppState = request.app.state.ctx
        db_ok = ctx.db.ping()
        out = {"database": db_ok, "engine": ctx.engine.ready, "engineEnabled": ctx.engine.enabled}
        if ctx.engine.last_error:
            out["engineError"] = ctx.engine.last_error
        return JSONResponse(out, status_code=200 if db_ok else 503)

    for r in (auth.router, users.router, chat.router, documents.router):
        app.include_router(r, prefix=API_PREFIX)
    return app
