"""Auth router — POST /auth/login + POST /auth/refresh + POST /auth/logout + GET /auth/me.

D2: Refresh token in HttpOnly cookie.
D5: Router commits session once (service layer does NOT commit).
D11: Origin-CSRF check on refresh/logout.
D12: Structured audit events.
D13: Logout idempotent.
"""
from __future__ import annotations

import hashlib
import ipaddress
import uuid
from datetime import UTC
from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import REFRESH_COOKIE_SAMESITE
from app.core.errors import forbidden, unauthorized
from app.db.session import get_session
from app.models.user import User
from app.modules.auth.audit import audit_log
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.refresh_service import (
    ReuseDetected,
    TokenExpired,
    TokenInvalid,
    _revoke_family,
    revoke_refresh_token,
    rotate_refresh,
)
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshResponse,
    UserPublic,
)
from app.modules.auth.security import (
    create_access_token,
    hash_token,
    verify_password,
)
from app.modules.auth.service import AuthResult, authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _envelope(data: Any) -> dict[str, Any]:
    """Standard success envelope `{success, data}`."""
    return {"success": True, "data": data}


_TOKEN_TYPE_BEARER = "bearer"  # noqa: S105 — RFC 6750 constant


def _parse_ip(settings: Settings, request: Request) -> str | None:
    """Extract + validate client IP for INET column.

    Fallback chain:
    - Nếu trust_proxy_headers=True và X-Forwarded-For hợp lệ → dùng X-Forwarded-For.
    - Nếu trust_proxy_headers=False, X-Forwarded-For vẫn được đọc nhưng bỏ qua
      (để tránh spoofing). Luôn fall through xuống request.client.host.
    - Cuối cùng: request.client.host → parse IPv4/IPv6 → return.
    - Nếu không parse được: return None.
    """
    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded:
        raw_forwarded = x_forwarded.split(",")[0].strip()
        if settings.trust_proxy_headers:
            try:
                ipaddress.ip_address(raw_forwarded)
                return raw_forwarded
            except ValueError:
                return None
    if request.client and request.client.host:
        client_host = request.client.host
        try:
            ipaddress.ip_address(client_host)
            return client_host
        except ValueError:
            return None
    return None


def _apply_cookie(
    response: Response,
    settings: Settings,
    token: str,
    max_age: int | None = None,
) -> None:
    """Set refresh cookie on Response using Starlette's built-in method."""
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        path=settings.refresh_cookie_path,
        max_age=max_age,
        httponly=True,
        samesite=REFRESH_COOKIE_SAMESITE,
        secure=settings.cookie_secure,
    )


def _clear_cookie(response: Response, settings: Settings) -> None:
    """Clear refresh cookie on Response."""
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
    )


def _hash_email_for_audit(email: str) -> str:
    """SHA-256 hash of email — safe to log."""
    return hashlib.sha256(email.encode()).hexdigest()[:16]


def _check_origin_csrf(request: Request, settings: Settings) -> None:
    """Verify Origin header matches allowed origins (CSRF protection).

    Luật:
    - Có Origin → phải ∈ settings.cors_origins, sai → 403 AUTH_CSRF_ORIGIN_REJECTED.
    - Không có Origin → cho qua + audit log (curl, Next.js route handler không gửi Origin).

    Được gọi trên refresh + logout endpoints.
    """
    origin = request.headers.get("origin")
    if origin is None:
        # Same-site request không có Origin (curl, Next.js route handler).
        # Cho qua, không phải lỗi.
        audit_log("auth.csrf.origin_absent", ip=_parse_ip(settings, request))
        return
    # Verify origin against allowed CORS origins
    if origin not in settings.cors_origins:
        raise forbidden(
            detail=f"Origin '{origin}' không được phép.",
            code="AUTH_CSRF_ORIGIN_REJECTED",
        )


def _get_refresh_token(request: Request, settings: Settings) -> str | None:
    """Extract refresh token from cookie."""
    return request.cookies.get(settings.refresh_cookie_name)


async def _create_session(
    session: AsyncSession,
    user: User,
    request: Request,
    settings: Settings,
) -> tuple[str, int]:
    """Tạo refresh session + set cookie.

    Returns: (opaque_token, max_age_seconds)
    """
    import secrets
    from datetime import datetime, timedelta

    from app.models.refresh_session import RefreshSession

    token = secrets.token_hex(32)
    token_hash = hash_token(token)
    family_id = uuid.uuid4()
    ttl = settings.jwt_refresh_token_ttl_seconds
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)

    rs = RefreshSession(
        user_id=user.id,
        family_id=family_id,
        token_hash=token_hash,
        user_agent=request.headers.get("user-agent"),
        ip_address=_parse_ip(settings, request),
        issued_at=datetime.now(UTC),
        expires_at=expires_at,
    )
    session.add(rs)
    await session.flush()

    audit_log(
        "auth.login.success",
        user_id=user.id,
        ip=_parse_ip(settings, request),
        user_agent=request.headers.get("user-agent"),
    )

    return token, ttl


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=None,
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
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Verify email + password → trả access token + user info + set refresh cookie."""
    settings = get_settings()
    result, user = await authenticate(
        session=session,
        email=body.email,
        password=body.password,
        verify_password_fn=verify_password,
    )
    if result == AuthResult.INVALID_CREDENTIALS:
        audit_log(
            "auth.login.failed",
            email_hash=_hash_email_for_audit(body.email),
            reason="invalid_credentials",
            ip=_parse_ip(settings, request),
        )
        raise unauthorized(
            detail="Email hoặc mật khẩu không chính xác.",
            code="AUTH_INVALID_CREDENTIALS",
        )
    if result == AuthResult.USER_INACTIVE:
        audit_log(
            "auth.login.failed",
            email_hash=_hash_email_for_audit(body.email),
            reason="user_inactive",
            ip=_parse_ip(settings, request),
        )
        raise unauthorized(
            detail="Email hoặc mật khẩu không chính xác.",
            code="AUTH_INVALID_CREDENTIALS",
        )

    # Success: create JWT + refresh session
    assert user is not None, "authenticate returned OK but user is None"
    access_token = create_access_token(subject=user.id, role=user.role)
    refresh_token, max_age = await _create_session(
        session, user, request, settings
    )
    await session.commit()

    user_public = UserPublic.model_validate(user)
    _apply_cookie(response, settings, refresh_token, max_age)

    return _envelope(
        LoginResponse(
            access_token=access_token,
            token_type=_TOKEN_TYPE_BEARER,
            expires_in=settings.jwt_access_token_ttl_seconds,
            user=user_public,
        ).model_dump()
    )


@router.post(
    "/refresh",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Cấp access token mới (rotation)",
    responses={
        200: {"description": "Cấp access token mới, rotate refresh cookie"},
        401: {"description": "Token invalid / expired / reuse detected"},
        403: {"description": "CSRF — Origin không hợp lệ"},
    },
)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Rotate refresh token: verify old → revoke → create new + cookie."""
    settings = get_settings()

    # Origin-CSRF check
    _check_origin_csrf(request, settings)

    token = _get_refresh_token(request, settings)
    if not token:
        raise unauthorized(
            detail="Refresh token không tìm thấy.",
            code="AUTH_REFRESH_INVALID",
        )

    ip = _parse_ip(settings, request)
    ua = request.headers.get("user-agent")

    result = await rotate_refresh(
        session=session,
        token=token,
        user_agent=ua,
        ip_address=ip,
        create_access_token_fn=create_access_token,
    )

    # --- error branches ---
    if isinstance(result, ReuseDetected):
        await _revoke_family(session, result.family_id, "reuse_detected")
        await session.commit()
        audit_log(
            "auth.refresh.reuse_detected",
            family_id=str(result.family_id),
            ip=ip,
        )
        _clear_cookie(response, settings)
        raise unauthorized(
            detail="Phát hiện reuse. Toàn bộ session đã bị thu hồi.",
            code="AUTH_REFRESH_REUSE_DETECTED",
        )

    if isinstance(result, TokenExpired):
        audit_log("auth.refresh.expired", ip=ip)
        _clear_cookie(response, settings)
        raise unauthorized(
            detail="Refresh token đã hết hạn.",
            code="AUTH_REFRESH_EXPIRED",
        )

    if isinstance(result, TokenInvalid):
        audit_log("auth.refresh.invalid", ip=ip)
        _clear_cookie(response, settings)
        raise unauthorized(
            detail="Refresh token không hợp lệ.",
            code="AUTH_REFRESH_INVALID",
        )

    # --- success ---
    rotation = result
    await session.commit()

    audit_log(
        "auth.refresh.rotated",
        user_id=rotation.user_id,
        family_id=str(rotation.family_id),
        ip=ip,
    )

    _apply_cookie(
        response,
        settings,
        rotation.refresh_token,
        settings.jwt_refresh_token_ttl_seconds,
    )

    return _envelope(
        RefreshResponse(
            access_token=rotation.access_token,
            expires_in=rotation.expires_in,
        ).model_dump()
    )


@router.post(
    "/logout",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Đăng xuất",
    responses={
        204: {"description": "No Content — logout thành công hoặc idempotent"},
        403: {"description": "CSRF — Origin không hợp lệ"},
    },
)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Revoke refresh token + clear cookie. Idempotent."""
    settings = get_settings()

    # Origin-CSRF check
    _check_origin_csrf(request, settings)

    token = _get_refresh_token(request, settings)
    ip = _parse_ip(settings, request)

    if token:
        await revoke_refresh_token(session, token)
        await session.commit()

    audit_log("auth.logout", ip=ip)
    _clear_cookie(response, settings)


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
