# apps/api — FastAPI Backend

> **Trạng thái**: Phase 1 BE — Auth (login/me) + DB migration + Docker compose.

## Stack (đã chốt ở `docs/adr/0001-backend-stack.md`, `0002-async-sqlalchemy-pattern.md`)

- Python 3.11
- FastAPI + Pydantic v2
- SQLAlchemy 2.x (async) + Alembic
- PostgreSQL 16 + pgvector
- Celery + Redis (Phase 2+)
- MinIO client (Phase 2+)
- passlib[bcrypt] + PyJWT
- Ruff + mypy + pytest

## Cấu trúc hiện tại

```
apps/api/
├── app/
│   ├── main.py                 # FastAPI factory + health checks + routers
│   ├── core/
│   │   ├── config.py           # Pydantic Settings
│   │   ├── constants.py        # Hard-coded constants
│   │   ├── enums.py            # UserRole, DocumentScopeCode
│   │   ├── errors.py           # RFC 7807 Problem Details
│   │   ├── logging.py          # structlog JSON
│   │   └── middleware.py       # RequestIdMiddleware
│   ├── db/
│   │   ├── base.py             # Declarative base
│   │   └── session.py          # async engine + session factory
│   ├── models/
│   │   ├── user.py             # User ORM
│   │   └── document_scope.py   # DocumentScope lookup table
│   └── modules/
│       └── auth/
│           ├── router.py       # /auth/login + /auth/me
│           ├── schemas.py      # LoginRequest, LoginResponse, UserPublic
│           ├── security.py     # bcrypt + JWT helpers
│           ├── service.py      # authenticate()
│           ├── dependencies.py # get_current_user
│           └── seed.py         # 3 demo users (admin/staff/student)
├── alembic/
│   ├── env.py                  # Async-aware
│   └── versions/
│       └── 0001_users_and_scopes.py
├── tests/                       # 49 tests (unit + integration với SQLite)
└── pyproject.toml
```

## Setup local với Docker (recommended)

```bash
# Từ root repo:
cp .env.example .env  # chỉnh nếu cần
make up                # Postgres + Redis + MinIO + API lên

# Đợi ~10s cho Postgres healthcheck xong:
make seed              # seed 3 demo users

# Check
curl http://localhost:8000/health/live

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.edu.vn","password":"Demo@2026"}' | jq -r .data.access_token)

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
```

## Setup local không có Docker (dev only — cần Postgres cài local)

```bash
cd apps/api
uv sync --extra dev

# Set env vars thủ công (xem .env.example):
export POSTGRES_HOST=localhost
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
# ...

uv run alembic upgrade head    # apply migrations
uv run python -m app.modules.auth.seed  # seed demo users

uv run uvicorn app.main:app --reload --port 8000
```

## Endpoints hiện có (Phase 1)

| Method | Path                    | Mục đích                       | Auth |
|--------|-------------------------|--------------------------------|------|
| GET    | `/`                     | Service metadata               | -    |
| GET    | `/health/live`          | Liveness probe                 | -    |
| GET    | `/health/ready`         | Readiness probe                | -    |
| POST   | `/api/v1/auth/login`    | Đăng nhập → access_token       | -    |
| GET    | `/api/v1/auth/me`       | Thông tin user hiện tại        | Bearer |
| GET    | `/docs`                 | Swagger UI                     | -    |
| GET    | `/openapi.json`         | OpenAPI 3.1 schema             | -    |

## Test strategy

- `pytest` 49 tests, dùng SQLite in-memory (driver `aiosqlite`) cho unit + integration.
- Override `get_session` dependency qua `app.dependency_overrides` để không cần Postgres thật.
- pgvector-specific test sẽ thêm khi Phase 2 cần.

```bash
cd apps/api
uv run pytest
uv run pytest --cov=app
```
