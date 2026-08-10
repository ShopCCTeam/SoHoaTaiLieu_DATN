"""Auth service — business logic tách khỏi HTTP layer."""
from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.models.user import User


class AuthResult(Enum):
    """Kết quả authenticate — tri-state để router phân biệt."""

    OK = "ok"
    """Email/password đúng, user active."""

    INVALID_CREDENTIALS = "invalid_credentials"
    """Email không tồn tại hoặc password sai."""

    USER_INACTIVE = "user_inactive"
    """Email đúng nhưng user bị is_active=False."""


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    return await session.get(User, user_id)


async def authenticate(
    session: AsyncSession,
    email: str,
    password: str,
    verify_password_fn: Callable[[str, str], bool],
) -> tuple[AuthResult, User | None]:
    """Verify email + password.

    Returns:
        (AuthResult.OK, user) — đăng nhập thành công.
        (AuthResult.INVALID_CREDENTIALS, None) — email không tồn tại hoặc password sai.
        (AuthResult.USER_INACTIVE, None) — email đúng nhưng user bị inactive.
    """
    user = await get_user_by_email(session, email)
    if user is None:
        # Constant-time: verify dummy hash để tránh timing oracle.
        from app.modules.auth.security import DUMMY_PASSWORD_HASH

        verify_password_fn(password, DUMMY_PASSWORD_HASH)
        return (AuthResult.INVALID_CREDENTIALS, None)
    if not user.is_active:
        return (AuthResult.USER_INACTIVE, None)
    if not verify_password_fn(password, user.password_hash):
        return (AuthResult.INVALID_CREDENTIALS, None)
    return (AuthResult.OK, user)


def ensure_valid_role(role: str) -> UserRole:
    """Validate role enum — raise ValueError nếu không hợp lệ."""
    return UserRole(role)
