"""Auth router — POST /auth/login + GET /auth/me.

Tất cả response bọc trong envelope `{success: true, data: ...}` (xem `docs/api/openapi.yaml`).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import unauthorized
from app.db.session import get_session
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    UserPublic,
)
from app.modules.auth.security import create_access_token, verify_password
from app.modules.auth.service import AuthResult, authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


def _envelope(data: Any) -> dict[str, Any]:
    """Standard success envelope `{success, data}`."""
    return {"success": True, "data": data}


@router.post(
    "/login",
    response_model=None,  # Trả envelope thô.
    status_code=status.HTTP_200_OK,
    summary="Đăng nhập",
    responses={
        401: {"description": "Email hoặc mật khẩu sai"},
        422: {"description": "Validation error"},
    },
)
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Verify email + password → trả access token + user info."""
    result, user = await authenticate(
        session=session,
        email=body.email,
        password=body.password,
        verify_password_fn=verify_password,
    )
    if result == AuthResult.INVALID_CREDENTIALS:
        raise unauthorized(
            detail="Email hoặc mật khẩu không chính xác.",
            code="AUTH_INVALID_CREDENTIALS",
        )
    if result == AuthResult.USER_INACTIVE:
        # Cùng 401 (chống user enumeration ở login).
        raise unauthorized(
            detail="Email hoặc mật khẩu không chính xác.",
            code="AUTH_INVALID_CREDENTIALS",
        )

    # --- success ---
    settings = get_settings()
    access_token = create_access_token(subject=user.id, role=user.role)
    user_public = UserPublic.model_validate(user)

    # Phase 1: không set refresh cookie. Phase 2 sẽ thêm HttpOnly cookie.
    return _envelope(
        LoginResponse(
            access_token=access_token,
            token_type="bearer",  # noqa: S106
            expires_in=settings.jwt_access_token_ttl_seconds,
            user=user_public,
        ).model_dump()
    )


@router.get(
    "/me",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin user hiện tại",
    responses={
        401: {"description": "Chưa xác thực / token invalid"},
    },
)
async def me(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Trả về user object của Bearer token."""
    return _envelope(
        MeResponse(user=UserPublic.model_validate(current_user)).model_dump()
    )
