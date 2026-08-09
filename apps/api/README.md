# apps/api — FastAPI Backend

> **Trạng thái**: Phase 0 BE — scaffold. Có health checks, settings, RFC 7807 errors.

## Stack (đã chốt ở `docs/adr/0001-backend-stack.md`)

- Python 3.11
- FastAPI + Pydantic v2
- SQLAlchemy 2.x (async) + Alembic
- PostgreSQL 16 + pgvector
- Celery + Redis
- MinIO client
- Ruff + mypy + pytest

## Cấu trúc hiện tại

```
apps/api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI factory + health checks
│   └── core/
│       ├── config.py           # Pydantic Settings
│       ├── constants.py        # Hard-coded constants
│       ├── errors.py           # RFC 7807 Problem Details
│       ├── logging.py          # structlog JSON
│       └── middleware.py       # RequestIdMiddleware
├── tests/
│   ├── test_config.py
│   ├── test_errors.py
│   └── test_health.py
├── pyproject.toml              # Ruff + mypy + pytest config
└── README.md
```

## Setup local

```bash
# Cài uv (https://github.com/astral-sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Tạo venv + install
cd apps/api
uv sync --extra dev

# Chạy
uv run uvicorn app.main:app --reload --port 8000

# Tests + lint + typecheck
uv run pytest
uv run ruff check
uv run mypy app
```

## Endpoints hiện có (Phase 0)

| Method | Path           | Mục đích                             |
|--------|----------------|--------------------------------------|
| GET    | `/`            | Service metadata                     |
| GET    | `/health/live` | Liveness probe                       |
| GET    | `/health/ready`| Readiness probe (chưa check DB/Redis)|
| GET    | `/docs`        | Swagger UI (auto-generated)          |
| GET    | `/openapi.json`| OpenAPI 3.1 schema                   |

Mọi error trả về RFC 7807 `application/problem+json` với các field:
`type`, `title`, `status`, `detail`, `code`, `request_id`, optional `errors[]`.

## Test strategy

- `pytest` unit + integration.
- Integration tests dùng TestClient của FastAPI (in-process).
- Database tests dùng `pytest-asyncio` + `asyncpg` (Phase 1 trở đi).

## Khi nào tiếp Phase 1

Sau khi commit này có CI xanh + commit Phase 0 BE được review:
- `/auth/login` + `/auth/refresh` (JWT issue + cookie rotation)
- Alembic init + migration đầu tiên (users + scopes)
- `/documents` GET với RBAC + scope filter
