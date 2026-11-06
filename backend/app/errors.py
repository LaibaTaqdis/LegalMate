"""One error shape for the whole API: {"error": {"code", "message", "details"}} (see frontend/BACKEND_API.md section 1.3)."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("legalmate.api")

_CODES = {400: "VALIDATION_ERROR", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "NOT_FOUND", 409: "CONFLICT",
          413: "FILE_TOO_LARGE", 415: "UNSUPPORTED_TYPE", 422: "UNPROCESSABLE", 429: "RATE_LIMITED", 501: "NOT_IMPLEMENTED",
          503: "UNAVAILABLE"}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None, headers: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details, self.headers = status, code, message, details, headers


def unauthorized(message: str = "Please sign in again.", code: str = "UNAUTHORIZED") -> ApiError:
    return ApiError(401, code, message, headers={"WWW-Authenticate": "Bearer"})


def not_found(what: str = "That item") -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what} was not found.")


def body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def _friendly(err: dict) -> tuple[str, str | None]:
    loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
    field = loc[-1] if loc else None
    msg = err.get("msg", "Invalid value")
    msg = msg.removeprefix("Value error, ")
    if err.get("type") == "missing":
        msg = "This field is required."
    return (f"{field}: {msg}" if field and not msg.startswith(field) else msg), field


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, e: ApiError):
        return JSONResponse(body(e.code, e.message, e.details), status_code=e.status, headers=e.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        first = e.errors()[0] if e.errors() else {}
        message, field = _friendly(first)
        return JSONResponse(body("VALIDATION_ERROR", message, {"field": field} if field else None), status_code=400)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        code = _CODES.get(e.status_code, "INTERNAL")
        message = "That address does not exist." if e.status_code in (404, 405) else (e.detail if isinstance(e.detail, str) else "Request failed.")
        return JSONResponse(body(code, message), status_code=e.status_code, headers=getattr(e, "headers", None))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, e: Exception):
        log.exception("Unhandled error on %s %s", request.method, request.url.path)     # details stay in the server log only
        return JSONResponse(body("INTERNAL", "Something went wrong on our side. Please try again."), status_code=500)
