# Nhật ký Tiến độ Dự án

> File log tiến độ từng Phase. Cập nhật theo format dưới. Mỗi Phase có mục riêng.

---

## 2026-08-09 — Phase 0 BE + FE Contract Sync

**Việc đã làm**:

- **Fix theo đợt review "chưa thể GO hoàn toàn"**:
  - Sửa OpenAPI description: chốt `openapi.yaml` là contract chuẩn, KHÔNG ghi đè từ implementation, dùng `oasdiff` để so sánh runtime schema.
  - Sửa CI guard `pyproject.toml` (đường dẫn tương đối với working-dir).
  - **Tạo `packages/contracts` với `openapi-typescript`**: generate TypeScript types trực tiếp từ `docs/api/openapi.yaml`. FE import `@ctsv/contracts` thay vì khai báo tay.
  - **Viết lại `apps/web/lib/api/types.ts`** dùng schema đã chốt (UPPER_SNAKE enum, snake_case field).
  - **`apps/web/lib/api/mappers.ts`** mới: snake_case DTO → camelCase domain model (FE-side). Mọi query hook đi qua mapper.
  - **Mock auth fix**:
    - Bỏ fallback admin khi email không tồn tại → 401 RFC 7807.
    - Xác thực password (`Demo@2026`).
    - Mock route `auth/login` trả `access_token` + `expires_in` + `user` + set HttpOnly cookie `rt`.
    - `getMockUserFromRequest()` exact token match (base64url decode role:email), KHÔNG substring `staff`/`student`.
  - **`apiClient` rewrite**: unwrap `{success, data}` envelope; error response nhận diện `application/problem+json` → ném `ApiError` chứa `ProblemDetail`.
  - Tất cả mock route (auth/me, documents, search, chat/query, admin/users, admin/models): trả envelope shape khớp OpenAPI.
  - Component FE (status-badge, document-table, metadata-form, upload-dropzone, version-list, chat-thread, dashboard) đã migrate sang enum mới.
  - Fixtures (`MOCK_DOCUMENTS`/`MOCK_VERSIONS`/`MOCK_OCR_BLOCKS`) đồng bộ theo UPPER_SNAKE enum + bổ sung OCR review fields + bbox PDF coordinate.

- **Tạo Phase 0 BE scaffold** (`apps/api/`):
  - `pyproject.toml`: FastAPI + Pydantic v2 + SQLAlchemy + Alembic + Celery + boto3 + uv.
  - `app/main.py`: app factory + health checks (`/health/live`, `/health/ready`).
  - `app/core/config.py`: Pydantic Settings (12-factor, `.env` load, SecretStr).
  - `app/core/errors.py`: RFC 7807 Problem Details + ApiError + `register_exception_handlers`.
  - `app/core/logging.py`: structlog JSON, 1 event/line.
  - `app/core/middleware.py`: RequestIdMiddleware (uuid v4 cho Phase 0, uuid v7 ở Python 3.14+).
  - 20 tests pytest pass; ruff + mypy strict pass.
  - `tests/test_config.py`, `tests/test_errors.py`, `tests/test_health.py`.

**Trạng thái sau commit này**:
- ✅ FE TypeScript types = 1:1 với OpenAPI (sinh tự động).
- ✅ FE queries chạy qua mapper (snake→camel).
- ✅ Mock auth: no fallback admin, RFC 7807 401, HttpOnly cookie.
- ✅ `pnpm check` PASS (FE 26/26 test + lint + typecheck + openapi:lint + build).
- ✅ `pnpm api:test` PASS (BE 20/20 test + ruff + mypy).
- ✅ Có thể bắt đầu Phase 1: `/auth/login` + Alembic init + `/documents` GET.

**Không còn "chỉ cần đổi env, không cần refactor FE"** — FE đã có lớp contract/mapper chuẩn.

**Commit kế tiếp**: `phase-1-auth-db` (viết `/auth/login` thật + Alembic init + users table).

---

## 2026-08-10 — Phase 1.1: Auth Hardening (Refresh Rotation + Argon2id)

**Việc đã làm**:

- **Argon2id** (D7): `pwdlib[argon2]>=0.3.0` thay bcrypt. `hash_password`/`verify_password` dùng `Argon2Hasher`. Dummy hash ổn định.
- **RefreshSession model** (D1): SQLite-compatible (`default=uuid.uuid4` + `_INet` TypeDecorator). Import vào `models/__init__.py`.
- **Rotation service** (`refresh_service.py`, D4): `SELECT FOR UPDATE` lock + atomic conditional `UPDATE WHERE`. Reuse detection qua `revoked_at` lookup.
- **Auth router**: `/auth/refresh` (rotation) + `/auth/logout` (revoke) + `/auth/login` (tạo session). Router commit một lần (D5).
- **Cookie**: Starlette `set_cookie`/`delete_cookie` — HttpOnly + SameSite=Lax + Secure(prod) + Path.
- **Origin-CSRF** (D11): refresh + logout check Origin header; reject missing/unexpected.
- **Structured audit** (D12): structlog JSON cho auth events (login success/failed, refresh rotated/reuse, logout).
- **Config fail-closed** (D9): `validate_production()` check JWT secret default, cookie secure, postgres password.
- **Seed guard** (D17): refuse seed ở production/staging.
- **`/health/ready`** (D10): `SELECT 1` Postgres thật, timeout 5s, trả 503 nếu fail.
- **CI**: postgres service + alembic upgrade/downgrade + coverage XML + oasdiff (pin version).
- **Tests**: 18 auth tests mới (reuse detection, cookie headers, Origin-CSRF, logout idempotent, DB session creation).
- **Fix linting**: 28 ruff errors → 0 (auto-fix + thủ công). mypy 18 errors → 0.

**Trạng thái sau Phase 1.1**:
> ⚠️ **Phase 1.1 CHƯA đóng** — chỉ có bằng chứng SQLite. Postgres/Docker/CI chưa chạy.

| Gate | Status | Evidence |
|---|---|---|
| Static | ✅ | ruff 0 errors + mypy 0 errors |
| Unit | ✅ | 84 passed, 4 deselected (Postgres integration — marker filter, không phải skip) |
| Postgres | ⚠️ | CHƯA chạy alembic upgrade trên PG thật; máy local chưa có Docker |
| Docker | ⚠️ | CHƯA start docker stack |
| CI | ⚠️ | CHƯA chạy GitHub Actions với postgres service |

> Kết luận: Phase 1.1 **CHƯA đóng** vì chưa có bằng chứng Postgres thật. Chỉ đánh ✅ Static + Unit (SQLite in-memory).

**ADR**: `docs/adr/0003-auth-hardening.md` (đã commit trước implementation).

**Risk**:
- ⚠️ Docker chưa có → Phase 1.2 gate user chạy thủ công.
- ⚠️ Demo users cần `seed --reset` sau khi chuyển argon2id.
- ⚠️ Audit dùng structured log; audit_logs table còn pending.

**Commit kế tiếp**: Phase 1.2 — Runtime Verification (docker stack, alembic PG, oasdiff, coverage ≥ 80%).


---

## 2026-08-09 — Phase 1 BE: Auth + DB Migration + Docker

**Việc đã làm**:

- **Database layer** (`apps/api/app/db/`):
  - `base.py`: SQLAlchemy 2.x declarative base.
  - `session.py`: async engine singleton + `get_session` FastAPI dependency (commit on success, rollback on exception).

- **ORM models** (`apps/api/app/models/`):
  - `user.py`: User (UUID PK, email UNIQUE, password_hash, full_name, role, department, is_active, created_at, updated_at).
  - `document_scope.py`: DocumentScope lookup (PUBLIC / STUDENT_AFFAIRS / INTERNAL).
  - `app/core/enums.py`: UserRole + DocumentScopeCode `StrEnum`.

- **Alembic** (`apps/api/alembic/`):
  - `alembic.ini` + async-aware `env.py` (URL override cho SQLite test).
  - `versions/0001_users_and_scopes.py`: tạo users + document_scopes + seed 3 scopes.

- **Auth module** (`apps/api/app/modules/auth/`):
  - `security.py`: `hash_password`/`verify_password` (bcrypt cost ≥ 12), `create_access_token`/`decode_access_token` (HS256).
  - `schemas.py`: LoginRequest, UserPublic, LoginResponse, MeResponse.
  - `service.py`: `authenticate()` + `get_user_by_email()` + `get_user_by_id()`.
  - `dependencies.py`: `get_current_user` (Bearer token → 401 RFC 7807 với code cụ thể).
  - `router.py`: `POST /api/v1/auth/login` + `GET /api/v1/auth/me` (envelope `{success, data}`).
  - `seed.py`: CLI tạo 3 demo users (admin/staff/student, password `Demo@2026`).

- **Wire-up**: `app/main.py` include auth router với prefix `/api/v1`.

- **Error helpers** (`app/core/errors.py`):
  - `unauthorized()` / `forbidden()` / `not_found()` accept optional `code=` override cho ngữ cảnh cụ thể (AUTH_INVALID_CREDENTIALS, AUTH_TOKEN_EXPIRED, ...).

- **Infra** (`infra/docker/`):
  - `docker-compose.yml`: pgvector/pgvector:pg16 + redis:7-alpine + minio + api (bind mount source).
  - `Dockerfile.api`: Python 3.11-slim + uv + FastAPI dev.
  - `Makefile` ở root: `make up/down/logs/db-shell/api-shell/seed/test/lint/typecheck/check`.
  - `.env.example` (root) — full env contract cho local dev.

- **Plan**: `docs/plans/2026-08-09-phase-1-be-auth-db.md` (writing-plans skill).
- **ADR**: `docs/adr/0002-async-sqlalchemy-pattern.md` — chốt async SQLAlchemy + asyncpg.

- **Tests**: 49 pass (từ 20 ở Phase 0).
  - `tests/test_db_session.py` (3), `tests/test_models.py` (5), `tests/test_alembic.py` (2), `tests/test_auth_security.py` (7), `tests/test_auth_router.py` (10), `tests/test_auth_seed.py` (2) — và 20 tests cũ.

**Trạng thái sau commit này**:
- ✅ 49 pytest pass.
- ✅ ruff clean (B008 ignore cho FastAPI Depends — idiomatic).
- ✅ mypy strict clean.
- ✅ `pnpm check` PASS (FE 26/26 + lint + typecheck + openapi:lint + build).
- ✅ OpenAPI runtime schema sync với contract: `/api/v1/auth/login`, `/api/v1/auth/me`.
- ✅ Docker compose file cho local dev (cần Docker để chạy — Windows hiện không có Docker, dùng SQLite test cho CI/local verify).

**Verify gate (Phase 1 — STATE AT 2026-08-09 21:30)**:

| Verify type | Status | Evidence |
|---|---|---|
| Static verified | ✅ | ruff + mypy strict clean |
| Unit verified | ✅ | 49/49 tests pass (SQLite in-memory via aiosqlite) |
| Postgres verified | ⚠️ | CHƯA chạy alembic upgrade trên PG thật; chỉ test SQLite |
| Docker verified | ⚠️ | CHƯA start docker stack; máy local chưa cài Docker Desktop |
| CI verified | ⚠️ | CHƯA có postgres service trong api job; chỉ chạy pytest SQLite |

**Ghi chú**: Chỉ ghi ✅ cho verify type thực sự đã pass. Không ghi "VERIFIED" chung chung.

**Đã hỏi user và chốt**:
- Scope: Auth + DB migration (chưa `/documents` GET ở commit này).
- DB engine: Postgres 16 local.
- Docker compose: full stack (Postgres+Redis+MinIO+API).

**Risk + đã mitigate**:
- ⚠️ Python 3.12 (env hiện tại) chưa có `uuid.uuid7()` → dùng `uuid.uuid4()` (note trong middleware).
- ⚠️ Docker chưa có trên máy local → verify qua SQLite test (aiosqlite) + OpenAPI runtime schema.
- ⚠️ JWT secret dev length: đã bump lên ≥ 32 bytes (PyJWT warning).
- ⚠️ **Refresh rotation / logout / reuse detection CHƯA có** → Phase 1.1.
- ⚠️ **`config.py` chưa fail-closed ở production** → Phase 1.1.
- ⚠️ **`/health/ready` chưa check Postgres thật** → Phase 1.1.
- ⚠️ **Auth contract mới chỉ có `/auth/login` + `/auth/me`** → Phase 1.1 thêm `/auth/refresh` + `/auth/logout`.

**Commit kế tiếp** (đã chốt lại sau review 2026-08-09 22:00):
- ❌ ~~Phase 2 /documents~~ — dời.
- ✅ **Phase 1.1 — Auth Completion**: refresh sessions, rotation, logout, cookie tests, argon2id, fail-closed config, health/ready real check.
- ✅ **Phase 1.2 — Runtime Verification**: docker stack lên, alembic upgrade/downgrade/upgrade trên PG thật, oasdiff CI, coverage ≥ 80%.
- Sau đó mới sang Phase 2 (Documents GET + RBAC scope).

**Chi tiết**:
- Plan Phase 1.1: `docs/plans/2026-08-09-phase-1.1-auth-completion.md`.
- ADR-0003 (chốt stack + schema + contract): `docs/adr/0003-auth-hardening.md`.
- ADR-0002 (async SQLAlchemy): `docs/adr/0002-async-sqlalchemy-pattern.md`.

---

## 2026-08-09 — Phase 1.5: Dev Environment Setup

**Việc đã làm**:
- `docs/setup/dev-environment.md`: hướng dẫn cài WSL2 + Docker Desktop + oasdiff trên Windows 10 (9 section, kèm troubleshooting).
- `docs/plans/2026-08-09-phase-1.5-dev-env.md`: plan chi tiết 4 task (docs + scripts + Makefile + PROGRESS).
- KHÔNG sửa code, schema, CI, docker-compose, Makefile (chờ user confirm trước khi apply scripts và Makefile target).

**Trạng thái**:
- ✅ Docs setup + plan đã sẵn sàng.
- ⏸ Dev cần chạy `bash scripts/verify-env.sh` (sẽ tạo ở commit kế) sau khi cài Docker + oasdiff.
- ⏸ Khi verify pass → `make up` → `make seed` → `curl http://localhost:8000/health/live`.

**Commit kế tiếp**:
- `chore: thêm verify-env script (Bash + PowerShell)` — tạo `scripts/verify-env.sh` + `scripts/verify-env.ps1`.
- `chore: make env-check target` — thêm target `make env-check` wrapper.
- `docs: progress phase 1.5 dev env setup` — append entry này vào git history (hiện tại chưa commit).

**Risk + đã mitigate**:
- ⚠️ Docker Desktop chưa cài trên máy local → docs hướng dẫn từng bước, có verify ngay sau mỗi bước.
- ⚠️ PowerShell execution policy có thể block script → hướng dẫn dùng `-ExecutionPolicy Bypass -File`.
- ⛔ Agent KHÔNG tự `docker compose up` (rule 08 §1 — lệnh tạo container + pull image ~500MB, cần user confirm).

**Chi tiết**: `docs/plans/2026-08-09-phase-1.5-dev-env.md`.

---

## 2026-08-09 — Khởi tạo Workspace Rules & Skills

**Việc đã làm**:
- Cài đặt 27 Agent Skill vào `.skills/` từ skill `autoskill`.
- Tạo 8 project rule trong `.cursor/rules/`:
  - `00-communication.mdc` — giao tiếp, ngôn ngữ, commit, branch.
  - `01-design-principles.mdc` — SOLID, DRY, KISS, YAGNI, Clean Architecture, Design Pattern.
  - `02-frontend-nextjs.mdc` — quy tắc FE Next.js/React/TS (globs: `apps/web/**`).
  - `03-backend-api.mdc` — quy tắc BE (globs: `apps/api/**`, `packages/**`) — placeholder cho Phase BE.
  - `04-database-rag-ocr.mdc` — PostgreSQL schema, RAG pipeline, OCR pipeline.
  - `05-testing.mdc` — TDD, unit/integration/E2E, coverage target.
  - `06-security.mdc` — auth, RBAC, secrets, rate limit, audit log.
  - `07-skill-activation.mdc` — bảng map task ↔ skill tương ứng.
- Tạo `AGENTS.md` ở root làm entry point cho agent.

**Quyết định**:
- BE stack (chốt): **Python + FastAPI + pgvector** (xem `docs/adr/0001-backend-stack.md`).
- Tất cả rule `alwaysApply: true` trừ 02 (globs FE) và 03 (globs BE).

**Các commit theo review (đã merge)**:

| # | SHA | Commit | Nội dung chính |
|---|---|---|---|
| 1 | `45ab6d8` | `docs: chốt hợp đồng API & domain` | 6 file docs (OpenAPI, RBAC, lifecycle, citation, root README). |
| 2 | `5ed884c` | `chore: siết chặt governance & CI` | rule 08 mới, pgvector, .gitignore mở rộng, CI workflow, email domain, scripts. |
| 3 | `2888d86` | `chore: scaffold backend foundation` | folder skeleton rỗng + ADR-0001 + Makefile + MODEL_CARD template. |
| 4 | `a847ce4` | `chore: đồng bộ foundation theo review` | RFC 7807 trong rule 03, ADR rename, PROGRESS update, +23 tests (RBAC/apiClient/file). |
| 5 | `ea805f1` | `chore: siết foundation trước Phase 0 BE` | OpenAPI 3.1 + Reusable responses + IDEMPOTENCY_KEY_MISMATCH, refresh token cookie, Idempotency thu hẹp, skill activation lọc, .gitignore `.env*`, OCR review (`requires_review` + `review_status`). |

**Trạng thái Foundation (sau commit `ea805f1`)**:
- ✅ Stack Python + FastAPI + pgvector đã chốt (xem `docs/adr/0001-backend-stack.md`).
- ✅ API contract OpenAPI 3.1 + RFC 7807 đã viết và **ĐÃ VERIFY** bằng `redocly lint` (22 warnings cosmetic, không phải errors).
- ✅ Contract-first: rule 03 chốt `docs/api/openapi.yaml` làm source of truth, CI sẽ so sánh khi FastAPI sinh openapi.json.
- ✅ Auth pattern: refresh token ở HttpOnly cookie (spec tại `docs/api/auth-cookie.md`), đã sửa endpoint table trong rule 03.
- ✅ Folder skeleton `apps/api/`, `services/worker/`, `services/ocr-training/`, `packages/contracts/`, `infra/docker/` đã có (chỉ README + .gitkeep, chưa code).
- ✅ Quality gate FE: `pnpm check` (lint + typecheck + test 26/26 + openapi:lint + build) PASS.
- ⏸ BE code thật chưa viết — **chờ lệnh "Bắt đầu Phase 0 BE"** từ user.

---

## Phase Frontend F0–F6 — ✅ Walkthrough xong + ✅ Review fix xong

- **F0**: Khung dựng + Design System Rose Tint 2026 + 3-role Auth.
- **F1**: Danh sách + Upload (Dropzone, SHA-256, validate MIME + magic bytes `%PDF-`).
- **F2**: Chi tiết + Tabs phiên bản + Metadata Form + `notFound()` chuẩn Next.js.
- **F3**: OCR Review split-view (canvas + bbox + confidence).
- **F4**: Search RAG (snippet highlight, BGE-M3 score) — đã qua `useSearchRAG`.
- **F5**: Chatbot RAG LangChain (citation chip) — đã qua `useChatRAGMutation`.
- **F6**: Admin (Users + Models + Training Runs) — đã qua `useAdminUsers`, `useAdminModels`.

**Kiểm chứng sau khi sửa (2026-08-09)**:
- ✅ 11 route handler mock viết đầy đủ (auth/login, auth/me, documents, search, chat/query, admin/users, admin/models).
- ✅ `lib/api/queries/index.ts` có 5 hook: `useDocuments`, `useSearchRAG`, `useChatRAGMutation`, `useAdminUsers`, `useAdminModels`.
- ✅ `lib/auth/server-helper.ts` parse role từ Authorization header.
- ✅ RBAC check server-side: documents (filter scope), admin (403), upload (403 cho student).
- ✅ `notFound()` gọi đúng cách trong `[id]/page.tsx` & `[id]/review/page.tsx`.
- ✅ `validateFileMagicBytes` chặn file rename `.exe → .pdf`.
- ✅ Sidebar persist `localStorage` (`sidebar_collapsed`).
- ✅ Logout nút ở Topbar (`logout() + router.push("/login")`).
- ✅ `aria-label` đã thêm cho mọi icon-only button (verified ở Topbar, Sidebar, Search button).
- ✅ `error.tsx` có telemetry logging (message, stack, digest, timestamp).
- ✅ `tsc --noEmit`: 0 errors.
- ✅ Vitest: 3/3 passed (StatusBadge).
- ✅ `pnpm build`: PASS, 12/12 routes (đã approve build scripts trong `pnpm-workspace.yaml`).
- ✅ `pnpm exec next lint`: PASS, 0 errors, 2 warnings intentional (chat-thread, sidebar exhaustive-deps).
- ✅ `.eslintrc.json` đã có (extends `next/core-web-vitals`).

**Verdict (sau commit 2888d86)**: FE feature-complete với mock API. Đã pass `pnpm check` (lint + typecheck + test + build). Khi cắm BE thật, chỉ cần đổi env `NEXT_PUBLIC_API_MODE=live` và `NEXT_PUBLIC_API_BASE_URL=https://api.example.edu.vn/api/v1`, không cần refactor FE.

---

## QG1–QG4: Quality Gate Evidence

> **Lưu ý**: Bảng này dùng mã QG1–QG4 (Quality Gate), KHÔNG trùng với A1–A5 (giai đoạn triển khai).

| ID | Hạng mục | Status | Bằng chứng |
|----|---|---|---|
| QG1 | Auth Unit Tests | ✅ | `uv run pytest tests/test_auth_*.py` — **48 passed** (2026-08-10 09:18 UTC) |
| QG2 | Auth Coverage ≥ 75% | ✅ | `pytest --cov=app.modules.auth` — **75.38%** (CI gate: `--cov-fail-under=75`, global gate: `--cov-fail-under=80`) |
| QG3 | Full test suite (no PG) | ✅ | `uv run pytest -v` — **84 passed, 4 deselected** (4 test Postgres integration bị `deselect` do marker filter `-m "not integration"`, không phải `skip`) |
| QG4 | Docker Compose syntax | ⏸ Planned | Validate bằng `docker compose -f infra/docker/docker-compose.yml config` |

---

## Phase Backend — ⚠️ Phase 1.1 CHƯA ĐÓNG (thiếu bằng chứng Postgres)

**Đã code xong ở Phase 1.1** (2026-08-10):
- ✅ Auth: login, me, refresh (rotation), logout.
- ✅ Argon2id hashing, RefreshSession model, origin-CSRF.
- ✅ SQLite tests: 84 passed, 4 deselected (Postgres integration).
- ✅ ADR-0003: `docs/adr/0003-auth-hardening.md`.
- ⚠️ Postgres/Docker/CI: **CHƯA có bằng chứng** — chờ Docker Desktop.

> ⚠️ Phase 1.1 **CHƯA ĐÓNG** vì chưa chạy trên PostgreSQL thật. Chuyển sang Phase 2 chỉ khi A3 (Docker runtime) hoàn thành.

**Trạng thái FE–BE contract** (đã chốt ở commit `45ab6d8`, `5ed884c`, `2888d86`):

- ✅ OpenAPI 3.1 spec ở `docs/api/openapi.yaml` (machine-readable).
- ✅ Tổng quan contract ở `docs/api/README.md`.
- ✅ RBAC matrix ở `docs/domain/rbac-matrix.md`.
- ✅ State machine Document/Version/Job/Index ở `docs/domain/document-lifecycle.md`.
- ✅ Citation spec ở `docs/domain/citation-spec.md`.
- ✅ Error contract = **RFC 7807 Problem Details** (đã update `03-backend-api.mdc`).
- ✅ Upload pattern = **202 Accepted + job_id** (FE poll `/jobs/{id}`).
- ✅ Stack chốt ở `docs/adr/0001-backend-stack.md`.


---

## 2026-08-12 — B0–B4: Runtime baseline, Worker/MinIO, OCR và RAG guardrail

**B0 — CI/OpenAPI**:

- Đọc run CI thất bại mới nhất `31566347899`: lỗi chặn là hai `$ref` không phân giải tới `DocumentScopeCode` trong contract.
- Contract hiện tại dùng `DocumentScope` nhất quán; chạy `pnpm openapi:lint` đã **PASS** (`Woohoo! Your API description is valid.`).

**B1 — Docker/PostgreSQL baseline**:

- Đã khởi động Docker Desktop theo ủy quyền và chạy PostgreSQL, Redis, MinIO, API.
- Phát hiện/sửa hai lỗi runtime chặn baseline: Docker image thiếu `README.md` được khai báo bởi package metadata; image/Compose thiếu `alembic.ini` và migration assets. Compose cũng chuyển `APP_CORS_ORIGINS` sang JSON array đúng format Pydantic Settings.
- Đã chạy Alembic lên `head`, seed ba tài khoản demo và xác minh `/health/ready` trả PostgreSQL `ok`; login API thành công.

**B2 — Worker và MinIO**:

- `MinioStorageService` đã tự tạo bucket khi upload nên không thêm init trùng lặp.
- Bổ sung service `worker`, broker/result backend Redis và healthcheck Celery. Worker dùng `uv run celery` vì executable nằm trong virtual environment.
- Upload PDF synthetic đã đi qua API, MinIO, Redis và worker. Job kết thúc `FAILED` với thông báo `All OCR engines failed` khi chưa có engine OCR thật; điều này xác nhận không có mock OCR chạy âm thầm.

**B3 — OCR thật và đồng bộ 300 DPI**:

- Thêm `ocr_render_dpi=300` và `ocr_text_layer_min_characters=50` vào config để inference đồng bộ DPI với dataset fine-tune.
- Pipeline ưu tiên `page.get_text("text")`: trang có ít nhất 50 ký tự text layer được lưu trực tiếp; trang scan được render RGB qua PyMuPDF tại DPI cấu hình trước PaddleOCR/Tesseract.
- Bổ sung dependency runtime cho PyMuPDF, PaddlePaddle/PaddleOCR, Pillow, pytesseract và binary Tesseract có language pack tiếng Việt. Image API/worker đã rebuild và hai container đang healthy.
- Kiểm chứng runtime: PDF text layer bypass OCR; PDF scan trắng render kích thước `2480x3509` tại 300 DPI rồi đi qua Tesseract. Chưa thực hiện benchmark CER/WER hoặc kiểm thử chất lượng với PDF scan tiếng Việt thật.

**B4 — RAG grounding**:

- Thêm `rag_vector_score_threshold=0.6` vào config. Guardrail chỉ chấp nhận evidence nếu `vector_score` cosine đạt ngưỡng; RRF `score` chỉ giữ vai trò xếp hạng/citation.
- Test mới xác minh kết quả RRF cao nhưng cosine `0.59` vẫn bị từ chối, cosine `0.60` được chấp nhận và thiếu `vector_score` bị từ chối.

**Bằng chứng đã chạy**:

| Gate | Kết quả |
|---|---|
| OpenAPI lint | ✅ `pnpm openapi:lint` PASS |
| Targeted backend tests | ✅ `uv run pytest tests/test_chat_grounding.py tests/test_ocr.py -q --tb=short` — 11 passed |
| Docker runtime | ✅ PostgreSQL, Redis, MinIO, API, Worker đang healthy |
| OCR runtime smoke | ✅ text layer + render 300 DPI/Tesseract; ⚠️ chưa benchmark PDF scan tiếng Việt thật |

**Phần còn lại trước khi đóng hẳn**:

- Chạy full quality gate (Ruff, mypy, toàn bộ pytest, frontend và `pnpm check`).
- So sánh OpenAPI runtime với contract bằng `oasdiff` khi binary/toolchain sẵn sàng.
- Chạy E2E upload một PDF scan tiếng Việt đã được phê duyệt, đánh giá CER/WER và kiểm tra PaddleOCR thật.
- Không push/commit trong lần thực hiện này.


**B5 — Governance, contract diff và quality gate**:

- Quét `.agents/` trước khi thay đổi tracking: 239 tệp, 239 tệp đang được Git theo dõi. Không thấy pattern secret độ tin cậy cao (AWS/GitHub/GitLab/Slack/Stripe/private key hoặc assignment token mật độ cao). Sau đó thêm `.agents/` vào `.gitignore` và chạy `git rm -r --cached .agents`; toàn bộ 239 tệp vẫn còn trên đĩa, không bị xóa. `docs/ai-usage.md` mô tả quy trình AI và yêu cầu evidence có thể lặp lại.
- Chạy đúng lệnh `oasdiff` trong CI bằng image `tufin/oasdiff:latest`. Lệnh hoàn tất exit `0` và sinh diff thông tin (31,746 bytes), phù hợp với chú thích CI rằng runtime chưa bao phủ toàn bộ endpoint tương lai trong contract; không bật fail-on-diff.
- Backend static gate sau thay đổi: Ruff check PASS, Ruff format check PASS và mypy PASS (62 source files). `pnpm openapi:lint` PASS. Frontend type-check, lint (1 warning dependency có sẵn), 31 unit tests và build đã đi hết bước compile/generate 12 static pages; runner Windows không trả prompt sau khi artifact `.next/BUILD_ID` được tạo.
- Các test trực tiếp bị ảnh hưởng đều pass, gồm 11 test OCR/RAG targeted, 6 chat router tests, SSE citation event, RBAC citation scope, citation title và MinIO unavailable path. Full backend suite với Postgres Docker chạy qua 100% progress sau khi xử lý các failure nhưng runner không kết thúc ở teardown; không ghi nhận full-suite PASS cho tới khi hiện tượng connection teardown được xử lý.

> Lưu ý: full-suite runner có cảnh báo SQLAlchemy về connection chưa được trả về pool trong teardown. Đây là hạn chế kiểm chứng hiện tại, không được xem là bằng chứng full-suite clean.


---

## 2026-08-12 — Hoàn thiện OCR page preview và tính nhất quán indexing

**Việc đã làm**:

- Mỗi `OcrPageResult` mang bytes PNG render 300 DPI trong bộ nhớ đến worker; worker lưu object key `documents/pages/{version_id}/{page}.png` qua `StorageService`/MinIO rồi mới persist `OCRPage.image_key`. Key được lưu là object key nội bộ, không phải public URL, để review vẫn đi qua scope/RBAC backend.
- Cả trang có text layer và trang scan đều render 300 DPI trước khi tạo kết quả trang. Text layer tiếp tục bypass nhận dạng OCR khi đạt 50 ký tự, nhưng vẫn có preview PNG 300 DPI cho OCR review UI.
- Worker commit OCR pages/blocks trước indexing nhưng giữ `Job.status=PROCESSING`; chỉ sau `_async_index_document_chunks` trả `SUCCEEDED` mới đặt `Job.status=SUCCEEDED` và `progress=100`. Nếu indexing lỗi, outer handler vẫn đánh dấu job failed.
- Bổ sung test integration xác minh `image_key`, PNG bytes đã lưu, và job còn `PROCESSING` trong lúc indexing. Bổ sung test grounding: `vector_score=0.61` pass, `0.59` reject, ngưỡng vẫn là `0.6`.

**Bằng chứng đã chạy**:

| Gate | Kết quả |
|---|---|
| `uv lock --check` | ✅ Exit 0 |
| `uv run mypy app` | ✅ 62 source files, không có lỗi |
| Test OCR + grounding trực tiếp | ✅ 12 passed |
| Full coverage gate | ✅ 248 passed, 4 skipped, coverage **83.00%** (gate 80%) |
| `.agents` còn tracked | ✅ `git ls-files .agents` trả 0 |

> Full suite hoàn thành logic/coverage nhưng phát 8 `SAWarning` về connection cleanup ở teardown. Đây là warning cần theo dõi; coverage command vẫn kết thúc với kết quả pass được ghi trong output.


---

## 2026-08-12 — T01: Ollama nội bộ và BGE-M3 thật (đang triển khai)

**Đã thực hiện trong source/config**:

- Chốt Ollama chạy nội bộ trong Docker Compose. Compose thêm service `ctsv-ollama` dùng image ghim `ollama/ollama:0.32.9`, volume `ollama_data`, healthcheck server và không tự động pull model khi khởi động.
- API và worker phụ thuộc Ollama healthy, dùng DNS nội bộ `http://ollama:11434`; profile Compose đặt `EMBEDDING_PROVIDER=bge-m3`, `EMBEDDING_API_URL=http://ollama:11434/api/embed`, `LLM_PROVIDER=ollama`.
- Adapter BGE-M3 chuyển từ endpoint legacy từng prompt sang endpoint batch Ollama `/api/embed`, gửi một danh sách input và fail-closed nếu số vector hoặc dimension không đúng 1024.
- Cập nhật `.env.example` bằng các biến RAG/Ollama mẫu; không đọc hoặc sửa `.env` thật.

**Bằng chứng đã chạy**:

| Gate | Kết quả |
|---|---|
| Test adapter `/api/embed` (RED trước code) | ✅ Thất bại đúng như kỳ vọng do adapter cũ gửi endpoint/payload legacy |
| `uv run pytest tests/test_config.py tests/test_embedding.py -q` | ✅ 19 passed |

**Chưa xác minh**:

- Chưa chạy Docker Compose, chưa pull `bge-m3` hoặc `qwen2.5:8b`, chưa chạy migration và chưa index vector thật. Các bước này cần được thực hiện có chủ đích vì image/model tốn dung lượng và thời gian.


**Bằng chứng runtime bổ sung**:

- Docker Desktop được khởi động theo xác nhận của người dùng. Compose syntax pass khi vô hiệu hoá đọc `.env`; service `ctsv-ollama` healthy.
- Đã pull `bge-m3:latest` (1.2 GB) và `qwen2.5:7b` (4.7 GB) vào volume `ollama_data`. Tag cũ `qwen2.5:8b` không có manifest; dùng `qwen2.5:7b` vì là tag hợp lệ cùng họ, đa ngôn ngữ và để lại headroom tốt hơn cho máy 32 GB RAM/8 GB VRAM.
- API container gọi thật `BGEM3EmbeddingStrategy` qua `http://ollama:11434/api/embed` và nhận đúng một embedding 1024 chiều. Provider chat Ollama trả response không rỗng từ `qwen2.5:7b`.
- Không dùng PDF/OCR thật, không chạy migration và không lưu script kiểm chứng tạm trong repository.


---

## 2026-08-12 — T02/T03: OCR native và tiền xử lý ảnh có cấu hình

PaddleOCR primary đã được kiểm chứng trong `ctsv-worker` bằng PDF scan **tổng hợp** tiếng Việt, không dùng tài liệu thật. Worker trả một trang, ba block OCR và PNG render 300 DPI. Lỗi runtime ban đầu được truy vết chính xác: Paddle cần `setuptools`, OpenCV cần `libGL.so.1`; extra `ocr` nay khai báo trực tiếp `numpy` và `setuptools`, còn Docker image cài `libgl1` và `libglib2.0-0` cùng Tesseract tiếng Việt. Worker được rebuild riêng sau khi WSL đã giới hạn 6 GB, không rebuild đồng thời API.

Stage tiền xử lý opt-in đã thêm trước hai OCR engine: deskew theo foreground angle, median denoise và adaptive binarisation. Các tham số nằm trong nhóm `OCR_PREPROCESS_*`; mặc định `OCR_PREPROCESS_ENABLED=false` để giữ baseline render 300 DPI và output hiện hành. Nhánh được bật đã chạy qua PaddleOCR trên cùng PDF tổng hợp, trả một trang và ba block; unit/config tests đạt 23 passed, Ruff sạch và mypy sạch trên 63 source files.

> Chưa có corpus được phép, vì vậy chưa đo CER/WER hoặc latency trước/sau. Bật preprocessing cho benchmark chỉ được thực hiện sau khi nhận corpus, chia test set và đóng baseline theo T15–T17.

---

## 2026-08-12 — T04: Ảnh thật có RBAC cho màn duyệt OCR

- Contract bổ sung endpoint `GET /documents/{id}/versions/{vid}/ocr/pages/{page}/image`. Router kiểm tra document scope **trước** khi truy vấn `OCRPage` và storage; chỉ sau đó trả bytes `image/png` với `Cache-Control: private, no-store`. Không tạo public URL MinIO.
- Frontend live mode dùng binary API client với bearer token, lấy PNG qua endpoint có RBAC; bbox pixel backend được chuẩn hoá theo `OCRPage.width`/`height` trước overlay. Mock mode vẫn giữ fixture riêng.
- Kiểm chứng đã có: test API staff đọc ảnh trang trả 200 PNG; student không có scope `INTERNAL` bị 403. `pnpm openapi:lint`, frontend typecheck và 31 frontend test đã pass trong phiên trước.

---

## 2026-08-12 — T05: Upload JPG/PNG an toàn và OCR ảnh một trang

**Đã thực hiện**:

- Cập nhật `docs/api/openapi.yaml` trước; `POST /documents` chấp nhận PDF tối đa 50MB, JPEG/PNG tối đa 10MB và yêu cầu MIME khớp magic bytes. Contract TypeScript được tái sinh từ nguồn chuẩn.
- Validator tại backend chỉ nhận `%PDF-`, `FF D8 FF` (JPEG) hoặc `89 50 4E 47 0D 0A 1A 0A` (PNG); MIME không khớp, bytes giả đổi đuôi và vượt giới hạn bị trả RFC 7807 `415`/`413`. Filename không được dùng làm storage key nên không tạo đường path traversal.
- Raw upload lưu extension và content type do validator phát hiện. Worker suy ra format từ object key do service kiểm soát; PDF tiếp tục render PyMuPDF 300 DPI, còn JPEG/PNG đi qua `process_image()` trực tiếp một trang, được chuẩn hoá thành PNG review tại `documents/pages/{version_id}/1.png`. Job vẫn chỉ `SUCCEEDED` sau indexing.
- Thêm test cho JPEG/PNG hợp lệ, JPEG giả đổi đuôi, giới hạn ảnh 10MB, regression PDF, dispatch OCR ảnh và luồng API test: upload PNG → version → OCR block → `image_key` → endpoint PNG private.

**Bằng chứng đã chạy**:

| Gate | Kết quả |
|---|---|
| OpenAPI | ✅ `pnpm openapi:lint` PASS; `pnpm openapi:generate` hoàn tất |
| T05 targeted tests | ✅ `uv run pytest tests/test_documents_upload.py tests/test_pdf_validator.py tests/test_ocr_image.py -q` — **15 passed, 1 skipped** |
| JPEG/PNG lifecycle API test | ✅ cả JPEG và PNG tạo OCR block và page key chuẩn; PNG được đọc lại qua API private trong test harness |
| Static backend | ✅ Ruff PASS; mypy PASS (**64 source files**) |
| Regression không phụ thuộc PG/Alembic/BGE live | ✅ **234 passed, 1 skipped, 27 deselected** |

**Bằng chứng native bổ sung**:

- Sau khi được xác nhận, đã rebuild và recreate **riêng** `ctsv-worker`; service trở lại `healthy`. Smoke test bằng ảnh JPEG **và PNG** tổng hợp không nhạy cảm, chạy qua đúng virtual environment worker, mỗi định dạng trả **1 page, 2 blocks, kích thước 1600×900 và PNG review hợp lệ**. Không in nội dung OCR, không upload hay đọc tài liệu thật.
- Lần thử đầu gọi Python hệ thống nên không thấy Pillow; đó không phải runtime worker. `uv run python` trong `/app/.venv` xác nhận extra OCR đã có và PaddleOCR primary xử lý ảnh trực tiếp thành công.
- Full coverage gate hiện kết thúc fail vì lỗi xác thực PostgreSQL của môi trường test và payload embedding BGE-M3 live không hợp lệ; coverage vẫn đạt **80.09%**. Đây không được ghi là full-suite clean.

---

## 2026-08-12 — T06: LangChain chain grounded thật cho chat

**Đã thực hiện**:

- Khai báo `langchain`, `langchain-community` và `langchain-ollama`; `uv.lock` khoá 153 package và `uv lock --check` đạt.
- Thêm `SearchDocumentsRetriever`: lấy scope được phép của user, chặn requested scope ngoài quyền **trước** `search_documents()`, sau đó dùng nguyên retrieval hybrid/RRF hiện có. Không thay vector store hoặc topology pgvector.
- Thêm `LangChainRagChain`: retriever → guardrail cosine `rag_vector_score_threshold=0.6` → `ChatPromptTemplate` → Ollama `ChatOllama` nội bộ ở live mode → `StrOutputParser`. Citation được tạo duy nhất từ evidence đã qua guardrail; score 0.59/no-result trả no-answer và không gọi LLM.
- Luồng chat sync và stateless gọi full chain. SSE dùng cùng retriever, guardrail và prompt template LangChain, sau đó giữ `AbstractLLMProvider.stream_generate()` để bảo toàn event token/citation/done và test client hiện hữu.
- Thêm `SafeRagTraceCallback` trong memory: trace chỉ có stage, số evidence và cờ grounding; không lưu question, quote, answer, nội dung tài liệu hoặc PII. Test ghim các invariant đó.

**Bằng chứng đã chạy**:

| Gate | Kết quả |
|---|---|
| Lock/source | ✅ `uv lock --check`; Ruff PASS; mypy PASS (**65 source files**) |
| LangChain unit + chat/SSE regression | ✅ **22 passed**: chain, citation, no-answer, 0.61/0.59, RBAC scope, SSE event/persistence |
| Live internal chain | ✅ rebuild/recreate **riêng `ctsv-api`**, healthcheck healthy; smoke synthetic qua `http://ollama:11434` trả `has_sufficient_evidence=true`, 1 citation và answer không rỗng |
| Trace privacy | ✅ test xác nhận trace không chứa question, quote hoặc answer |

**Lưu ý kiểm chứng**: Regression chat phát ra 6 `SAWarning` về cleanup connection SQLite test harness; test vẫn pass và đây không phải lỗi chain. Full pytest/coverage mới nhất đạt **80.86%** nhưng kết thúc `3 failed, 258 passed, 1 skipped, 3 errors`: các test PostgreSQL/Alembic bị chặn bởi xác thực PostgreSQL test và các test BGE-M3 live bị chặn bởi payload embedding không hợp lệ. Hai nhóm này có trước T06, không được ghi là full-suite clean. Docker runtime sau rebuild riêng có `ctsv-api`, `ctsv-worker`, `ctsv-ollama`, Redis, PostgreSQL và MinIO đều `healthy`.


---

## 2026-08-12 — B5: Ổn định, kiểm kê và evidence sau T01–T06

**Kiểm kê implementation thực tế**:

- `apps/api` không còn là scaffold: hiện có FastAPI, models, migrations, document/auth/search/chat modules, `app/worker/`, OCR native, storage, embedding và LangChain chain.
- Compose chuẩn là `infra/docker/docker-compose.yml`, gồm PostgreSQL+pgvector, Redis, MinIO, Ollama, API và worker. Worker implementation thật ở `apps/api/app/worker/`; `services/worker/` chỉ còn tài liệu scaffold cũ.
- Frontend hỗ trợ live mode và mock mode. Các Next.js route như `/api/chat/query` vẫn ghi rõ `DEMO ONLY`; chúng phục vụ UI/demo, không phải bằng chứng FastAPI/RAG runtime.
- `services/ocr-training/` vẫn là scaffold offline. Chưa có corpus được phê duyệt hay benchmark CER/WER; không khẳng định fine-tune OCR đã hoàn tất.

**Sửa trực tiếp trong phạm vi B5**:

- Áp dụng Ruff format cho `security.py`, `embedding.py`, `ocr_engine.py` và `rag_chain.py`; không đổi hành vi contract/OCR/RAG.
- Sửa fixture PostgreSQL integration để lỗi credential local được skip ngoài CI nhưng fail-closed trong CI. Test round-trip Alembic nay probe xác thực trước migration, tránh báo lỗi migration giả do database test local chưa được cấu hình.
- Đồng bộ `README.md` và `AGENTS.md` với source/runtime thật, chỉ ra đường dẫn Compose chuẩn, mock/live boundary, training scaffold và lệnh quality gate. Không đưa password, `.env`, tài liệu/OCR thật hay model artifact vào tài liệu.

**Evidence đã chạy**:

| Gate | Kết quả |
|---|---|
| OpenAPI/frontend/workspace | ✅ `pnpm check` PASS; frontend có 32 unit tests pass, build hoàn tất 12 route. |
| Backend static | ✅ Ruff check + Ruff format check PASS; mypy PASS trên 65 source files. |
| Backend tests local | ✅ 260 passed, 5 skipped, 8 warnings. Năm skip là integration PostgreSQL khi test database local không xác thực được; CI vẫn fail-closed. |
| Targeted OCR/RAG | ✅ 23 passed, 1 skipped, 1 warning: OCR 300 DPI/preprocessing/image, guardrail 0.6, citation, LangChain chain và chat router. |
| Compose config | ✅ `docker-compose --env-file .env.example -f infra/docker/docker-compose.yml config` PASS; không đọc `.env` thật và không khởi động service. |
| Runtime health | ✅ API, worker, Ollama, Redis, PostgreSQL và MinIO đều healthy. |
| OCR native | ✅ worker xử lý ảnh PNG synthetic: 1 page, 2 blocks, 1600×900; chỉ ghi metadata. |
| LangChain/Ollama | ✅ API gọi chain nội bộ với evidence synthetic: evidence đủ, 1 citation, answer không rỗng; chỉ ghi metadata. |

**Giới hạn và việc còn mở**:

- PostgreSQL/Alembic integration chưa có evidence pass trên database test được cấu hình đúng; local hiện skip do credential test không sẵn sàng, không được coi là PostgreSQL integration clean.
- Suite backend còn 8 warning, gồm cảnh báo cleanup connection SQLAlchemy trong test harness; test logic vẫn pass nhưng warning cần theo dõi riêng.
- Smoke OCR/RAG dùng dữ liệu synthetic. Không chạy upload PDF/ảnh thật, không benchmark CER/WER, không truy cập hoặc log nội dung tài liệu người dùng.
- Không có commit, push, migration, seed, Docker Compose up/down hay rebuild trong đợt B5.


---

## 2026-08-12 — B6: PostgreSQL integration và full HTTP E2E synthetic

**Thiết lập cô lập và fail-closed**:

- Dùng database PostgreSQL riêng `ctsv_b6_test`, role runner giới hạn và file biến môi trường tạm ngoài repository. Credential không được ghi vào source, log hoặc tài liệu.
- `tests/conftest.py` và `tests/test_alembic.py` yêu cầu database integration hợp lệ khi chạy marker `integration` hoặc trong CI. Credential/database lỗi phải làm test fail, không được đổi thành skip âm thầm.
- Cấu hình `CELERY_DOCUMENTS_QUEUE` được đưa vào `Settings`; runner B6 dùng queue `b6-documents`, Redis DB broker/backend riêng và bucket `ctsv-b6-synthetic` để không đụng job hay object runtime chính.

**PostgreSQL/Alembic và regression**:

| Gate | Kết quả đã có evidence |
|---|---|
| Alembic round-trip trên PostgreSQL cô lập | ✅ Test migration upgrade/downgrade/upgrade nằm trong 5 integration tests pass |
| ORM PostgreSQL | ✅ 5 passed với `pytest -m integration` |
| Static backend | ✅ Ruff check, Ruff format check và mypy pass trên 65 source files |
| Adapter/config Ollama | ✅ 28 targeted tests pass; payload BGE-M3 và provider Ollama được ghim `keep_alive` |
| Full backend suite | ✅ `266 passed, 1 skipped, 8 warnings` trong 59.27s |
| Workspace | ✅ `pnpm check` pass; 32 frontend tests pass và build 12 route hoàn tất |
| Whitespace diff | ✅ `git diff --check` exit 0; chỉ còn cảnh báo chuyển CRLF/LF của Git, không có whitespace error |

**Full HTTP E2E synthetic thực tế**:

- Runner tạm khởi tạo cặp API/worker riêng trên port `18000`, chạy Alembic, seed demo user trong namespace B6 và dọn hai container ở `finally`. Không chạy Docker Compose hay Docker build.
- E2E gọi HTTP thật theo luồng login staff/student → upload PDF synthetic → poll worker → OCR → lưu raw/preview PNG trong MinIO → kiểm tra metadata PostgreSQL → search → LangChain/Ollama chat → assertion RBAC và insufficient-evidence.
- Lần evidence cuối trả: `B6 E2E passed: pages=1 blocks=1 chunks=1 embedding_dimension=1024 citations=1` và `content_log_check=clean`.
- Staff nhận được evidence/citation thật. Student bị từ chối ở ba đường INTERNAL: document detail, search và chat (HTTP 403). Câu hỏi không liên quan trả `has_sufficient_evidence=false` và không có citation.
- RAG guardrail vẫn giữ cosine `rag_vector_score_threshold=0.6`; test ghim `0.61` được nhận và `0.59` bị loại.

**Kiểm soát bộ nhớ runtime B6**:

- Lỗi E2E ban đầu là Ollama chấm dứt `qwen2.5:7b` vì áp lực RAM khi BGE-M3 còn resident. Không đổi model, không dùng mock và không hạ guardrail.
- Bổ sung hai setting explicit `embedding_ollama_keep_alive` và `llm_ollama_keep_alive`, mặc định `5m` để giữ hành vi runtime thông thường. Chỉ runner B6 đặt `0`, khiến BGE-M3/Qwen được unload sau request; worker B6 chạy một process và `max-tasks-per-child=1` để tránh OCR/PaddleOCR giữ RAM không cần thiết. Lần chạy cuối E2E pass với Ollama và OCR thật.
- E2E không gửi marker nội dung synthetic trong query-string nữa vì access log URL đã tạo false positive. Log API/worker được kiểm marker sau chạy và kết quả clean.

**Warnings và giới hạn còn lại**:

- Tám `SAWarning` SQLAlchemy đã điều tra là garbage-collector cleanup connection SQLite trong `test_stateless_chat_query`; không phải `ResourceWarning` hay leak đã tái hiện từ code runtime. Trước đó suite với `-W error::ResourceWarning` vẫn pass.
- Không có corpus OCR được phê duyệt: chưa benchmark CER/WER, chưa tuyên bố OCR fine-tune/training hoàn tất và không đọc PDF/OCR thật.
- E2E dùng PDF synthetic một trang; chưa thay thế bằng benchmark tải lớn, nhiều trang hoặc PDF scan tiếng Việt được phê duyệt.
- Không commit, push, thay đổi OpenAPI, migration schema, Docker Compose hay dữ liệu/model artifact trong B6.
