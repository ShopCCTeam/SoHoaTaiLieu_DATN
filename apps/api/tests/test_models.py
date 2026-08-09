"""Unit tests cho ORM models — dùng SQLite in-memory."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.document_scope import DocumentScope
from app.models.user import User


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_user_persists(session) -> None:
    user = User(
        id="usr_01",
        email="admin@example.edu.vn",
        password_hash="bcrypt_hash",
        full_name="Quản Trị",
        role="admin",
        department="Phòng CTSV",
    )
    session.add(user)
    await session.commit()
    stmt = select(User).where(User.email == "admin@example.edu.vn")
    result = await session.execute(stmt)
    loaded = result.scalar_one()
    assert loaded.id == "usr_01"
    assert loaded.role == "admin"
    assert loaded.is_active is True


@pytest.mark.asyncio
async def test_email_is_unique(session) -> None:
    from sqlalchemy.exc import IntegrityError

    user1 = User(
        id="usr_01",
        email="dup@example.edu.vn",
        password_hash="h",
        full_name="A",
        role="staff",
    )
    user2 = User(
        id="usr_02",
        email="dup@example.edu.vn",
        password_hash="h",
        full_name="B",
        role="staff",
    )
    session.add(user1)
    await session.commit()
    session.add(user2)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_document_scope_seed(session) -> None:
    scope = DocumentScope(code="PUBLIC", description="Công khai toàn bộ SV")
    session.add(scope)
    await session.commit()
    loaded = await session.get(DocumentScope, scope.id)
    assert loaded is not None
    assert loaded.code_enum.value == "PUBLIC"


def test_user_tablename() -> None:
    assert User.__tablename__ == "users"


def test_document_scope_tablename() -> None:
    assert DocumentScope.__tablename__ == "document_scopes"
