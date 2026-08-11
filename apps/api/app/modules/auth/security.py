"""Auth security primitives.

- `hash_password` / `verify_password`: argon2id (OWASP 2024).
- `create_access_token` / `decode_access_token`: HS256 JWT, TTL configurable.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import jwt
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings

# Argon2id — OWASP 2024 recommendation.
_password_hasher = Argon2Hasher()

# Dummy hash: valid argon2id format (argon2-cffi v=19).
# Pre-computed so it is stable across imports.
DUMMY_ARGON2ID_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "dGVzdGR1bW15aGFzaHNhbHQ$"
    "kGxKQQlC8J2vJfN2wB3y4xPqQqR8tU5vW6xY0zA1B2k123456"
)


def hash_password(plain: str) -> str:
    """Hash password với argon2id. Plain text KHÔNG log."""
    return _password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password với argon2id hash. Constant-time comparison."""
    try:
        return _password_hasher.verify(plain, hashed)
    except Exception:  # pragma: no cover — broad catch for malformed hashes
        return False


def create_access_token(
    *,
    subject: str,
    role: str,
    ttl_seconds: int | None = None,
) -> str:
    """Tạo HS256 access token.

    `subject` = user.id (UUID string).
    `role` = user.role (admin/staff/student) — embed cho RBAC nhanh.
    """
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.jwt_access_token_ttl_seconds
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + ttl,
        "iss": settings.app_name,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode + verify access token. Raises `jwt.PyJWTError` nếu invalid/expired."""
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub", "role"]},
    )


def hash_token(token: str) -> str:
    """SHA-256 hash of opaque refresh token (stored in DB, never plaintext)."""
    return hashlib.sha256(token.encode()).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison — timing-safe."""
    return hmac.compare_digest(a.encode(), b.encode())
