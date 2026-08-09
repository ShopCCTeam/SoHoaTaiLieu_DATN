"""Test cho seed script — verify 3 demo users."""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.user import User
from app.modules.auth.seed import seed


@pytest.mark.asyncio
async def test_seed_creates_three_demo_users(db_session_factory: async_sessionmaker):
    # Patch global session factory để seed dùng db_session thay vì Postgres thật.
    from app.db import session as session_module

    session_module._session_factory = db_session_factory

    await seed()

    async with db_session_factory() as session:
        stmt = select(User).order_by(User.role)
        users = (await session.execute(stmt)).scalars().all()

    emails = {u.email for u in users}
    assert "admin@example.edu.vn" in emails
    assert "staff@example.edu.vn" in emails
    assert "student@example.edu.vn" in emails

    roles = {u.role for u in users}
    assert "admin" in roles
    assert "staff" in roles
    assert "student" in roles


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session_factory: async_sessionmaker):
    from app.db import session as session_module

    session_module._session_factory = db_session_factory

    await seed()
    await seed()  # chạy 2 lần

    async with db_session_factory() as session:
        stmt = select(User).where(User.email == "admin@example.edu.vn")
        result = await session.execute(stmt)
        # Phải chỉ có 1 row, không duplicate.
        users = result.scalars().all()
        assert len(users) == 1
