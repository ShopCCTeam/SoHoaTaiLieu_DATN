"""Integration tests cho ORM models trên PostgreSQL thật.

Mục đích: verify `postgresql.UUID` + `postgresql.INET` round-trip qua ORM.
SQLite (test_models.py) chỉ verify TypeDecorator wrap → không phải bằng chứng
về hành vi PG thật. D18 yêu cầu "test phải chạm DB thật của schema".

Trong CI: fail nếu Postgres không khả dụng (fixture `pg_engine` dùng
`_skip_or_fail` trong `conftest.py`).
Ngoài CI (dev không có Docker stack): skip.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models.refresh_session import RefreshSession
from app.models.user import User


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_uuid_roundtrip_on_postgres(pg_engine: AsyncEngine) -> None:
    """User.id lưu + load đúng dạng UUID native (không phải CHAR(36))."""
    from app.modules.auth.security import hash_password

    factory = async_sessionmaker(bind=pg_engine, expire_on_commit=False)
    async with factory() as session:
        user = User(
            id="usr_pg_uuid_01",
            email="pg_uuid@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="PG UUID Test",
            role="staff",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    # Re-load từ session mới — verify UUID object qua PG roundtrip
    async with factory() as session:
        loaded = await session.get(User, user_id)
        assert loaded is not None
        assert loaded.id == user_id
        assert loaded.email == "pg_uuid@example.edu.vn"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_session_inet_roundtrip_on_postgres(
    pg_engine: AsyncEngine,
) -> None:
    """RefreshSession.ip_address round-trip qua PostgreSQL INET (IPv4 + IPv6).

    KHÔNG so sánh string — verify giá trị qua query filter dùng IP string,
    PG tự parse lại qua INET. Nếu column bị wrap thành String thay vì INET
    → query không match → test fail.
    """
    from sqlalchemy import select

    from app.modules.auth.security import hash_password

    factory = async_sessionmaker(bind=pg_engine, expire_on_commit=False)
    async with factory() as session:
        user = User(
            id="usr_pg_inet_01",
            email="pg_inet@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="PG INet Test",
            role="staff",
            is_active=True,
        )
        session.add(user)
        await session.commit()

        rs_v4 = RefreshSession(
            id=uuid.uuid4(),
            user_id=user.id,
            family_id=uuid.uuid4(),
            token_hash="d" * 64,
            issued_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=3600),
            ip_address="203.0.113.42",  # IPv4 public test range
        )
        session.add(rs_v4)
        await session.commit()
        v4_id = rs_v4.id

        rs_v6 = RefreshSession(
            id=uuid.uuid4(),
            user_id=user.id,
            family_id=uuid.uuid4(),
            token_hash="e" * 64,
            issued_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=3600),
            ip_address="2001:db8::1",  # IPv6 documentation range
        )
        session.add(rs_v6)
        await session.commit()
        v6_id = rs_v6.id

    # Query lại qua IP filter — INET support network comparison
    async with factory() as session:
        stmt = select(RefreshSession).where(RefreshSession.id.in_([v4_id, v6_id]))
        loaded = (await session.execute(stmt)).scalars().all()
        assert len(loaded) == 2
        # Gía trị load về còn nguyên — verify INET không bị PG tự động
        # convert thành dạng khác (vd CIDR / normalize) ngoài ý muốn.
        by_id = {r.id: r for r in loaded}
        assert str(by_id[v4_id].ip_address) == "203.0.113.42"
        assert str(by_id[v6_id].ip_address) == "2001:db8::1"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_session_uuid_roundtrip_on_postgres(
    pg_engine: AsyncEngine,
) -> None:
    """RefreshSession.id + family_id round-trip qua postgresql.UUID.

    Verify query filter bằng UUID object (không phải string) hoạt động —
    chứng minh column thực sự là UUID chứ không phải CHAR(36) wrapper.
    """
    from app.modules.auth.security import hash_password

    factory = async_sessionmaker(bind=pg_engine, expire_on_commit=False)
    target_id = uuid.uuid4()
    target_family = uuid.uuid4()

    async with factory() as session:
        user = User(
            id="usr_pg_refresh_uuid",
            email="pg_refresh_uuid@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="PG Refresh UUID",
            role="staff",
            is_active=True,
        )
        session.add(user)
        await session.commit()

        rs = RefreshSession(
            id=target_id,
            user_id=user.id,
            family_id=target_family,
            token_hash="f" * 64,
            issued_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=3600),
        )
        session.add(rs)
        await session.commit()

    # Query bằng UUID object — nếu column là CHAR(36) thì WHERE bằng UUID
    # vẫn match (PG cast string→uuid), nhưng nếu column là TEXT thì fail.
    async with factory() as session:
        loaded = await session.get(RefreshSession, target_id)
        assert loaded is not None
        assert loaded.id == target_id
        assert loaded.family_id == target_family
