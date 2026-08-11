"""Alembic env — async-aware.

Đọc connection URL từ `app.core.config.get_settings().postgres_url`.
Sync wrapper chạy migrations qua `connection.run_sync()`.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.models.document_scope import DocumentScope  # noqa: F401

# Tất cả ORM models phải import ở đây để Base.metadata nhận đủ schema.
# MỚI thêm model → thêm import.
from app.models.user import User  # noqa: F401

# Alembic Config object.
config = context.config

# Setup logging từ alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata cho autogenerate.
target_metadata = Base.metadata


def _resolve_database_url() -> str:
    """Lấy URL từ alembic config (nếu set) hoặc fallback Settings.

    Ưu tiên URL từ alembic config để:
    - Cho phép test chạy offline với SQLite mà không cần Postgres thật.
    - Cho phép override khi chạy `alembic` CLI với `-x url=...`.
    """
    cfg_url = context.config.get_main_option("sqlalchemy.url")
    if cfg_url:
        return cfg_url
    return get_settings().postgres_url


def run_migrations_offline() -> None:
    """Chạy migrations ở 'offline' mode — sinh SQL script không cần DB."""
    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Chạy migrations ở 'online' mode qua async engine."""
    url = _resolve_database_url()
    # Nếu URL là sqlite (test mode) → dùng sync engine.
    if url.startswith("sqlite"):
        from sqlalchemy import create_engine

        engine = create_engine(url)
        with engine.connect() as connection:
            do_run_migrations(connection)
        engine.dispose()
        return
    # Production: async engine + asyncpg.
    engine = create_async_engine(url, echo=False)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
