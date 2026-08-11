# Original User Request

## 2026-08-11T05:59:03Z

Build and integrate the complete backend, AI services, and frontend for "Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên" (SoHoaTaiLieu_DATN). The system uses FastAPI + PostgreSQL/pgvector + Celery + MinIO for the backend, PaddleOCR for document digitization, BGE-M3 + pgvector for RAG search, and Ollama for AI chatbot. Frontend is Next.js 14 (already built with mock API, needs switching to live backend).

Working directory: E:\SoHoaTaiLieu_DATN
Integrity mode: development

## Current State (already done — DO NOT modify)

- Frontend (apps/web): 12 routes, 26 tests, all with mock API (`NEXT_PUBLIC_API_MODE=mock`). Design system, auth flow, document list/detail, OCR review, RAG search, chatbot, admin pages all built.
- Backend (apps/api): FastAPI scaffold with auth module (login, me, refresh, logout), Argon2id hashing, refresh token rotation, RBAC 3 roles, Alembic migrations (users + document_scopes + refresh_sessions), 91 tests passing, 84% coverage.
- OpenAPI contract: `docs/api/openapi.yaml` (OpenAPI 3.1) defines all endpoints.
- Docker Compose: `infra/docker/docker-compose.yml` with PostgreSQL+pgvector, Redis, MinIO, API containers.
- CI: GitHub Actions with 3 jobs (OpenAPI lint, Web quality gate, API quality gate). ALL GREEN.

## Requirements

### R1. Document Management & Storage (Phase B)
Implement RESTful document management APIs matching the OpenAPI contract (`docs/api/openapi.yaml`). This includes:
- Multi-part file upload with MinIO S3 storage
- Document CRUD with RBAC scope filtering (PUBLIC / STUDENT_AFFAIRS / INTERNAL)
- Document versioning and metadata management
- Async document processing pipeline via Celery background tasks
- PDF magic bytes validation and file size limits

### R2. OCR Pipeline (Phase C)
Build an OCR service that extracts text and bounding boxes from uploaded PDF/image documents:
- PaddleOCR as primary engine with Tesseract as fallback
- Extract text blocks with page numbers, bounding box coordinates, and confidence scores
- Store OCR results linked to document versions
- OCR review workflow (approve/reject/edit extracted text)

### R3. RAG Vector Search Engine (Phase D)
Implement semantic search using embeddings and pgvector:
- BGE-M3 multilingual embeddings (1024 dimensions)
- Chunk documents and store vectors in PostgreSQL pgvector
- Hybrid search: full-text + vector similarity with re-ranking
- Search API returning top-k results with relevance scores and source citations

### R4. RAG Chatbot with Citations (Phase E)
Build a streaming chatbot that answers questions using RAG context:
- Ollama local LLM integration (Qwen2.5 or Llama-3.1 8B) with provider adapter pattern
- LangChain pipeline: query → retrieve → generate with citations
- Streaming SSE responses with citation tracking (document name, page, bbox)
- Conversation history management

### R5. Frontend-Backend Integration (Phase F)
Switch the existing Next.js frontend from mock API mode to live backend:
- Replace `NEXT_PUBLIC_API_MODE=mock` with `live` and connect to real FastAPI endpoints
- Ensure all 12 routes work with real data
- End-to-end testing with Playwright

## Acceptance Criteria

### Backend API Completeness
- [ ] All endpoints in `docs/api/openapi.yaml` are implemented and return correct response shapes
- [ ] `uv run pytest` passes with ≥ 80% global coverage
- [ ] `uv run ruff check . && uv run ruff format --check . && uv run mypy app` all pass
- [ ] `docker compose -f infra/docker/docker-compose.yml up` starts all services healthy

### Document & Storage
- [ ] Upload a PDF file → stored in MinIO → metadata in PostgreSQL
- [ ] RBAC filtering: student sees only PUBLIC docs, staff sees STUDENT_AFFAIRS, admin sees all
- [ ] Files > 50MB rejected; non-PDF magic bytes rejected

### OCR
- [ ] Upload a PDF → OCR extracts text blocks with bbox coordinates
- [ ] OCR results stored and retrievable via API

### RAG Search & Chat
- [ ] Search query returns relevant document chunks with similarity scores
- [ ] Chat endpoint streams responses with document citations

### Frontend Integration
- [ ] `pnpm dev` with `NEXT_PUBLIC_API_MODE=live` connects to backend successfully
- [ ] `pnpm test` passes all existing tests

## Follow-up — 2026-08-11T15:02:40Z

Continue building the "Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên" (SoHoaTaiLieu_DATN). Phase B (Document Management) is ALREADY COMPLETE. You must implement Phase C, D, E, and F.

Working directory: E:\SoHoaTaiLieu_DATN
Integrity mode: development

## Current State (already done — DO NOT modify existing code)

- Frontend (apps/web): 12 routes, 26 tests, mock API mode.
- Backend (apps/api): FastAPI with auth module + Document Management module (Phase B). 132 tests passing. ruff/mypy/format all clean.
- OpenAPI contract: `docs/api/openapi.yaml`
- Docker Compose: `infra/docker/docker-compose.yml`

## Requirements

### R1. OCR Pipeline (Phase C)
Build an OCR service that extracts text and bounding boxes from uploaded PDF/image documents:
- PaddleOCR as primary engine with Tesseract as fallback
- Extract text blocks with page numbers, bounding box coordinates, and confidence scores
- Store OCR results linked to document versions
- OCR review workflow (approve/reject/edit extracted text)
- Celery async tasks for OCR processing

### R2. RAG Vector Search Engine (Phase D)
Implement semantic search using embeddings and pgvector:
- BGE-M3 multilingual embeddings (1024 dimensions)
- Chunk documents and store vectors in PostgreSQL pgvector
- Hybrid search: full-text + vector similarity with re-ranking
- Search API returning top-k results with relevance scores and source citations

### R3. RAG Chatbot with Citations (Phase E)
Build a streaming chatbot that answers questions using RAG context:
- Ollama local LLM integration (Qwen2.5 or Llama-3.1 8B) with provider adapter pattern
- LangChain pipeline: query → retrieve → generate with citations
- Streaming SSE responses with citation tracking (document name, page, bbox)
- Conversation history management

### R4. Frontend-Backend Integration (Phase F)
Switch the existing Next.js frontend from mock API mode to live backend:
- Replace `NEXT_PUBLIC_API_MODE=mock` with `live` and connect to real FastAPI endpoints
- Ensure all 12 routes work with real data
- End-to-end testing with Playwright

## Acceptance Criteria

### OCR (Phase C)
- [ ] Upload a PDF → OCR extracts text blocks with bbox coordinates
- [ ] OCR results stored and retrievable via API
- [ ] PaddleOCR + Tesseract fallback working

### RAG Search (Phase D)
- [ ] Search query returns relevant document chunks with similarity scores
- [ ] Hybrid search (full-text + vector) with re-ranking

### RAG Chat (Phase E)
- [ ] Chat endpoint streams responses with document citations
- [ ] Conversation history management

### Frontend Integration (Phase F)
- [ ] `pnpm dev` with `NEXT_PUBLIC_API_MODE=live` connects to backend successfully
- [ ] `pnpm test` passes all existing tests
- [ ] `pnpm build` succeeds

### Quality Gates
- [ ] `uv run pytest` passes with ≥ 80% global coverage
- [ ] `uv run ruff check . && uv run ruff format --check . && uv run mypy app` all pass

## Follow-up — 2026-08-11T09:02:48Z

Continue building the "Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên" (SoHoaTaiLieu_DATN). Phases B, C, D are ALREADY COMPLETE. You must implement Phase E and Phase F only.

Working directory: E:\SoHoaTaiLieu_DATN
Integrity mode: development

## Current State (DO NOT modify existing code unless necessary for integration)

- Frontend (apps/web): 12 routes, 26 tests, mock API mode (`NEXT_PUBLIC_API_MODE=mock`).
- Backend (apps/api): FastAPI with auth + documents + OCR + RAG search modules. 186 tests passing. ruff/mypy/format all clean.
- Search module at `apps/api/app/modules/search/` with hybrid RRF search.
- OCR engine at `apps/api/app/services/ocr_engine.py` with PaddleOCR + Tesseract.
- Embedding service at `apps/api/app/services/embedding.py` with BGE-M3.

## Requirements

### R1. RAG Chatbot with Citations (Phase E)
Build a streaming chatbot that answers questions using RAG context:
- Ollama local LLM integration (Qwen2.5 or Llama-3.1 8B) with provider adapter pattern
- LangChain pipeline: query → retrieve → generate with citations
- Streaming SSE responses with citation tracking (document name, page, bbox)
- Conversation history management
- New module: `apps/api/app/modules/chat/`
- Celery task for async chat if needed

### R2. Frontend-Backend Integration (Phase F)
Switch the existing Next.js frontend from mock API mode to live backend:
- Create/update API client in `apps/web` to connect to real FastAPI endpoints
- Replace `NEXT_PUBLIC_API_MODE=mock` with `live` mode
- Ensure all 12 routes work with real data from backend
- Update any type mismatches between frontend types and backend responses

## Acceptance Criteria

### RAG Chat (Phase E)
- [ ] Chat endpoint streams responses with document citations
- [ ] Provider adapter pattern for LLM swapping
- [ ] Conversation history stored and retrievable

### Frontend Integration (Phase F)
- [ ] `pnpm dev` with `NEXT_PUBLIC_API_MODE=live` connects to backend
- [ ] `pnpm test` passes all existing tests
- [ ] `pnpm build` succeeds

### Quality Gates
- [ ] `uv run pytest` passes with ≥ 80% global coverage
- [ ] `uv run ruff check . && uv run ruff format --check . && uv run mypy app` all pass


