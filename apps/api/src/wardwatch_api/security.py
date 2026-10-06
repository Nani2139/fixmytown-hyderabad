"""Password hashing + signed session cookie. Stdlib only so Windows stays easy."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

SESSION_COOKIE = "ww_session"
SECRET = os.getenv("JWT_SECRET", "dev-insecure-change-me")
COOKIE_MAX_AGE = 60 * 60 * 24 * 14  # 14 days


def hash_password(plain: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 120_000)
    return f"pbkdf2${salt}${digest.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        scheme, salt, digest = stored.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2":
        return False
    check = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 120_000)
    return hmac.compare_digest(check.hex(), digest)


def sign_session(user_id: str) -> str:
    sig = hmac.new(SECRET.encode(), user_id.encode(), hashlib.sha256).hexdigest()
    return f"{user_id}.{sig}"


def read_session(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    user_id, sig = token.rsplit(".", 1)
    expected = hmac.new(SECRET.encode(), user_id.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return user_id


def set_session_cookie(response: JSONResponse, user_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        sign_session(user_id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
        path="/",
    )


def user_id_from_request(request: Request) -> str | None:
    return read_session(request.cookies.get(SESSION_COOKIE))
