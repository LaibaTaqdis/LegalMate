"""FastAPI dependencies: shared state and the signed-in user."""
from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .errors import unauthorized
from .security import decode_access_token
from .state import AppState
from .users_repo import USER_COLS

_bearer = HTTPBearer(auto_error=False)


def get_state(request: Request) -> AppState:
    return request.app.state.ctx


def current_user(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                 state: AppState = Depends(get_state)) -> dict:
    """The signed-in user's row. Checked against the database on every request, so a suspended or deleted account loses access at once."""
    if creds is None:
        raise unauthorized("Please sign in to continue.")
    claims = decode_access_token(creds.credentials, state.settings.jwt_secret)
    if claims is None:
        raise unauthorized("Your session has expired. Please sign in again.", "TOKEN_EXPIRED")
    row = state.db.one(f"select {USER_COLS} from app.users where id = %s", [claims["sub"]])
    if row is None or row["status"] != "active":
        raise unauthorized("This account is not available.")
    row["_sid"] = claims.get("sid")
    request.state.user_id = str(row["id"])
    return row
