"""Unit tests cho ORM models.

Model tests dùng PG engine vì RefreshSession dùng PG-specific types
(UUID, INET, gen_random_uuid). SQLite không hỗ trợ.

Local: pytest SKIP các test này (Postgres required).
CI: chạy với postgres service.
"""
from __future__ import annotations

from datetime import UTC

import pytest

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


@pytest.mark.integration
async def test_refresh_session_has_required_columns() -> None:
    """Cần Postgres vì RefreshSession dùng UUID + INET."""
    import uuid
    from datetime import datetime

    from app.db.base import Base
    from app.models.user import User
    from app.modules.auth.security import hash_password
    from tests.conftest import get_postgres_test_engine

    engine = get_postgres_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = engine.session_factory
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

        from app.models.refresh_session import RefreshSession

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
        assert loaded.ip_address is None  # INET null

    await engine.dispose()


@pytest.mark.integration
async def test_refresh_session_ip_address_inet() -> None:
    """Cần Postgres vì cột INET."""
    import uuid
    from datetime import datetime

    from app.db.base import Base
    from app.models.user import User
    from app.modules.auth.security import hash_password
    from tests.conftest import get_postgres_test_engine

    engine = get_postgres_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = engine.session_factory
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

        from app.models.refresh_session import RefreshSession

        rs = RefreshSession(
            id=uuid.uuid4(),
            user_id=user.id,
            family_id=uuid.uuid4(),
            token_hash="b" * 64,
            expires_at=datetime.now(UTC),
            ip_address="192.168.1.100",  # INET
        )
        session.add(rs)
        await session.commit()

        loaded = await session.get(RefreshSession, rs.id)
        assert loaded is not None
        assert str(loaded.ip_address) == "192.168.1.100"

    await engine.dispose()
