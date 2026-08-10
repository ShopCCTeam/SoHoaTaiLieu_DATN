"""Refresh token rotation service.

D1: Opaque token + SHA-256 hash stored in DB. Family-based revocation.
D4: Atomic rotation via SELECT FOR UPDATE + conditional UPDATE WHERE.
D5: Service does NOT commit — router/application layer commits once.

Usage pattern:
    session = ...
    result = await rotate_refresh(session, token, ua, ip)
    await session.commit()   # ← router commits
    if result is None:
        raise unauthorized(...)
    access_token, new_token = result
"""
from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.modules.auth.security import hash_token


@dataclass
class RotationResult:
    """Kết quả rotation thành công."""

    access_token: str
    refresh_token: str  # plaintext (sent to client)
    expires_in: int


@dataclass
class ReuseDetected:
    """Token cũ bị reuse — family revoked."""

    family_id: uuid.UUID


# ---- helpers (không commit) ----

async def _get_session_by_hash(
    session: AsyncSession,
    token_hash: str,
) -> tuple[RefreshSession | None, bool]:
    """Lookup session by token hash.

    Returns:
        (session, False) — session tồn tại và chưa revoked.
        (session, True) — session tồn tại nhưng đã bị revoked (reuse detected).
        (None, False) — session không tồn tại.
    """
    stmt = select(RefreshSession).where(
        RefreshSession.token_hash == token_hash,
    )
    result = await session.execute(stmt)
    s = result.scalar_one_or_none()
    if s is None:
        return (None, False)
    return (s, s.revoked_at is not None)


async def _lock_session_for_update(
    session: AsyncSession,
    session_id: uuid.UUID,
) -> RefreshSession | None:
    """Lock session row for update (prevents concurrent rotation)."""
    stmt = (
        select(RefreshSession)
        .where(
            RefreshSession.id == session_id,
            RefreshSession.revoked_at.is_(None),
        )
        .with_for_update()
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _revoke_family(
    session: AsyncSession,
    family_id: uuid.UUID | None,
    reason: str,
) -> int:
    """Revoke ALL sessions in a family (NIST 800-63B reuse detection)."""
    stmt = (
        update(RefreshSession)
        .where(
            RefreshSession.family_id == family_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    result: Any = await session.execute(stmt)
    rowcount: int = result.rowcount
    return rowcount


def _generate_opaque_token() -> str:
    """Tạo opaque refresh token (32 bytes hex = 64 chars)."""
    return secrets.token_hex(32)


# ---- main rotation service (không commit) ----

async def rotate_refresh(
    session: AsyncSession,
    token: str,
    user_agent: str | None,
    ip_address: str | None,
    create_access_token_fn: Callable[..., str],
) -> tuple[RotationResult, None] | tuple[None, str]:
    """Rotate refresh token.

    Returns:
        (RotationResult, None) — success
        (None, "reuse") — reuse detected, family revoked
        (None, "expired") — token expired
        (None, "invalid") — token not found / user inactive
    """
    settings = get_settings()
    token_hash = hash_token(token)

    # Step 1: lookup by hash — check for reuse
    old_session, was_revoked = await _get_session_by_hash(session, token_hash)
    if old_session is None:
        return (None, "invalid")
    if was_revoked:
        # Reuse detected: token was valid before but has been revoked
        return (None, "reuse")

    # Step 2: check expiry
    now = datetime.now(UTC)
    if old_session.expires_at.replace(tzinfo=UTC) < now:
        return (None, "expired")

    # Step 3: lock FOR UPDATE
    locked = await _lock_session_for_update(session, old_session.id)
    if locked is None:
        return (None, "invalid")

    # Step 4: generate new token + family
    new_token = _generate_opaque_token()
    new_token_hash = hash_token(new_token)
    new_family_id = uuid.uuid4()
    new_session = RefreshSession(
        user_id=locked.user_id,
        family_id=new_family_id,
        token_hash=new_token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC)
        + timedelta(seconds=settings.jwt_refresh_token_ttl_seconds),
    )
    session.add(new_session)
    await session.flush()

    # Step 5: revoke old session
    old_session.revoked_at = datetime.now(UTC)
    old_session.replaced_by_id = new_session.id

    # Step 6: load user
    user = await session.get(User, locked.user_id)
    if user is None or not user.is_active:
        return (None, "invalid")

    # Step 7: generate access token
    access_token = create_access_token_fn(subject=user.id, role=user.role)

    return (
        RotationResult(
            access_token=access_token,
            refresh_token=new_token,
            expires_in=settings.jwt_access_token_ttl_seconds,
        ),
        None,
    )


async def revoke_refresh_token(
    session: AsyncSession,
    token: str,
) -> bool:
    """Revoke a specific refresh token (logout).

    Returns True nếu token được revoke, False nếu không tìm thấy.
    Service does NOT commit — router commits.
    """
    token_hash = hash_token(token)
    stmt = (
        update(RefreshSession)
        .where(
            RefreshSession.token_hash == token_hash,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    result: Any = await session.execute(stmt)
    rowcount: int = result.rowcount
    return rowcount > 0


async def revoke_all_user_sessions(
    session: AsyncSession,
    user_id: str,
    reason: str,
) -> int:
    """Revoke ALL refresh sessions for a user (e.g., password change).

    Returns count of revoked sessions.
    """
    stmt = (
        update(RefreshSession)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    result: Any = await session.execute(stmt)
    rowcount: int = result.rowcount
    return rowcount
