"""Auth security primitives.

- `hash_password` / `verify_password`: bcrypt cost ≥ 12.
- `create_access_token` / `decode_access_token`: HS256 JWT, TTL configurable.

Refresh token (HttpOnly cookie) sẽ thêm ở Phase 2.
"""
from __future__ import annotations

import time
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# bcrypt cost ≥ 12 (rule 06-security.mdc).
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    """Hash password với bcrypt cost 12. Plain text KHÔNG log."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password với bcrypt hash. Constant-time comparison."""
    try:
        return _pwd_context.verify(plain, hashed)
    except (ValueError, TypeError):
        # Hash malformed → false. KHÔNG raise (tránh info leak).
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
