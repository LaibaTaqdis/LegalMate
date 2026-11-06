"""Passwords (argon2id), access tokens (short-lived JWT) and refresh tokens (random, stored only as a hash)."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()                       # argon2id with the library's current defaults
# Verified against when the account does not exist, so "unknown email" and "wrong password" take equally long.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, stored: str | None) -> bool:
    try:
        return _hasher.verify(stored or _DUMMY_HASH, password) and stored is not None
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(stored: str) -> bool:
    return _hasher.check_needs_rehash(stored)


# ---- access tokens -------------------------------------------------------------------------------------------
def make_access_token(user_id: str, role: str, secret: str, minutes: int, session_id: str | None = None) -> str:
    """`sid` is the login session (refresh-token family) this token belongs to, so one device can be signed out without the others."""
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user_id, "role": role, "sid": session_id, "typ": "access", "iat": now, "exp": now + timedelta(minutes=minutes)},
                      secret, algorithm="HS256")


def decode_access_token(token: str, secret: str) -> dict | None:
    """The token's claims, or None if it is expired, forged or not an access token."""
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], leeway=5, options={"require": ["exp", "sub", "iat"]})
    except jwt.PyJWTError:
        return None
    return claims if claims.get("typ") == "access" else None


# ---- refresh tokens ------------------------------------------------------------------------------------------
def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
