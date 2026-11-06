"""The signed-in user: account details, onboarding profile (context for the chatbot), password."""
from __future__ import annotations

import psycopg.errors
from fastapi import APIRouter, Depends, Request, Response

from ..deps import current_user, get_state
from ..errors import ApiError
from ..schemas import ChangePasswordIn, ProfileIn, UserPatch, clean_text
from ..security import hash_password, verify_password
from ..state import AppState
from ..users_repo import USER_COLS, profile_out, save_profile, user_out

router = APIRouter(prefix="/users/me", tags=["users"])


@router.get("")
def get_me(user: dict = Depends(current_user)):
    return user_out(user)


@router.patch("")
def update_me(body: UserPatch, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """name, email, phone, city, address. (Email and phone are not re-verified yet: there is no mail/SMS service in this version.)"""
    sent = body.model_fields_set
    cols = {"name": body.name, "email": body.email, "phone": body.phone, "city": clean_text(body.city, 60), "address": clean_text(body.address, 200)}
    changes = {k: v for k, v in cols.items() if k in sent and not (k in ("name", "email") and v is None)}
    if not changes:
        return user_out(user)
    sets = ", ".join(f"{k} = %s" for k in changes)
    try:
        row = state.db.one(f"update app.users set {sets}, updated_at = now() where id = %s returning {USER_COLS}", [*changes.values(), user["id"]])
    except psycopg.errors.UniqueViolation as e:
        which = "phone number" if "phone" in (e.diag.constraint_name or "") else "email"
        raise ApiError(409, "CONFLICT", f"That {which} belongs to another account.", {"field": "phone" if which != "email" else "email"})
    return user_out(row)


@router.get("/profile")
def get_profile(user: dict = Depends(current_user)):
    return profile_out(user)


@router.put("/profile")
def put_profile(body: ProfileIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    """Replaces the onboarding answers. Used by the setup form after sign-up and by the profile page later."""
    return profile_out(save_profile(state.db, str(user["id"]), body))


@router.post("/password", status_code=204)
def change_password(body: ChangePasswordIn, user: dict = Depends(current_user), state: AppState = Depends(get_state)):
    state.limiter.check(f"pwchange:{user['id']}", 6, 900)
    if not verify_password(body.currentPassword, user["password_hash"]):
        raise ApiError(422, "WRONG_PASSWORD", "Your current password is incorrect.")
    state.db.run("update app.users set password_hash = %s, updated_at = now() where id = %s", [hash_password(body.newPassword), user["id"]])
    # sign out every other device; this one (the session id inside the access token) stays signed in
    state.db.run("update app.refresh_tokens set revoked_at = coalesce(revoked_at, now()) where user_id = %s and family_id is distinct from %s::uuid",
                 [user["id"], user.get("_sid")])
    return Response(status_code=204)
