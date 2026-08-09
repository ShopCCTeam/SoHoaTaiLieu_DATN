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

## Phase Backend — ⏸ Chưa bắt đầu (chờ lệnh)

**Trạng thái FE–BE contract** (đã chốt ở commit `45ab6d8`, `5ed884c`, `2888d86`):

- ✅ OpenAPI 3.1 spec ở `docs/api/openapi.yaml` (machine-readable).
- ✅ Tổng quan contract ở `docs/api/README.md`.
- ✅ RBAC matrix ở `docs/domain/rbac-matrix.md`.
- ✅ State machine Document/Version/Job/Index ở `docs/domain/document-lifecycle.md`.
- ✅ Citation spec ở `docs/domain/citation-spec.md`.
- ✅ Error contract = **RFC 7807 Problem Details** (đã update `03-backend-api.mdc`).
- ✅ Upload pattern = **202 Accepted + job_id** (FE poll `/jobs/{id}`).
- ✅ Stack chốt ở `docs/adr/0001-backend-stack.md`.

**Khi nào bắt đầu code BE**: Chờ lệnh "Bắt đầu Phase 0 BE".

**Sẽ dùng**:
- Skill `writing-plans` (viết plan ở đây).
- Mở worktree `phase-0-be`.
- Code theo `03-backend-api.mdc` + `04-database-rag-ocr.mdc` + `.cursor/rules/08-governance.mdc`.
