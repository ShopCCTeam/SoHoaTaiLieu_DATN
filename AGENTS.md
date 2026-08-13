# AGENTS.md — Workspace Context cho AI Agent

> File này là **entry point** cho mọi agent làm việc trong workspace này.
> Cursor tự động load file này đầu mỗi session.

## Dự án

**Tên**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên
**Stack**: Next.js 14 (Frontend) + FastAPI / Python 3.11 (Backend) — đã chốt ở ADR-0001.
**Tính năng cốt lõi**: OCR (PaddleOCR/Tesseract) + RAG (LangChain + BGE-M3 + Ollama) + RBAC 3 roles.
**Repo**: `E:\SoHoaTaiLieu_DATN` (monorepo pnpm workspaces + uv cho apps/api).

## Cấu trúc repo

```
SoHoaTaiLieu_DATN/
├── apps/
│   ├── web/                    ← Next.js 14 Frontend (F0-F6 + contract sync xong)
│   └── api/                    ← FastAPI runtime (auth, documents, OCR, RAG, worker)
├── packages/
│   └── contracts/              ← OpenAPI → TypeScript types (auto-generated)
├── docs/                       ← tài liệu (PROGRESS.md, walkthrough, ADRs)
├── .skills/                    ← 27 Agent Skill đã cài (xem rule 07-skill-activation.mdc)
├── .cursor/rules/              ← 9 rule file (xem bên dưới)
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

- ✅ Frontend F0–F6: có live mode qua API client và mock mode riêng cho UI/demo. Mock route không phải evidence backend runtime.
- ✅ Backend: Auth refresh rotation, document upload/version, RBAC scope, OCR review, search hybrid và chat grounded đã có implementation trong `apps/api`.
- ✅ Runtime Compose: PostgreSQL+pgvector, Redis, MinIO, Ollama, API và Celery worker; worker thật nằm tại `apps/api/app/worker/`.
- ✅ B6 synthetic runtime: PostgreSQL test database, queue, Redis namespace và MinIO bucket cô lập; integration fail-closed, Alembic round-trip và HTTP E2E synthetic đã có evidence tái lập qua `scripts/e2e-synthetic-document.py`.
- ✅ OCR synthetic: PDF render 300 DPI, PaddleOCR primary, Tesseract fallback, preprocessing opt-in và ảnh review private qua API RBAC. Đây không phải benchmark hoặc chứng cứ OCR trên tài liệu thật.
- ✅ RAG synthetic: BGE-M3 1024 chiều qua Ollama, guardrail cosine 0.6, LangChain chain, citation và no-answer. Đây không thay thế benchmark Recall@K/MRR hoặc citation accuracy.
- ⚠️ OCR training offline trong `services/ocr-training/` vẫn là scaffold; chưa có corpus 200 PDF được phê duyệt, baseline/fine-tune hoặc benchmark CER/WER.
- ⚠️ E2E frontend live bằng Playwright chưa có evidence; mock Next.js chỉ phục vụ UI/demo, không là bằng chứng backend runtime.
- 📖 Đọc trạng thái/evidence chi tiết ở `docs/PROGRESS.md`; đọc `MANUS.md` trước mọi thay đổi.

## Tech stack cố định (KHÔNG thay đổi khi chưa có ADR mới)

**Frontend**:
- Next.js 14+ (App Router), TypeScript Strict, Tailwind CSS.
- Zustand v5 + TanStack Query v5.
- Framer Motion, Lucide React (100% SVG icon).
- Zod + React Hook Form.
- Vitest + Testing Library, Playwright (E2E).

**Backend** (đã chốt trong `docs/adr/0001-backend-stack.md`):
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
pnpm typecheck        # tsc --noEmit

# BE (uv-managed)
cd apps/api
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
uv run ruff check app tests
uv run mypy app

# Contracts (FE–BE shared types)
pnpm --filter @ctsv/contracts generate

# Workspace
pnpm install
pnpm check            # FE lint + typecheck + test + build + OpenAPI lint + BE test/ruff/mypy

# Docker Compose (Postgres + Redis + MinIO + Ollama + API + worker)
# Chỉ chạy/rebuild khi đã được người dùng phê duyệt.
docker-compose --env-file .env.example -f infra/docker/docker-compose.yml config
make up               # khởi động stack khi đã được phê duyệt
make seed             # seed môi trường development khi đã được phê duyệt
make logs             # tail logs
make down             # dừng stack khi đã được phê duyệt
```

## Ghi chú quan trọng

- **Ngôn ngữ giao tiếp**: 100% tiếng Việt với user. Code identifier tiếng Anh.
- **Không commit** file `.env*`, `node_modules/`, `.next/`, `data/**`, `models/**`, file PDF mẫu, model checkpoint.
- **Mỗi commit = 1 concern**. Frontend/Backend tách commit khi không coupling.
- **Trước khi merge**: chạy `pnpm check`, backend Ruff/format/mypy/pytest và đọc `docs/PROGRESS.md`. Không tự commit hoặc merge khi chưa có yêu cầu rõ ràng.
- **Backend không có Docker trên Windows?**: dùng environment Python 3.11+ phù hợp để chạy test unit SQLite; các test mang marker PostgreSQL chỉ là evidence khi có PostgreSQL test được cấu hình và xác thực thành công.
