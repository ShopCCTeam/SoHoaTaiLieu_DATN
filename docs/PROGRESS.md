# Nhật ký Tiến độ Dự án

> File log tiến độ từng Phase. Cập nhật theo format dưới. Mỗi Phase có mục riêng.

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
- BE stack (chốt sau): **Python + FastAPI + pgvector** (xem `docs/adr/0001-stack.md`).
- Tất cả rule `alwaysApply: true` trừ 02 (globs FE) và 03 (globs BE).

**Sau review P0/P1 (commit `45ab6d8`, `5ed884c`, scaffold đang chuẩn bị)**:

- ✅ Commit 1 — `docs: chốt hợp đồng API & domain`: 6 file docs (OpenAPI, RBAC, lifecycle, citation, root README).
- ✅ Commit 2 — `chore: siết chặt governance & CI`: rule 08 mới, pgvector, .gitignore mở rộng, CI workflow, email domain, scripts.
- ⏳ Commit 3 — `chore: scaffold backend foundation`: folder skeleton rỗng + ADR-0001 + Makefile + MODEL_CARD template.

Kết quả: foundation hoàn tất, sẵn sàng cho Phase 0 BE code thật khi user ra lệnh.

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
- ⚠️ `pnpm build` cần `pnpm approve-builds esbuild unrs-resolver` (1 lần, do pnpm 10+ chặn build script mặc định).
- ⚠️ Chưa có `.eslintrc.json` — chạy `pnpm exec next lint` lần đầu sẽ hỏi. Tạo file `.eslintrc.json` với `extends: ["next/core-web-vitals"]` để skip prompt.

**Verdict**: FE sẵn sàng tích hợp BE. Khi cắm BE thật, chỉ cần đổi env `NEXT_PUBLIC_API_MODE=live` và `NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api/v1`, không cần refactor FE.

---

## Phase Backend — ⏸ Chưa bắt đầu

- Chờ lệnh "bắt đầu Phase 0 BE" sau khi FE ổn.
- Sẽ dùng skill: `writing-plans` (viết plan) → `using-git-worktrees` (mở worktree) → chọn stack theo decision tree `nodejs-best-practices`.
- API contract đã chốt trong rule `03-backend-api.mdc`.
