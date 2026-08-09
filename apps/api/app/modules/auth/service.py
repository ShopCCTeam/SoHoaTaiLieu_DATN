"""Auth service — business logic tách khỏi HTTP layer."""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.models.user import User


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
) -> User | None:
    """Verify email + password. Return User hoặc None.

    Trả None khi:
    - Email không tồn tại.
    - Password sai.
    - User bị `is_active=False`.
    """
    user = await get_user_by_email(session, email)
    if user is None:
        # Constant-time-ish: vẫn verify dummy hash để tránh timing oracle.
        verify_password_fn(password, "$2b$12$" + "0" * 53)
        return None
    if not user.is_active:
        return None
    if not verify_password_fn(password, user.password_hash):
        return None
    return user


def ensure_valid_role(role: str) -> UserRole:
    """Validate role enum — raise ValueError nếu không hợp lệ."""
    return UserRole(role)
