"""Tests cho /auth/login + /auth/refresh + /auth/logout + /auth/me endpoints.

Test theo ADR-0003 v3:
- Cookie Set-Cookie headers (httpx response.headers).
- Origin-CSRF check.
- Refresh token reuse detection.
- Logout idempotent.
"""
from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.session import get_session
from app.models.refresh_session import RefreshSession
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_refresh_cookie(cookies: dict[str, str]) -> str | None:
    """Extract rt cookie value from httpx cookies."""
    return cookies.get("rt")


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success_sets_refresh_cookie(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    """Login returns 200 + sets HttpOnly refresh cookie."""
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert body["data"]["user"]["email"] == "admin@example.edu.vn"

    # Cookie phải được set
    set_cookie = response.headers.get("set-cookie", "")
    assert "rt=" in set_cookie.lower()
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "WrongPass!"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.edu.vn", "password": "Demo@2026"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_inactive_user_returns_401(
    db_session_factory: async_sessionmaker,
) -> None:
    from app.main import create_app
    from app.modules.auth.security import hash_password

    async with db_session_factory() as session:
        user = User(
            id="usr_inactive",
            email="inactive@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="Inactive User",
            role="staff",
            is_active=False,
        )
        session.add(user)
        await session.commit()

    app = create_app()

    async def _override():
        async with db_session_factory() as s:
            yield s
            await s.commit()

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.edu.vn", "password": "Demo@2026"},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


# ---------------------------------------------------------------------------
# /me tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_me_with_valid_token_returns_user(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    token = login.json()["data"]["access_token"]

    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["user"]["email"] == "admin@example.edu.vn"


@pytest.mark.asyncio
async def test_me_without_token_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_MISSING_TOKEN"


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.asyncio
async def test_me_with_expired_token_returns_401(
    seeded_user: User,
) -> None:
    from app.main import create_app
    from app.modules.auth.security import create_access_token

    app = create_app()
    expired_token = create_access_token(
        subject=seeded_user.id,
        role=seeded_user.role,
        ttl_seconds=1,
    )
    await asyncio.sleep(2)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_EXPIRED"


# ---------------------------------------------------------------------------
# Refresh tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    # Login first
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )

    # Extract cookie
    cookie_header = login.headers.get("set-cookie", "")
    rt_cookie = None
    for part in cookie_header.split(";"):
        if "rt=" in part.lower():
            rt_cookie = part.split("rt=", 1)[1].strip().split(";")[0].split(";")[0]
            break

    assert rt_cookie is not None, f"No rt cookie in: {cookie_header}"

    # Refresh
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": f"rt={rt_cookie}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "access_token" in body["data"]
    # Access token có thể giống vì cùng TTL và timing; key là rotation đã xảy ra.
    # Verify rotation qua test khác (reuse detection).


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REFRESH_INVALID"


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": "rt=invalid_token_not_in_db",
        },
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REFRESH_INVALID"


@pytest.mark.asyncio
async def test_refresh_rotation_revokes_old_token(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    # Login
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    cookie_header = login.headers.get("set-cookie", "")
    rt_token = None
    for part in cookie_header.split(";"):
        if "rt=" in part.lower():
            rt_token = part.split("rt=", 1)[1].strip().split(";")[0]
            break
    assert rt_token is not None

    # Refresh lần 1 → nhận token mới
    r1 = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": f"rt={rt_token}",
        },
    )
    assert r1.status_code == 200
    r1_cookie = r1.headers.get("set-cookie", "")
    rt_token_2 = None
    for part in r1_cookie.split(";"):
        if "rt=" in part.lower():
            rt_token_2 = part.split("rt=", 1)[1].strip().split(";")[0]
            break
    assert rt_token_2 is not None
    assert rt_token_2 != rt_token

    # Dùng token cũ lần 2 → reuse detected → 401
    r2 = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": f"rt={rt_token}",
        },
    )
    assert r2.status_code == 401
    assert r2.json()["code"] == "AUTH_REFRESH_REUSE_DETECTED"


# ---------------------------------------------------------------------------
# CSRF tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_missing_origin_returns_403(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    # Login
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    cookie_header = login.headers.get("set-cookie", "")
    rt_token = None
    for part in cookie_header.split(";"):
        if "rt=" in part.lower():
            rt_token = part.split("rt=", 1)[1].strip().split(";")[0]
            break

    # Refresh WITHOUT Origin header → 403 CSRF
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"rt={rt_token}"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_CSRF_ORIGIN_ABSENT"


@pytest.mark.asyncio
async def test_refresh_unexpected_origin_returns_403(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    # Login
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    cookie_header = login.headers.get("set-cookie", "")
    rt_token = None
    for part in cookie_header.split(";"):
        if "rt=" in part.lower():
            rt_token = part.split("rt=", 1)[1].strip().split(";")[0]
            break

    # Refresh với Origin không trong CORS list → 403
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "https://evil.example.com",
            "Cookie": f"rt={rt_token}",
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_CSRF_ORIGIN_REJECTED"


# ---------------------------------------------------------------------------
# Logout tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_revokes_token_and_clears_cookie(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    # Login
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    cookie_header = login.headers.get("set-cookie", "")
    rt_token = None
    for part in cookie_header.split(";"):
        if "rt=" in part.lower():
            rt_token = part.split("rt=", 1)[1].strip().split(";")[0]
            break

    # Logout
    response = await api_client.post(
        "/api/v1/auth/logout",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": f"rt={rt_token}",
        },
    )
    assert response.status_code == 204

    # Cookie phải được clear
    clear_cookie = response.headers.get("set-cookie", "")
    assert "rt=" in clear_cookie.lower()
    assert "max-age=0" in clear_cookie.lower()


@pytest.mark.asyncio
async def test_logout_idempotent_no_token(api_client: AsyncClient) -> None:
    """Logout không có token → still 204 (idempotent)."""
    response = await api_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_csrf_requires_origin(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/auth/logout")
    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_CSRF_ORIGIN_ABSENT"


# ---------------------------------------------------------------------------
# Login sets refresh session in DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_creates_refresh_session_in_db(
    db_session_factory: async_sessionmaker,
) -> None:
    from sqlalchemy import select

    from app.main import create_app
    from app.modules.auth.security import hash_password

    async with db_session_factory() as session:
        user = User(
            id="usr_login_session",
            email="session_test@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="Session Test",
            role="staff",
            is_active=True,
        )
        session.add(user)
        await session.commit()

    app = create_app()

    async def _override():
        async with db_session_factory() as s:
            yield s
            await s.commit()

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "session_test@example.edu.vn", "password": "Demo@2026"},
        )
    assert login.status_code == 200

    # Verify refresh session was created
    async with db_session_factory() as session:
        stmt = select(RefreshSession).where(
            RefreshSession.user_id == "usr_login_session"
        )
        sessions = (await session.execute(stmt)).scalars().all()
        assert len(sessions) == 1
        assert sessions[0].user_id == "usr_login_session"
        assert sessions[0].revoked_at is None
        assert len(sessions[0].token_hash) == 64  # SHA-256 hex
