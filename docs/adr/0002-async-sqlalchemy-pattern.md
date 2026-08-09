# ADR-0002: Async SQLAlchemy Pattern

> **Status:** Accepted
> **Date:** 2026-08-09
> **Decider:** CTSV DatN Team

## Context

Backend FastAPI cần kết nối Postgres 16 với async I/O (FastAPI handler là `async def`).

Các option:

1. **Sync SQLAlchemy 2.x + `run_in_executor`** — đơn giản, nhưng block event loop khi query.
2. **Async SQLAlchemy 2.x + asyncpg** — native asyncio, đúng pattern FastAPI.
3. **SQLModel + async** — abstraction cao, nhưng thêm 1 layer, ít ecosystem cho Postgres-specific features.

## Decision

Dùng **Async SQLAlchemy 2.x + asyncpg** (option 2).

## Rationale

- FastAPI handler là `async def` → sync SQLAlchemy sẽ block event loop khi chạy query nặng.
- Asyncpg là driver Postgres nhanh nhất (theo benchmarks SQLAlchemy chính thức).
- SQLAlchemy 2.x đã ổn định cho async (sau 2.0 GA).
- Không cần SQLModel: ta cần kiểm soát Alembic migrations, pgvector column, raw SQL cho vector search.

## Pattern

- `app/db/session.py`: singleton `async_sessionmaker` bind vào `AsyncEngine`.
- `get_session()`: FastAPI dependency yield session, commit/rollback qua context manager.
- `Base` (`app/db/base.py`): declarative base, không có Flask-style mixins.
- Alembic `env.py`: đọc URL từ settings, chạy migrations qua `connection.run_sync(do_run_migrations)` để support sync Alembic API.
- Test: dùng SQLite in-memory với `aiosqlite` driver, override `get_session` dependency qua `app.dependency_overrides`.

## Consequences

- (+) Native async performance.
- (+) Alembic tự động scan `Base.metadata` cho autogenerate.
- (+) Test nhanh với SQLite, không cần Postgres thật.
- (-) Phải cẩn thận: lazy loading bị disabled trong async mode — phải eager load (`selectinload`) hoặc explicit query.
- (-) Một số pattern sync (vd: `session.execute()` trả `CursorResult`) cần `await session.execute()`.

## Refs

- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#dialect-postgresql-asyncpg
- `.cursor/rules/03-backend-api.mdc` — backend API conventions.
- `.cursor/rules/04-database-rag-ocr.mdc` — schema conventions.