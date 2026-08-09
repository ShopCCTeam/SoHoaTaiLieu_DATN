"""Async SQLAlchemy engine + session factory.

Lifecycle:
- Engine: singleton, lazily created on first use.
- `get_session`: FastAPI dependency, yield session trong scope của request.
- Auto-commit khi route return thành công; rollback khi exception.

Test isolation: trong pytest, override `get_session` bằng session factory dùng
SQLite in-memory (xem `tests/conftest.py`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def create_engine(url: str | None = None, **kwargs: Any) -> AsyncEngine:
    """Tạo async engine. Có thể override URL cho test."""
    settings = get_settings()
    return create_async_engine(
        url or settings.postgres_url,
        echo=False,
        pool_pre_ping=True,
        **kwargs,
    )


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Singleton engine."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Singleton session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency. Yields session, commit/rollback handled here."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def reset_engine_for_test() -> None:
    """Reset singleton. Dùng trong test fixture khi override URL."""
    global _engine, _session_factory
    if _engine is not None:
        # async engine không dispose đồng bộ; gọi từ event loop
        pass
    _engine = None
    _session_factory = None
