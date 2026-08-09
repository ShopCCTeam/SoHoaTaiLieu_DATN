"""Unit tests cho async session factory — chạy SQLite in-memory."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session_factory


@pytest.fixture
def sqlite_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    yield engine
    # Cleanup đồng bộ — chỉ gọi khi event loop đang chạy.
    engine.sync_engine.dispose()


@pytest.mark.asyncio
async def test_session_factory_creates_async_session(sqlite_engine):
    factory = async_sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    async with factory() as session:
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_session_commit_persists_rows(sqlite_engine):
    """Sanity check: insert row, commit, query lại → thấy row."""
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("CREATE TABLE test_t (id INTEGER PRIMARY KEY)"))
        await conn.execute(text("INSERT INTO test_t (id) VALUES (42)"))
    async with sqlite_engine.connect() as conn:
        result = await conn.execute(text("SELECT id FROM test_t"))
        assert result.scalar() == 42


def test_get_session_factory_is_singleton() -> None:
    """Singleton — 2 lần gọi trả về cùng instance."""
    factory1 = get_session_factory()
    factory2 = get_session_factory()
    assert factory1 is factory2
