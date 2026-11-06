"""Sign up, sign in, token refresh, sign out. No OTP step: accounts are usable immediately."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import psycopg.errors
from fastapi import APIRouter, Depends, Request, Response

from ..deps import current_user, get_state
from ..errors import ApiError, unauthorized
from ..ratelimit import client_ip
from ..schemas import LoginIn, LogoutIn, RefreshIn, RegisterIn, normalize_phone
from ..security import hash_password, hash_token, needs_rehash, verify_password
from ..state import AppState
from ..users_repo import USER_COLS, issue_tokens, user_out

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("legalmate.auth")

FAIL_LIMIT, FAIL_WINDOW = 8, 15 * 60          # failed sign-ins per account / per address in 15 minutes
GRACE_SECONDS = 10                            # a just-rotated refresh token being replayed is a race between tabs, not theft


@router.post("/register", status_code=201)
def register(body: RegisterIn, request: Request, state: AppState = Depends(get_state)):
    ip = client_ip(request, state.settings.trust_proxy)
    state.limiter.check(f"register:{ip}", 6, 3600, "Too many accounts created from this connection. Please try again later.")
    try:
        user = state.db.one(
            f"insert into app.users (email, name, password_hash, phone, cnic_last4, preferred_language, accepted_terms_at) "
            f"values (%s, %s, %s, %s, %s, %s, now()) returning {USER_COLS}",
            [body.email, body.fullName, hash_password(body.password), body.phone, body.cnic.replace('-', '')[-4:] if body.cnic else None, body.preferredLanguage])
    except psycopg.errors.UniqueViolation as e:
        which = "phone" if "phone" in (e.diag.constraint_name or "") else "email"
        raise ApiError(409, "CONFLICT", f"This {which} is already registered. Try signing in instead.", {"field": which})
    tokens = issue_tokens(state, user, remember=True, user_agent=request.headers.get("user-agent"), ip=ip)
    return {"user": user_out(user), **tokens}


def _find_account(state: AppState, identifier: str) -> dict | None:
    ident = identifier.strip()
    if "@" in ident:
        return state.db.one(f"select {USER_COLS} from app.users where lower(email) = %s", [ident.lower()])
    try:
        phone = normalize_phone(ident)
    except ValueError:
        return None
    return state.db.one(f"select {USER_COLS} from app.users where phone = %s", [phone])


@router.post("/login")
def login(body: LoginIn, request: Request, state: AppState = Depends(get_state)):
    ip = client_ip(request, state.settings.trust_proxy)
    ident_key = f"loginfail:acct:{body.identifier.strip().lower()}"
    ip_key = f"loginfail:ip:{ip}"
    wait = max(state.limiter.blocked(ident_key, FAIL_LIMIT, FAIL_WINDOW), state.limiter.blocked(ip_key, FAIL_LIMIT * 3, FAIL_WINDOW))
    if wait:
        raise ApiError(429, "RATE_LIMITED", "Too many failed sign-in attempts. Please wait a few minutes and try again.",
                       {"retryAfterSeconds": wait}, headers={"Retry-After": str(wait)})

    user = _find_account(state, body.identifier)
    if not verify_password(body.password, user["password_hash"] if user else None):
        state.limiter.add(ident_key)
        state.limiter.add(ip_key)
        raise unauthorized("The email or password is incorrect.", "INVALID_CREDENTIALS")
    if user["status"] != "active":
        raise ApiError(403, "FORBIDDEN", "This account has been suspended. Please contact support.")
    if user["role"] != body.role:
        raise ApiError(403, "FORBIDDEN", f"This account is not a {body.role} account. Choose the right tab on the sign-in screen.")

    state.limiter.clear(ident_key)
    new_hash = hash_password(body.password) if needs_rehash(user["password_hash"]) else None
    state.db.run("update app.users set last_login_at = now(), password_hash = coalesce(%s, password_hash) where id = %s", [new_hash, user["id"]])
    tokens = issue_tokens(state, user, remember=body.remember, user_agent=request.headers.get("user-agent"), ip=ip)
    return {"user": user_out(user), **tokens}


@router.post("/refresh")
def refresh(body: RefreshIn, request: Request, state: AppState = Depends(get_state)):
    """Swap a refresh token for a new pair. The old token stops working. Presenting an old one again revokes the whole login session."""
    h = hash_token(body.refreshToken)
    with state.db.tx() as c:
        rt = c.execute("select * from app.refresh_tokens where token_hash = %s for update", [h]).fetchone()
        if rt is None:
            raise unauthorized("Please sign in again.", "INVALID_REFRESH")
        now = datetime.now(timezone.utc)
        if rt["revoked_at"] is not None:
            if (now - rt["revoked_at"]).total_seconds() > GRACE_SECONDS:
                c.execute("update app.refresh_tokens set revoked_at = coalesce(revoked_at, now()) where family_id = %s", [rt["family_id"]])
                log.warning("refresh token reuse detected; session %s revoked", rt["family_id"])
            raise unauthorized("Please sign in again.", "INVALID_REFRESH")
        if rt["expires_at"] <= now:
            raise unauthorized("Your session has expired. Please sign in again.", "TOKEN_EXPIRED")
        user = c.execute(f"select {USER_COLS} from app.users where id = %s", [rt["user_id"]]).fetchone()
        if user is None or user["status"] != "active":
            raise unauthorized("This account is not available.")
        c.execute("update app.refresh_tokens set revoked_at = now(), last_used_at = now() where id = %s", [rt["id"]])
    return issue_tokens(state, user, remember=rt["remember"], user_agent=request.headers.get("user-agent"),
                        ip=client_ip(request, state.settings.trust_proxy), family_id=str(rt["family_id"]))


@router.post("/logout", status_code=204)
def logout(body: LogoutIn, state: AppState = Depends(get_state)):
    """Ends this login session. Works even when the access token has already expired."""
    if body.refreshToken:
        state.db.run("update app.refresh_tokens set revoked_at = coalesce(revoked_at, now()) "
                     "where family_id = (select family_id from app.refresh_tokens where token_hash = %s)", [hash_token(body.refreshToken)])
    return Response(status_code=204)


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user_out(user)


@router.post("/forgot-password", status_code=204)
def forgot_password(request: Request, state: AppState = Depends(get_state)):
    """Always 204 (never reveals whether an account exists). No email is sent yet: there is no mail service in this version."""
    state.limiter.check(f"forgot:{client_ip(request, state.settings.trust_proxy)}", 5, 3600)
    return Response(status_code=204)
