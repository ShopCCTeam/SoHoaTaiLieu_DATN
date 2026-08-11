# Project Plan: SoHoaTaiLieu_DATN

## Architecture
- **Monorepo**: Next.js 14 (`apps/web`) + FastAPI (`apps/api`) + Contracts (`packages/contracts`)
- **Backend Stack**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic, PostgreSQL 16 + pgvector, Celery + Redis, MinIO (S3)
- **AI Stack**: PaddleOCR / Tesseract, BGE-M3 (1024 dim), Ollama (Qwen2.5/Llama-3.1 8B), LangChain
- **Frontend Stack**: Next.js 14 App Router, TypeScript Strict, Zustand v5, TanStack Query v5, Lucide React (SVG icons)

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| B | Document Management & Storage | MinIO S3 integration, REST APIs matching `openapi.yaml`, RBAC scope filtering (PUBLIC/STUDENT_AFFAIRS/INTERNAL), versioning, Celery async pipeline, PDF magic bytes validation, max 50MB limit | Phase 1 (Auth DONE) | DONE |
| C | OCR Pipeline | PaddleOCR primary + Tesseract fallback, text block extraction with page numbers, bounding box coordinates, confidence scores, OCR storage linked to document versions, OCR review API (approve/reject/edit) | Phase B | DONE |
| D | RAG Vector Search Engine | BGE-M3 multilingual embeddings (1024 dim), document chunking, pgvector storage, hybrid search (full-text + vector similarity + reranking), Search API with relevance scores & citations | Phase C | DONE |
| E | RAG Chatbot with Citations | Ollama LLM provider adapter, LangChain pipeline (query -> retrieve -> generate), SSE streaming endpoint with citations (document name, page, bbox), conversation history | Phase D | DONE |
| F | Frontend Integration | Switch Next.js from mock API (`NEXT_PUBLIC_API_MODE=mock`) to live backend (`live`), route verification across all 12 routes, Playwright E2E verification | Phase E | DONE |

## Quality Gates
- **Backend**:
  - `uv run pytest` >= 80% coverage
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy app`
- **Frontend**:
  - `pnpm test`
  - `pnpm build`
- **Integrity**:
  - Forensic Auditor verdict must be CLEAN (no hardcoded outputs, facade logic, or test bypasses).

## Code Layout
- Frontend: `apps/web/src/` (app/, components/, lib/api/, store/, hooks/)
- Backend: `apps/api/app/` (api/v1/, core/, db/, models/, schemas/, services/, worker/)
- Contracts: `packages/contracts/`
