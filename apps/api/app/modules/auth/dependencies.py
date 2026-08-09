"""FastAPI dependencies cho auth — Bearer token + current user lookup."""
from __future__ import annotations

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import unauthorized
from app.db.session import get_session
from app.models.user import User
from app.modules.auth.security import decode_access_token
from app.modules.auth.service import get_user_by_id

# tokenUrl chỉ để OpenAPI doc biết nơi lấy token.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,  # Tự raise 401 RFC 7807 để consistent với errors module.
)


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Decode Bearer token + load User từ DB.

    Raises 401 (RFC 7807) nếu:
    - Token thiếu.
    - Token invalid/expired.
    - User không tồn tại.
    - User không active.
    """
    if not token:
        raise unauthorized(
            detail="Thiếu Bearer token. Vui lòng đăng nhập.",
            code="AUTH_MISSING_TOKEN",
        )
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as e:
        raise unauthorized(
            detail="Access token đã hết hạn. Vui lòng đăng nhập lại.",
            code="AUTH_TOKEN_EXPIRED",
        ) from e
    except jwt.InvalidTokenError as e:
        raise unauthorized(
            detail="Access token không hợp lệ.",
            code="AUTH_INVALID_TOKEN",
        ) from e

    user_id = payload.get("sub")
    if not user_id:
        raise unauthorized(
            detail="Token thiếu subject claim.",
            code="AUTH_INVALID_TOKEN",
        )

    user = await get_user_by_id(session, user_id)
    if user is None:
        raise unauthorized(
            detail="Người dùng không tồn tại.",
            code="AUTH_USER_NOT_FOUND",
        )
    if not user.is_active:
        raise unauthorized(
            detail="Tài khoản đã bị vô hiệu hoá.",
            code="AUTH_USER_DISABLED",
        )
    return user
