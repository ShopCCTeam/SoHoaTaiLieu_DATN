"""Pytest fixtures shared across tests."""
from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.models.user import User


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mỗi test chạy trong env riêng với JWT secret cố định."""
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-must-be-32-bytes-or-more!")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_TTL_SECONDS", "60")
    get_settings.cache_clear()
    yield


@pytest.fixture
async def db_engine(tmp_path: Path):
    """SQLite async engine, tạo schema mới mỗi test."""
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session_factory(db_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
async def seeded_user(db_session_factory) -> User:
    """Tạo 1 user mẫu để test login."""
    from app.modules.auth.security import hash_password

    async with db_session_factory() as session:
        user = User(
            id="usr_admin_01",
            email="admin@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="Quản Trị Viên",
            role="admin",
            department="Phòng CTSV",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        yield user


@pytest.fixture
async def api_client(db_session_factory) -> AsyncIterator[AsyncClient]:
    """Async HTTP client với DB dependency override."""
    from app.main import create_app

    app = create_app()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        async with db_session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
