"""Authentication for the Fall Detection module: its own users and sessions
(opaque bearer tokens stored in the module's own database). Independent of SMC's
auth, licensing and SSO. Passwords are hashed with scrypt.

First run: with no users, POST /api/auth/setup creates the first admin (or set
ADMIN_EMAIL / ADMIN_PASSWORD in the environment)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import time

from fastapi import Depends, Header, HTTPException

from falldet import config
from falldet.core import db

log = logging.getLogger("auth")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, dk_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_password(password: str) -> None:
    if len(password or "") < config.PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters.")


def count_users() -> int:
    with db.connect(config.DB_PATH) as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def create_user(email: str, password: str, name: str = "") -> dict:
    email = normalize_email(email)
    if "@" not in email:
        raise ValueError("Enter a valid email address.")
    validate_password(password)
    with db.connect(config.DB_PATH) as conn:
        try:
            cur = conn.execute("INSERT INTO users(email, name, password_hash) VALUES(?,?,?)",
                               (email, name.strip(), hash_password(password)))
        except Exception as e:
            if "UNIQUE" in str(e):
                raise ValueError("That email is already registered.") from None
            raise
    return {"id": cur.lastrowid, "email": email, "name": name.strip()}


def bootstrap_from_env() -> None:
    if config.ADMIN_EMAIL and config.ADMIN_PASSWORD and count_users() == 0:
        create_user(config.ADMIN_EMAIL, config.ADMIN_PASSWORD, "Admin")
        log.info("created the first admin from ADMIN_EMAIL")


def authenticate(email: str, password: str) -> dict | None:
    with db.connect(config.DB_PATH) as conn:
        row = conn.execute("SELECT id, email, name, password_hash, active FROM users WHERE email = ?",
                           (normalize_email(email),)).fetchone()
    # verify even for an unknown email, so timing does not reveal which emails exist
    ok = verify_password(password or "", row[3] if row else hash_password("x"))
    if not (row and ok and row[4]):
        return None
    return {"id": row[0], "email": row[1], "name": row[2]}


def create_session(user: dict) -> str:
    token = secrets.token_urlsafe(32)
    with db.connect(config.DB_PATH) as conn:
        conn.execute("INSERT INTO sessions(token, user_id, expires_at) VALUES(?,?,?)",
                     (token, user["id"], time.time() + config.SESSION_TTL_SECONDS))
    return token


def revoke_session(token: str) -> None:
    with db.connect(config.DB_PATH) as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def purge_expired() -> None:
    with db.connect(config.DB_PATH) as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))


def get_session_user(token: str | None) -> dict | None:
    if not token:
        return None
    with db.connect(config.DB_PATH) as conn:
        row = conn.execute("SELECT u.id, u.email, u.name, u.active, s.expires_at FROM sessions s "
                           "JOIN users u ON u.id = s.user_id WHERE s.token = ?", (token,)).fetchone()
    if not row or not row[3] or row[4] < time.time():
        return None
    return {"id": row[0], "email": row[1], "name": row[2]}


def bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


def current_user(authorization: str | None = Header(None)) -> dict:
    user = get_session_user(bearer(authorization))
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return user


require_user = Depends(current_user)
