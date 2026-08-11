"""Declarative base cho ORM models.

Single source of truth — Alembic tự động scan `Base.metadata` để generate migrations.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base. Tất cả ORM models kế thừa từ đây."""
