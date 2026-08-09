"""Unit tests cho password hashing + JWT."""

from __future__ import annotations

import time

import jwt
import pytest

from app.modules.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_roundtrip() -> None:
    plain = "Demo@2026"
    hashed = hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$2b$")
    assert verify_password(plain, hashed) is True


def test_verify_wrong_password_returns_false() -> None:
    hashed = hash_password("Demo@2026")
    assert verify_password("WrongPass", hashed) is False


def test_verify_malformed_hash_returns_false() -> None:
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_create_and_decode_access_token_roundtrip() -> None:
    token = create_access_token(subject="usr_01", role="admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "usr_01"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_invalid_token_raises() -> None:
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("invalid.token.here")


def test_decode_expired_token_raises() -> None:
    # TTL 1s → đợi sleep.
    token = create_access_token(subject="usr_01", role="staff", ttl_seconds=1)
    time.sleep(2)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_token_requires_role_claim() -> None:
    """Nếu payload thiếu 'role', decode raises MissingRequiredClaimError."""
    import time as _t

    settings_payload = {
        "sub": "usr_01",
        "iat": int(_t.time()),
        "exp": int(_t.time()) + 60,
        "iss": "ctsv-api",
        "type": "access",
    }
    from app.core.config import get_settings

    settings = get_settings()
    token = jwt.encode(
        settings_payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)
