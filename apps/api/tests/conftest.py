"""Pytest fixtures shared across tests."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg  # noqa: F401 — InvalidCatalogNameError for skip_or_fail
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.models.user import User

# ---------------------------------------------------------------------------
# Env setup
# ---------------------------------------------------------------------------

# CI phải có Postgres — nếu probe fail thì FAIL, không skip. Local dev
# không có Docker thì skip — expected.
_IN_CI = os.environ.get("CI", "").lower() in {"1", "true", "yes"}


def _skip_or_fail(msg: str) -> None:
    """Trong CI: fail (Postgres phải chạy). Ngoài CI: skip (expected)."""
    if _IN_CI:
        pytest.fail(f"CI phải có Postgres: {msg}")
    pytest.skip(msg)


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mỗi test chạy trong env riêng với JWT secret cố định."""
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-must-be-32-bytes-or-more!")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_TTL_SECONDS", "60")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "cache+memory://")
    get_settings.cache_clear()

    from app.worker.celery_app import configure_celery

    configure_celery()
    yield


@pytest.fixture(autouse=True)
def _force_local_storage():
    """Force LocalStorageService cho mọi test.

    Production `get_storage_service()` chỉ trả LocalStorageService khi
    app_env == "test". Nhiều test chạy dưới app_env khác (development/
    staging/production) → sẽ nhận MinioStorageService và fail vì package
    `minio` không được cài. Reset storage singleton về LocalStorageService
    trước mỗi test, teardown về None để không rò rỉ giữa các test.
    """
    from app.services import storage as storage_module
    from app.services.storage import LocalStorageService

    storage_module._storage_instance = LocalStorageService()
    yield
    storage_module._storage_instance = None


@pytest.fixture(autouse=True)
def _mock_ocr_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the worker's OCR step succeed in tests without native engines.

    Production `process_document_task` builds a bare `OcrEngineService()` whose
    PaddleOCR/Tesseract engines are unavailable in CI/dev; the service now
    raises (no silent mock). Tests that exercise the full pipeline explicitly
    inject the deterministic mock strategy as the primary engine here.
    """
    import app.worker.tasks as tasks_module
    from app.services.ocr_engine import FallbackMockOcrStrategy, OcrEngineService

    def _factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs.setdefault("primary_engine", FallbackMockOcrStrategy())
        return OcrEngineService(*args, **kwargs)

    monkeypatch.setattr(tasks_module, "OcrEngineService", _factory)
    yield


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def db_engine(tmp_path: Path):
    """SQLite async engine, tạo schema mới mỗi test.

    RefreshSession (PG UUID/INET) wrap bằng TypeDecorator để chạy được
    trên SQLite. Integration tests trên Postgres dùng `pg_engine` fixture.
    """
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def pg_engine():
    """Postgres async engine cho integration tests.

    Trong CI: probe fail → pytest.fail (Postgres phải chạy).
    Ngoài CI (dev không có Docker stack): skip.

    Raises:
        pytest.fail() — khi CI không có Postgres.
        pytest.skip() — khi local không có Postgres.
    """
    engine = get_postgres_test_engine()
    try:
        async with engine.connect() as conn:
            await conn.run_sync(lambda c: None)
    except (OSError, asyncpg.InvalidCatalogNameError) as exc:
        # OSError bao trùm ConnectionRefusedError + socket.gaierror + TimeoutError.
        # asyncpg.InvalidCatalogNameError — sai tên DB (asyncpg không phải OSError subclass).
        await engine.dispose()
        _skip_or_fail(f"Postgres không khả dụng: {type(exc).__name__}: {exc}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


def get_postgres_test_engine() -> AsyncEngine:
    """Postgres engine cho integration tests (CI: có postgres service).

    Env vars được set trong CI job:
        POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    """
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_TEST_DB", os.environ.get("POSTGRES_DB", "ctsv_test"))
    user = os.environ.get("POSTGRES_USER", "ctsv_test")
    password = os.environ.get("POSTGRES_PASSWORD", "ctsv_test")
    url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    engine = create_async_engine(
        url,
        poolclass=NullPool,
        echo=False,
    )
    return engine


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    """Async session dùng SQLite (unit tests).

    Dùng join_transaction_mode='create_savepoint' để mỗi test tự rollback.
    """
    factory = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    async with factory() as session:
        yield session


@pytest.fixture
async def db_session_factory(db_engine, monkeypatch) -> async_sessionmaker[AsyncSession]:
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    monkeypatch.setattr("app.db.session._session_factory", factory)
    return factory


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


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
async def admin_user(db_session_factory) -> User:
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
async def staff_user(db_session_factory) -> User:
    from app.modules.auth.security import hash_password

    async with db_session_factory() as session:
        user = User(
            id="usr_staff_01",
            email="staff@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="Cán Bộ CTSV",
            role="staff",
            department="Phòng CTSV",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        yield user


@pytest.fixture
async def student_user(db_session_factory) -> User:
    from app.modules.auth.security import hash_password

    async with db_session_factory() as session:
        user = User(
            id="usr_student_01",
            email="student@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="Sinh Viên A",
            role="student",
            department="Khoa CNTT",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        yield user


def auth_headers_for(user: User) -> dict[str, str]:
    from app.modules.auth.security import create_access_token

    token = create_access_token(subject=user.id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


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
