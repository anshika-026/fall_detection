from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from falldet import auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Per-client throttle for sign-in / setup attempts (in-memory; one process).
_attempts: dict[str, deque] = defaultdict(deque)
WINDOW, LIMIT = 300.0, 10


def _throttle(request: Request, key: str = "") -> None:
    ident = f"{request.client.host if request.client else '?'}|{key}"
    q = _attempts[ident]
    now = time.time()
    while q and q[0] < now - WINDOW:
        q.popleft()
    if len(q) >= LIMIT:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")
    q.append(now)


class Credentials(BaseModel):
    email: str
    password: str
    name: str = ""


@router.get("/status")
def status():
    return {"setup_required": auth.count_users() == 0}


@router.post("/setup")
def setup(payload: Credentials, request: Request):
    """Creates the first admin. Refused once any user exists."""
    _throttle(request, "setup")
    if auth.count_users() > 0:
        raise HTTPException(status_code=409, detail="Setup is already complete. Sign in instead.")
    try:
        user = auth.create_user(payload.email, payload.password, payload.name or "Admin")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return {"token": auth.create_session(user), "user": user}


@router.post("/login")
def login(payload: Credentials, request: Request):
    _throttle(request, auth.normalize_email(payload.email))
    user = auth.authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return {"token": auth.create_session(user), "user": user}


@router.get("/me")
def me(user: dict = Depends(auth.current_user)):
    return user


@router.post("/logout")
def logout(authorization: str | None = Header(None)):
    token = auth.bearer(authorization)
    if token:
        auth.revoke_session(token)
    return {"ok": True}
