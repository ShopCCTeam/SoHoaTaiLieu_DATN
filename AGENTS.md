# AGENTS.md — Workspace Context cho AI Agent

> File này là **entry point** cho mọi agent làm việc trong workspace này.
> Cursor tự động load file này đầu mỗi session.

## Dự án

**Tên**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên
**Stack**: Next.js 14 (App Router) + TypeScript + Tailwind + Zustand + TanStack Query (FE) — sẽ bổ sung Backend (chưa chốt Node.js hay Python).
**Tính năng cốt lõi**: OCR (PaddleOCR/Tesseract) + RAG (LangChain + BGE-M3 + Qdrant + Ollama) + RBAC 3 roles.
**Repo**: `E:\SoHoaTaiLieu_DATN` (monorepo pnpm workspaces).

## Cấu trúc repo

```
SoHoaTaiLieu_DATN/
├── apps/
│   └── web/                    ← Next.js 14 Frontend (F0-F6 đã xong, đang chờ review)
├── docs/                       ← tài liệu (PROGRESS.md, walkthrough, ADRs)
├── .skills/                    ← 27 Agent Skill đã cài (xem rule 07-skill-activation.mdc)
├── .cursor/rules/              ← 8 rule file (xem bên dưới)
└── AGENTS.md                   ← file này
```

## Quy tắc bắt buộc (đọc các file này theo thứ tự)

| # | File | Khi nào đọc |
|---|---|---|
| 00 | `.cursor/rules/00-communication.mdc` | Mọi session — giao tiếp, ngôn ngữ, commit |
| 01 | `.cursor/rules/01-design-principles.mdc` | Mọi session — SOLID, Clean Architecture, Design Pattern |
| 02 | `.cursor/rules/02-frontend-nextjs.mdc` | Khi sửa FE (apps/web/**) |
| 03 | `.cursor/rules/03-backend-api.mdc` | Khi sửa BE (sẽ áp dụng khi Phase BE bắt đầu) |
| 04 | `.cursor/rules/04-database-rag-ocr.mdc` | Khi sửa DB schema, RAG pipeline, OCR pipeline |
| 05 | `.cursor/rules/05-testing.mdc` | Khi viết/sửa test |
| 06 | `.cursor/rules/06-security.mdc` | Khi sửa auth, permission, secrets, log |
| 07 | `.cursor/rules/07-skill-activation.mdc` | Trước khi bắt đầu task — chọn skill phù hợp |
| 08 | `.cursor/rules/08-governance.mdc` | Mọi session — giới hạn quyền agent, idempotency, RAG safety |

## Trạng thái hiện tại

- ✅ Frontend Phase F0–F6 đã walkthrough, đang chờ người khác review & fix 4 MUST-FIX.
- ⏸ Phase 0 Backend chưa bắt đầu (chờ lệnh).
- ✅ 27 Agent Skill đã cài.
- ✅ 8 Project Rule đã thiết lập (rule 00–07).
- ✅ Rule 08 (governance) bổ sung sau review P0.
- 📖 Đọc tiến độ chi tiết ở `docs/PROGRESS.md`.

## Tech stack cố định (KHÔNG thay đổi khi chưa có ADR mới)

**Frontend**:
- Next.js 14+ (App Router), TypeScript Strict, Tailwind CSS.
- Zustand v5 + TanStack Query v5.
- Framer Motion, Lucide React (100% SVG icon).
- Zod + React Hook Form.
- Vitest + Testing Library, Playwright (E2E).

**Backend** (đã chốt trong `docs/adr/0001-stack.md`):
- Python 3.11 + FastAPI + Pydantic v2.
- SQLAlchemy 2.x + Alembic.
- PostgreSQL 16 + pgvector (vector + full-text + metadata).
- Celery + Redis (broker).
- MinIO (S3-compatible file storage).
- Uvicorn (dev) / Gunicorn + Uvicorn workers (prod).

**AI/ML**:
- OCR: PaddleOCR (primary, fine-tuned bằng dữ liệu riêng) + Tesseract (fallback runtime only).
- Embedding: BGE-M3 multilingual (1024 dim).
- LLM: Ollama local (Qwen2.5 hoặc Llama-3.1 8B) — provider adapter để swap.
- Vector DB: **pgvector** (chung PostgreSQL, không tách Qdrant trong MVP).

## Lệnh nhanh

```bash
# FE
cd apps/web
pnpm install
pnpm dev              # http://localhost:3000
pnpm test             # Vitest unit
pnpm build            # Production build
pnpm lint             # ESLint

# Workspace
pnpm -r build         # build tất cả apps
pnpm -r test          # test tất cả apps
```

## Ghi chú quan trọng

- **Ngôn ngữ giao tiếp**: 100% tiếng Việt với user. Code identifier tiếng Anh.
- **Không commit** file `.env`, `node_modules/`, `.next/`, file PDF mẫu lớn.
- **Mỗi Phase**: mở 1 git worktree riêng (skill `using-git-worktrees`).
- **Trước khi merge**: chạy `pnpm test` + `pnpm build` + đọc `docs/PROGRESS.md`.
