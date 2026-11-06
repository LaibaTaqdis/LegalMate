"""User rows <-> the API's User object, onboarding profile, and token issuing."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .db import Database
from .schemas import ProfileIn
from .security import hash_token, make_access_token, new_refresh_token

USER_COLS = ("id, email, name, password_hash, phone, cnic_last4, city, address, role, status, preferred_language, profile, "
             "profile_completed_at, created_at")
ROLE_LABELS = {"client": "Citizen Account", "lawyer": "Lawyer Account", "admin": "Administrator"}


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds") if dt else None


def _display_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    national = phone[3:] if phone.startswith("+92") else phone
    return f"{national[:3]} {national[3:]}".strip()


def user_out(row: dict) -> dict:
    cnic_last = row.get("cnic_last4")
    return {
        "id": str(row["id"]), "name": row["name"], "email": row["email"],
        "phone": _display_phone(row.get("phone")), "phoneCountryCode": "+92",
        "cnic": f"*****-***{cnic_last[:3]}-{cnic_last[3:]}" if cnic_last and len(cnic_last) == 4 else None, "cnicVerified": False,
        "city": row.get("city"), "address": row.get("address"), "avatarUrl": None,
        "role": row["role"], "roleLabel": ROLE_LABELS.get(row["role"], "Account"),
        "preferredLanguage": row["preferred_language"], "profileCompleted": row.get("profile_completed_at") is not None,
        "joinedAt": iso(row.get("created_at")),
    }


# ---- onboarding profile --------------------------------------------------------------------------------------
PROFILE_FIELDS = ("province", "city", "userType", "employmentStatus", "roles", "ageBand", "maritalStatus", "language", "interests")


def profile_out(row: dict) -> dict:
    p = row.get("profile") or {}
    out = {k: p.get(k) for k in PROFILE_FIELDS}
    out["roles"], out["interests"] = p.get("roles") or [], p.get("interests") or []
    out["language"] = p.get("language") or row["preferred_language"]
    out["completed"] = row.get("profile_completed_at") is not None
    return out


def engine_profile(row: dict) -> dict:
    """What the chat engine may know about the user. Deliberately no name, CNIC, phone, email or address."""
    p = row.get("profile") or {}
    return {
        "province": p.get("province"), "city": p.get("city") or row.get("city"), "userType": p.get("userType"),
        "employmentStatus": p.get("employmentStatus"), "role": ", ".join(p.get("roles") or []) or None,
        "ageBand": p.get("ageBand"), "maritalStatus": p.get("maritalStatus"),
        "preferredLanguage": {"en": "English", "ur": "Urdu", "both": "English and Urdu"}.get(p.get("language") or row["preferred_language"]),
    }


def save_profile(db: Database, user_id: str, data: ProfileIn) -> dict:
    from psycopg.types.json import Jsonb

    profile = {k: v for k, v in data.model_dump().items() if v not in (None, [], "")}
    lang = profile.get("language")
    row = db.one(
        f"update app.users set profile = %s, city = coalesce(%s, city), preferred_language = coalesce(%s, preferred_language), "
        f"profile_completed_at = now(), updated_at = now() where id = %s returning {USER_COLS}",
        [Jsonb(profile), profile.get("city"), lang, user_id])
    return row


# ---- sessions (refresh-token families) -----------------------------------------------------------------------
def issue_tokens(state, user: dict, *, remember: bool, user_agent: str | None, ip: str | None, family_id: str | None = None) -> dict:
    """Create a refresh token (new login session, or the next link of an existing one) and a matching access token."""
    s = state.settings
    refresh = new_refresh_token()
    days = s.refresh_days_remember if remember else s.refresh_days_session
    expires = datetime.now(timezone.utc) + timedelta(days=days)
    row = state.db.one(
        "insert into app.refresh_tokens (user_id, family_id, token_hash, remember, user_agent, ip, expires_at) "
        "values (%s, coalesce(%s::uuid, gen_random_uuid()), %s, %s, %s, %s, %s) returning family_id",
        [user["id"], family_id, hash_token(refresh), remember, (user_agent or "")[:200], ip, expires])
    access = make_access_token(str(user["id"]), user["role"], s.jwt_secret, s.access_ttl_minutes, str(row["family_id"]))
    return {"accessToken": access, "refreshToken": refresh}


LOGIN_ID_PHONE = re.compile(r"^[+\d][\d\s\-]{8,}$")
