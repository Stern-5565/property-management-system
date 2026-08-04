"""Password hashing and JWT token creation/verification.

Hashing versus encryption - why passwords are hashed, never encrypted:
Encryption is two-way: given the key, ciphertext can be turned back into
the original plaintext. Hashing (bcrypt, here) is one-way: there is no key
that turns a password hash back into the password. Verifying a login
re-hashes the submitted password and compares the two hashes - the
original password is never stored or recoverable, by us or by anyone who
steals the database. bcrypt specifically (rather than a fast general-
purpose hash like SHA-256) also embeds a random salt in its own output and
has a deliberately slow, tunable work factor, which is what actually makes
it resistant to brute-force/rainbow-table attacks - a fast hash is the
wrong tool for passwords even though it's still "hashing".

Access tokens versus refresh tokens:
- An access token is short-lived (JWT_ACCESS_TOKEN_EXPIRE_MINUTES, default
  30 minutes) and is sent with every request to prove who the caller is.
  Short lifetime limits how long a stolen token stays useful.
- A refresh token is long-lived (JWT_REFRESH_TOKEN_EXPIRE_DAYS, default 7
  days) and is used for exactly one thing: obtaining a new access token via
  POST /api/auth/refresh, without making the user log in again every 30
  minutes. It is never accepted by any other endpoint - see the "type"
  claim check in decode_token.

Both are signed (not encrypted) JWTs: anyone can read the payload (it's
just base64), but nobody can forge or modify one without JWT_SECRET_KEY,
which only the server knows.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.exceptions import AppError

TokenType = Literal["access", "refresh"]


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash (e.g. not actually a bcrypt hash) - treat as a
        # failed verification rather than letting the exception propagate.
        return False


def _create_token(user_id: int, token_type: TokenType, expires_delta: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    return _create_token(user_id, "access", timedelta(minutes=settings.jwt_access_token_expire_minutes))


def create_refresh_token(user_id: int) -> str:
    settings = get_settings()
    return _create_token(user_id, "refresh", timedelta(days=settings.jwt_refresh_token_expire_days))


def decode_token(token: str, expected_type: TokenType) -> dict:
    """Decodes and validates a JWT, raising AppError(401) with a generic,
    safe message on any problem - expired, malformed, wrong signature, or
    the wrong token type presented to the wrong endpoint (e.g. a refresh
    token sent as if it were an access token). The caller never learns
    which specific thing was wrong, only that the credential is invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise AppError("TOKEN_EXPIRED", "Your session has expired. Please log in again.", status_code=401) from None
    except jwt.InvalidTokenError:
        raise AppError("INVALID_TOKEN", "Could not validate credentials.", status_code=401) from None

    if payload.get("type") != expected_type:
        raise AppError("INVALID_TOKEN", "Could not validate credentials.", status_code=401)

    return payload
