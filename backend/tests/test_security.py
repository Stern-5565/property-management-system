"""Tests for app/core/security.py - password hashing and JWT tokens.

Pure unit tests, no database involved.
"""

import time

import pytest

from app.core.exceptions import AppError
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password


def test_hash_password_does_not_return_the_plain_password() -> None:
    hashed = hash_password("Password123!")
    assert hashed != "Password123!"
    assert hashed.startswith("$2b$")  # bcrypt's own format marker


def test_verify_password_accepts_the_correct_password() -> None:
    hashed = hash_password("Password123!")
    assert verify_password("Password123!", hashed) is True


def test_verify_password_rejects_the_wrong_password() -> None:
    hashed = hash_password("Password123!")
    assert verify_password("WrongPassword", hashed) is False


def test_hash_password_uses_a_random_salt_each_time() -> None:
    """Two hashes of the same password must differ - if they didn't, that
    would mean no random salt was being used, which defeats a major point
    of bcrypt (identical passwords would produce identical hashes,
    revealing which users share a password just from the database alone).
    """
    first = hash_password("Password123!")
    second = hash_password("Password123!")
    assert first != second
    # Both still verify correctly despite being different strings.
    assert verify_password("Password123!", first) is True
    assert verify_password("Password123!", second) is True


def test_access_token_round_trips_the_user_id() -> None:
    token = create_access_token(user_id=42)
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_refresh_token_round_trips_the_user_id() -> None:
    token = create_refresh_token(user_id=42)
    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"


def test_decode_token_rejects_an_access_token_presented_as_a_refresh_token() -> None:
    """A refresh token must never be usable where an access token is
    expected, and vice versa - otherwise the two token types wouldn't
    actually be separate security boundaries."""
    access_token = create_access_token(user_id=1)

    with pytest.raises(AppError) as exc_info:
        decode_token(access_token, expected_type="refresh")
    assert exc_info.value.code == "INVALID_TOKEN"
    assert exc_info.value.status_code == 401


def test_decode_token_rejects_garbage() -> None:
    with pytest.raises(AppError) as exc_info:
        decode_token("not.a.real.token", expected_type="access")
    assert exc_info.value.code == "INVALID_TOKEN"


def test_decode_token_rejects_a_token_signed_with_a_different_secret() -> None:
    import jwt as pyjwt

    forged = pyjwt.encode(
        {"sub": "1", "type": "access", "iat": time.time(), "exp": time.time() + 3600},
        "a-completely-different-secret-that-is-long-enough-for-hs256",
        algorithm="HS256",
    )

    with pytest.raises(AppError) as exc_info:
        decode_token(forged, expected_type="access")
    assert exc_info.value.code == "INVALID_TOKEN"
