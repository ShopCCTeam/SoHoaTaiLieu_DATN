"""Test cho seed script — verify 3 demo users và --reset."""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.user import User
from app.modules.auth.seed import DEMO_EMAILS, seed


@pytest.mark.asyncio
async def test_seed_creates_three_demo_users(db_session_factory: async_sessionmaker) -> None:
    # Patch global session factory để seed dùng db_session thay vì Postgres thật.
    from app.db import session as session_module

    session_module._session_factory = db_session_factory

    await seed()

    async with db_session_factory() as session:
        stmt = select(User).order_by(User.role)
        users = (await session.execute(stmt)).scalars().all()

    emails = {u.email for u in users}
    for email in DEMO_EMAILS:
        assert email in emails

    roles = {u.role for u in users}
    assert "admin" in roles
    assert "staff" in roles
    assert "student" in roles


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session_factory: async_sessionmaker) -> None:
    from app.db import session as session_module

    session_module._session_factory = db_session_factory

    await seed()
    await seed()  # chạy 2 lần

    async with db_session_factory() as session:
        stmt = select(User).where(User.email == "admin@example.edu.vn")
        result = await session.execute(stmt)
        users = result.scalars().all()
        assert len(users) == 1


@pytest.mark.asyncio
async def test_seed_reset_deletes_and_reseeds(db_session_factory: async_sessionmaker) -> None:
    from app.db import session as session_module

    session_module._session_factory = db_session_factory

    # Seed lần 1
    await seed()

    # Verify có user
    async with db_session_factory() as session:
        stmt = select(User).where(User.email == "admin@example.edu.vn")
        result = await session.execute(stmt)
        assert result.scalar_one_or_none() is not None

    # Reset + seed lại
    await seed(reset=True)

    # Verify vẫn còn user
    async with db_session_factory() as session:
        stmt = select(User).where(User.email == "admin@example.edu.vn")
        result = await session.execute(stmt)
        assert result.scalar_one_or_none() is not None
