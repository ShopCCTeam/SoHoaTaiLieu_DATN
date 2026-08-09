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
- BE stack: **chưa chốt** (Node.js hay Python) — đề xuất Node + Fastify hoặc Python + FastAPI, sẽ quyết ở Phase 0 BE.
- Tất cả rule `alwaysApply: true` trừ 02 (globs FE) và 03 (globs BE).

---

## Phase Frontend F0–F6 — ✅ Walkthrough xong (đang chờ review)

- **F0**: Khung dựng + Design System Rose Tint 2026 + 3-role Auth.
- **F1**: Danh sách + Upload (Dropzone, SHA-256, validate MIME).
- **F2**: Chi tiết + Tabs phiên bản + Metadata Form.
- **F3**: OCR Review split-view (canvas + bbox + confidence).
- **F4**: Search RAG (snippet highlight, BGE-M3 score).
- **F5**: Chatbot RAG LangChain (citation chip → `/documents/[id]?page=N`).
- **F6**: Admin (Users + Models + Training Runs).
- Build PASS, Unit Test StatusBadge PASS (3/3).

**Còn lại (FE MUST-FIX, do người khác xử)**:
1. `lib/api/client.ts` — page F4–F6 chưa qua `apiClient`, đang dùng fixture.
2. `app/api/documents/route.ts` — không check role.
3. `app/(app)/documents/[id]/page.tsx` — fallback `MOCK_DOCUMENTS[0]` khi id sai.
4. `app/api/documents/route.ts` — `MOCK_DOCUMENTS.unshift()` mutate global state.

---

## Phase Backend — ⏸ Chưa bắt đầu

- Chờ lệnh "bắt đầu Phase 0 BE" sau khi FE ổn.
- Sẽ dùng skill: `writing-plans` (viết plan) → `using-git-worktrees` (mở worktree) → chọn stack theo decision tree `nodejs-best-practices`.
- API contract đã chốt trong rule `03-backend-api.mdc`.
