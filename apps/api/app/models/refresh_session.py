"""RefreshSession ORM — lưu refresh token opaque hash + family revocation.

Map với bảng `refresh_sessions` trong migration 0002.
- id/family_id: dùng `default=uuid.uuid4` cho SQLite; `server_default` cho PG.
- ip_address: dùng `_INet` TypeDecorator (String on SQLite, INET on PG).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import CHAR, TypeDecorator

from app.db.base import Base


class _UUID(TypeDecorator[uuid.UUID]):
    """Store UUID as CHAR(36) on SQLite, UUID on PostgreSQL.

    Wrap postgresql.UUID(as_uuid=True) — SQLite không có native UUID type.
    """

    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: uuid.UUID | None, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class _INet(TypeDecorator[str]):
    """Store IP as String on SQLite, INET on PostgreSQL."""

    impl = String(45)
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(INET())
        return dialect.type_descriptor(String(45))

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        return value


class RefreshSession(Base):
    """Refresh token session với family-based rotation và reuse detection."""

    __tablename__ = "refresh_sessions"

    # id: Python-side default for both SQLite and PostgreSQL.
    # Do NOT use server_default=func.gen_random_uuid() — SQLite has no such function.
    id: Mapped[uuid.UUID] = mapped_column(
        _UUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        _UUID(),
        nullable=False,
        default=uuid.uuid4,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        _INet(),
        nullable=True,
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        _UUID(),
        ForeignKey("refresh_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RefreshSession id={self.id} family={self.family_id} "
            f"user={self.user_id} revoked={self.revoked_at is not None}>"
        )
