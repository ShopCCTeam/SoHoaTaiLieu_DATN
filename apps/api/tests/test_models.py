"""Unit tests cho ORM models — chạy trên SQLite (in-memory).

TypeDecorator `_UUID` + `_INet` wrap PG-specific types thành String/CHAR để
SQLite chấp nhận → local dev không cần Postgres stack.

Chú ý về INET:
- Test `test_refresh_session_ip_address_roundtrip` dưới đây chỉ verify round-trip
  qua String(45) trên SQLite — KHÔNG phải bằng chứng về INET trên PG.
- Test PG roundtrip thật (UUID + INET) nằm ở `tests/test_models_pg.py`, mark
  `@pytest.mark.integration`, dùng `pg_engine` fixture (fail trong CI nếu
  Postgres không chạy, skip ngoài CI).

CI: chạy local (SQLite) cho test_models; PG roundtrip ở test_models_pg —
fail nếu Postgres không có.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models.user import User  # noqa: F401 — no PG types, OK on SQLite


def test_user_tablename() -> None:
    """Không cần Postgres."""
    assert User.__tablename__ == "users"


def test_refresh_session_tablename() -> None:
    """Verify RefreshSession.__tablename__ = 'refresh_sessions'.

    Import inline để tránh SQLite conftest tạo bảng INET/UUID khi collection.
    """
    from app.models.refresh_session import RefreshSession

    assert RefreshSession.__tablename__ == "refresh_sessions"


async def test_refresh_session_has_required_columns(
    db_engine: AsyncEngine,
) -> None:
    """Tạo + load session — verify tất cả required columns persist.

    Chạy trên SQLite qua `db_engine` (TypeDecorator _UUID + _INet).
    """
    from app.models.refresh_session import RefreshSession
    from app.modules.auth.security import hash_password

    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email="model_test@example.edu.vn",
            password_hash=hash_password("Test@2026"),
            full_name="Model Test User",
            role="staff",
            is_active=True,
        )
        session.add(user)
        await session.commit()

        rs = RefreshSession(
            id=uuid.uuid4(),
            user_id=user.id,
            family_id=uuid.uuid4(),
            token_hash="a" * 64,
            expires_at=datetime.now(UTC),
        )
        session.add(rs)
        await session.commit()

        loaded = await session.get(RefreshSession, rs.id)
        assert loaded is not None
        assert loaded.user_id == user.id
        assert loaded.token_hash == "a" * 64
        assert loaded.revoked_at is None
        assert loaded.ip_address is None  # INet null


async def test_refresh_session_ip_address_roundtrip(
    db_engine: AsyncEngine,
) -> None:
    """Verify cột IP address round-trip qua SQLite (String(45)).

    CHÚ Ý: Đây chỉ chứng minh `_INet` TypeDecorator hoạt động trên SQLite.
    Hành vi INET trên PostgreSQL được verify ở `tests/test_models_pg.py`.
    """
    from app.models.refresh_session import RefreshSession
    from app.modules.auth.security import hash_password

    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email="inet_test@example.edu.vn",
            password_hash=hash_password("Test@2026"),
            full_name="INet Test",
            role="staff",
        )
        session.add(user)
        await session.commit()

        rs = RefreshSession(
            id=uuid.uuid4(),
            user_id=user.id,
            family_id=uuid.uuid4(),
            token_hash="b" * 64,
            expires_at=datetime.now(UTC),
            ip_address="192.168.1.100",  # String trên SQLite, INET trên PG
        )
        session.add(rs)
        await session.commit()

        loaded = await session.get(RefreshSession, rs.id)
        assert loaded is not None
        assert str(loaded.ip_address) == "192.168.1.100"
