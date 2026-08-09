# Phase 1 BE: Auth + DB Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans để implement task-by-task.

**Goal:** `/auth/login` + `/auth/me` thật (JWT + Postgres) + Alembic init với `users` + `document_scopes`.

**Architecture:**
- Backend FastAPI app đã có scaffold (commit `fcdc84c`). Phase 1 thêm DB layer (SQLAlchemy 2.x async + Alembic), auth module (bcrypt + HS256 JWT), Docker Compose cho local dev.
- FE giữ nguyên (mock auth đã RFC 7807 compliant — khi BE chạy, chỉ cần flip `NEXT_PUBLIC_API_MODE=live`).

**Tech Stack:**
- Python 3.11 + FastAPI 0.115+ + Pydantic v2.
- SQLAlchemy 2.x async + Alembic.
- PostgreSQL 16 + pgvector (chỉ cần extension để Phase 2 dùng).
- passlib[bcrypt] + PyJWT.
- Docker Compose (Postgres + Redis + MinIO + API).
- Pytest + pytest-asyncio + httpx (test client).

**Out of scope (Phase 2+):**
- `/documents` GET + RBAC đầy đủ.
- Refresh token rotation (Phase 1 chỉ issue access token, không có refresh).
- pgvector tables (`embeddings`, `chat_messages`).
- Celery worker.

---

## Task 1: Pydantic `EmailStr` + DB engine factory

**Files:**
- Modify: `apps/api/pyproject.toml` (thêm `email-validator`).
- Create: `apps/api/app/db/__init__.py`.
- Create: `apps/api/app/db/session.py` (async engine + `get_session`).
- Create: `apps/api/app/db/base.py` (declarative base).
- Test: `apps/api/tests/test_db_session.py`.

**Step 1 — Test fail**: `tests/test_db_session.py::test_get_session_yields_async_session` — expect session có thể execute `SELECT 1`.

**Step 2 — Run**: `cd apps/api && uv run pytest tests/test_db_session.py -v` → FAIL (module not found).

**Step 3 — Implement**: Tạo `session.py` với `create_async_engine(settings.postgres_url)`, `async_sessionmaker`, dependency `get_session` yield `AsyncSession`.

**Step 4 — Run**: PASS.

**Step 5 — Commit**: `chore(be): async SQLAlchemy session factory`.

---

## Task 2: ORM models — User + DocumentScope

**Files:**
- Create: `apps/api/app/models/__init__.py`.
- Create: `apps/api/app/models/user.py`.
- Create: `apps/api/app/models/document_scope.py`.
- Create: `apps/api/app/core/enums.py` (`UserRole`, `DocumentScopeCode`).
- Test: `apps/api/tests/test_models.py`.

**Step 1 — Test fail**: `test_models.User.__tablename__ == "users"`, `test_models.User.email` UNIQUE constraint enforced.

**Step 2 — Run**: FAIL.

**Step 3 — Implement**: User UUID PK (uuid7 lib — fallback uuid4 nếu chưa có 3.14), email UNIQUE, password_hash, full_name, role enum (`admin`/`staff`/`student`), department, is_active, created_at, updated_at (server_default + onupdate). DocumentScope id + code UNIQUE enum (`PUBLIC`/`STUDENT_AFFAIRS`/`INTERNAL`) + description.

**Step 4 — Run**: PASS.

**Step 5 — Commit**: `feat(be): User + DocumentScope ORM models`.

---

## Task 3: Alembic init + async env

**Files:**
- Create: `apps/api/alembic.ini`.
- Create: `apps/api/alembic/env.py` (async-aware).
- Create: `apps/api/alembic/script.py.mako`.
- Create: `apps/api/alembic/versions/0001_users_and_scopes.py`.

**Step 1 — Test fail**: `cd apps/api && uv run alembic check` → FAIL (no migrations).

**Step 2 — Run**: FAIL.

**Step 3 — Implement**:
- `alembic.ini` standard.
- `env.py` async: dùng `create_async_engine`, `connection.run_sync(do_run_migrations)`.
- `0001_users_and_scopes.py` tạo `users` + `document_scopes`, seed 3 rows cho scopes.

**Step 4 — Run**: `uv run alembic upgrade head` (cần Postgres — xem Task 4 cho Docker setup trước) → PASS.

**Step 5 — Commit**: `feat(be): alembic init + users + document_scopes migration`.

---

## Task 4: Docker Compose cho local dev

**Files:**
- Create: `infra/docker/docker-compose.yml`.
- Create: `infra/docker/Dockerfile.api` (dev target, bind mount).
- Create: `.env.example` ở root (update nếu đã có).
- Create: `Makefile` ở root.
- Modify: `apps/api/pyproject.toml` (thêm `aiosqlite` cho test).

**Step 1 — Verify**: `docker compose -f infra/docker/docker-compose.yml config` → OK.

**Step 2 — Run**: `make up` → Postgres + Redis + MinIO + API container chạy.

**Step 3 — Implement**:
- `docker-compose.yml`: services `postgres` (image `pgvector/pgvector:pg16`), `redis`, `minio`, `api` (build từ Dockerfile.api, bind mount source, command `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`). Healthcheck cho Postgres.
- `Dockerfile.api`: Python 3.11-slim, cài uv, copy `pyproject.toml` + sync, copy source.
- `.env.example`: `POSTGRES_PASSWORD`, `JWT_SECRET`, etc.
- `Makefile`: `up`, `down`, `logs`, `db-shell`, `api-shell`, `seed`, `test`.

**Step 4 — Verify**: `curl http://localhost:8000/health/live` → 200.

**Step 5 — Commit**: `chore(infra): docker compose cho local dev (postgres+redis+minio+api)`.

---

## Task 5: Auth module — security primitives

**Files:**
- Create: `apps/api/app/modules/__init__.py`.
- Create: `apps/api/app/modules/auth/__init__.py`.
- Create: `apps/api/app/modules/auth/security.py`.
- Test: `apps/api/tests/test_auth_security.py`.

**Step 1 — Test fail**: `test_hash_password_and_verify_roundtrip`, `test_create_and_decode_jwt_roundtrip`, `test_decode_expired_jwt_raises`.

**Step 2 — Run**: FAIL.

**Step 3 — Implement**: `hash_password(plain) -> str` (bcrypt cost ≥ 12), `verify_password(plain, hash) -> bool`, `create_access_token(subject: str, role: UserRole, ttl_seconds: int) -> str`, `decode_access_token(token: str) -> dict`.

**Step 4 — Run**: PASS.

**Step 5 — Commit**: `feat(be): password hashing + JWT security primitives`.

---

## Task 6: Auth service + dependency

**Files:**
- Create: `apps/api/app/modules/auth/schemas.py`.
- Create: `apps/api/app/modules/auth/service.py`.
- Create: `apps/api/app/modules/auth/dependencies.py`.
- Test: `apps/api/tests/test_auth_service.py`.

**Step 1 — Test fail**: `test_authenticate_returns_user_on_valid_credentials`, `test_authenticate_returns_none_on_wrong_password`, `test_authenticate_returns_none_on_inactive_user`, `test_get_current_user_returns_user_on_valid_token`, `test_get_current_user_raises_401_on_missing_token`, `test_get_current_user_raises_401_on_invalid_token`.

**Step 2 — Run**: FAIL.

**Step 3 — Implement**:
- `schemas.py`: `LoginRequest(email: EmailStr, password: str)`, `UserPublic(...)` (match OpenAPI `User`), `LoginResponse(access_token, expires_in, user)`, `MeResponse(user)`.
- `service.py`: `authenticate(session, email, password) -> User | None`. Wrap trong `get_user_by_email`.
- `dependencies.py`: `get_current_user(session = Depends(get_session), token: str = Depends(oauth2_scheme)) -> User` — 401 nếu token invalid/expired, 401 nếu user không tồn tại hoặc inactive.

**Step 4 — Run**: PASS (dùng SQLite in-memory + seed fixture).

**Step 5 — Commit**: `feat(be): auth service + current-user dependency`.

---

## Task 7: Auth router — `/auth/login` + `/auth/me`

**Files:**
- Create: `apps/api/app/modules/auth/router.py`.
- Modify: `apps/api/app/main.py` (include router).

**Step 1 — Test fail**: `tests/test_auth_router.py::test_login_success_returns_access_token`, `test_login_wrong_password_returns_401`, `test_login_unknown_email_returns_401`, `test_login_validation_error_returns_422`, `test_me_with_valid_token_returns_user`, `test_me_without_token_returns_401`, `test_me_with_invalid_token_returns_401`.

**Step 2 — Run**: FAIL.

**Step 3 — Implement**:
- `router.py`: `POST /auth/login` (LoginRequest → LoginResponse + set refresh cookie optional Phase 1), `GET /auth/me` (Bearer required, return UserPublic).
- `main.py`: `app.include_router(auth_router, prefix="/api/v1")`.

**Step 4 — Run**: `uv run pytest tests/test_auth_router.py -v` → PASS.

**Step 5 — Commit**: `feat(be): /auth/login + /auth/me endpoints`.

---

## Task 8: Demo user seed script

**Files:**
- Create: `apps/api/app/modules/auth/seed.py`.

**Step 1 — Test**: `tests/test_auth_seed.py::test_seed_creates_three_demo_users`.

**Step 2 — Run**: FAIL.

**Step 3 — Implement**: CLI script tạo 3 user (admin/staff/student, password `Demo@2026`). `python -m app.modules.auth.seed`.

**Step 4 — Run**: PASS.

**Step 5 — Commit**: `feat(be): demo user seed script`.

---

## Task 9: OpenAPI verify + docs

**Files:**
- Create: `docs/adr/0002-async-sqlalchemy-pattern.md`.
- Modify: `apps/api/README.md` (Docker setup section).
- Modify: `AGENTS.md`.
- Modify: `docs/PROGRESS.md`.

**Step 1 — Run**: `python -c "from app.main import create_app; import json; print(json.dumps(create_app().openapi(), indent=2))" > /tmp/runtime-openapi.json`.

**Step 2 — Run**: `npx oasdiff breaking /tmp/runtime-openapi.json docs/api/openapi.yaml` → check xem có endpoint mới nào CHƯA có trong YAML.

**Step 3 — Verify**: Nếu mismatch → update YAML trước, regenerate contracts, rồi commit.

**Step 4 — Commit**: `docs: phase 1 BE ADR + README + PROGRESS`.

---

## Task 10: Final verify + commit

**Verify**:
- `pnpm check` (FE) PASS.
- `pnpm api:test` PASS (~40 tests).
- `pnpm api:lint` + `pnpm api:mypy` clean.
- `make up` → docker stack healthy.
- `curl /health/live`, `curl /api/v1/auth/login`, `curl /api/v1/auth/me` đều đúng status.

**Commit**: `chore(be): Phase 1 — Auth + DB migration + Docker compose`.

---

## Verification Commands Reference

```bash
# Lint + typecheck + test BE
cd apps/api
uv run ruff check app tests
uv run mypy app
uv run pytest -v

# Local dev stack
cd ../..
make up
make logs
make api-shell  # bash inside api container

# Manual API test
curl http://localhost:8000/health/live
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.edu.vn","password":"Demo@2026"}' | jq -r .data.access_token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me

# Run migration
make api-shell
uv run alembic upgrade head
```

## Risk Notes

- **uuid7 chưa có trong Python <3.14**: dùng `uuid.uuid4()` cho Phase 1. Sẽ chuyển `uuid.uuid7()` khi nâng Python.
- **bcrypt 72-byte limit**: `Demo@2026` (9 chars) an toàn.
- **OpenAPI schema drift**: Phase 1 chưa thêm endpoint mới ngoài scope OpenAPI hiện tại (login + me đã có trong YAML). Nếu schema drift, cập nhật YAML trước.
- **CORS**: dev chỉ allow `http://localhost:3000`. Production cần update env.
- **JWT secret dev**: đã đặt default placeholder trong Settings. Production phải set qua secret manager.