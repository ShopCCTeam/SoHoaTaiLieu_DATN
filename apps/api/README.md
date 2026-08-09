# apps/api — FastAPI Backend

> **Trạng thái**: scaffold. Chưa có code. Sẽ viết ở Phase 0 BE sau khi được phê duyệt plan.

## Stack (đã chốt ở `docs/adr/0001-backend-stack.md`)

- Python 3.11
- FastAPI + Pydantic v2
- SQLAlchemy 2.x (async) + Alembic
- PostgreSQL 16 + pgvector
- Celery + Redis
- MinIO client
- Ruff + mypy + pytest

## Cấu trúc dự kiến

```
apps/api/
├── app/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── core/                    # config, security, database, logging
│   ├── modules/                 # auth, users, documents, ocr, search, rag, admin, audit
│   ├── storage/                 # MinIO client
│   └── workers/                 # Celery app + tasks
├── tests/
├── pyproject.toml
└── .env.example                 # sẽ reference ../../.env.example
```

## Khi nào bắt đầu code

Sẽ bắt đầu sau khi có lệnh "Bắt đầu Phase 0 BE" từ user. Phase 0 bao gồm:
1. `pyproject.toml` + `uv` setup
2. `app/main.py` + health check
3. `app/core/config.py` (Pydantic Settings)
4. `app/core/database.py` (SQLAlchemy async engine)
5. Alembic init + migration đầu tiên (users + documents)
6. `/auth/login` + `/auth/me` (JWT issue)
7. `/documents` GET (RBAC check + scope filter)

Trước khi code, đọc:
- `docs/api/README.md`
- `docs/api/openapi.yaml`
- `docs/domain/rbac-matrix.md`
- `docs/domain/document-lifecycle.md`
- `.cursor/rules/03-backend-api.mdc`
- `.cursor/rules/08-governance.mdc`
