"""Integration tests cho /auth/login + /auth/me."""

from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.user import User


@pytest.mark.asyncio
async def test_login_success_returns_access_token_and_user(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 60
    assert data["user"]["email"] == "admin@example.edu.vn"
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401_problem_detail(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "WrongPass!"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["type"].endswith("/problems/auth_invalid_credentials")
    assert body["code"] == "AUTH_INVALID_CREDENTIALS"
    assert "Chưa xác thực" in body["title"]


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.edu.vn", "password": "Demo@2026"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_inactive_user_returns_401(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    from app.modules.auth.security import hash_password

    async with db_session_factory() as session:
        user = User(
            id="usr_disabled",
            email="disabled@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="Disabled",
            role="staff",
            is_active=False,
        )
        session.add(user)
        await session.commit()

    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "disabled@example.edu.vn", "password": "Demo@2026"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_validation_error_returns_422(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "short"},
    )
    assert response.status_code == 422
    body = response.json()
    # FastAPI validation error → RFC 7807 wrapper.
    assert "type" in body


@pytest.mark.asyncio
async def test_login_missing_field_returns_422(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn"},
    )
    assert response.status_code == 422


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
    assert body["data"]["user"]["id"] == "usr_admin_01"


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
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    from app.modules.auth.security import create_access_token

    expired_token = create_access_token(
        subject=seeded_user.id,
        role=seeded_user.role,
        ttl_seconds=1,
    )
    await asyncio.sleep(2)

    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_EXPIRED"
