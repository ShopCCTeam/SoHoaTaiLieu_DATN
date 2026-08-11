## 2026-08-11T08:22:35Z
You are Worker Phase D for 'Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên' (SoHoaTaiLieu_DATN).
Your working directory is `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_d`.

## Objectives
Implement Phase D (RAG Vector Search Engine) in `apps/api/`:
1. ORM Model & Migration:
   - Create `DocumentChunk` ORM model (`apps/api/app/models/document_chunk.py`), register in `app/models/__init__.py`. Support dual SQLite (json vector fallback) & PostgreSQL pgvector (`Vector(1024)`) and full-text search (`tsvector`).
   - Create Alembic migration `0005_document_chunks_pgvector.py` creating `document_chunks` table, HNSW cosine index, and GIN tsvector index.
2. Embedding & Chunking Services:
   - Implement `EmbeddingService` (`app/services/embedding.py`) with Strategy pattern (BGE-M3 1024-dim primary adapter, deterministic SHA-256 Mock fallback adapter for pytest/dev).
   - Implement `ChunkingService` (`app/services/chunking.py`) with recursive text splitting from `OCRBlock`/`OCRPage` data preserving `chunk_index`, `page_number`, `block_ids`, `text`, and unified Min-Max Envelope bounding box (`[x0, y0, x1, y1]`).
3. Search APIs & Celery Indexing Task:
   - Implement Celery task `index_document_chunks_task` (`app/worker/tasks.py`) triggered automatically after OCR succeeds.
   - Implement REST APIs `POST /search` and `GET /search` (`app/modules/search/router.py`, `service.py`, `schemas.py`) with RRF hybrid search (vector similarity + full-text search) and RBAC scope filtering (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`).
4. OpenAPI Spec & Tests:
   - Update `docs/api/openapi.yaml` with Search API schemas and routes.
   - Write thorough unit & integration tests (`tests/test_search.py`, `tests/test_chunking.py`, `tests/test_embedding.py`).
   - Run quality checks: `uv run pytest` (>= 80% coverage), `uv run ruff check app tests`, `uv run ruff format --check app tests`, `uv run mypy app`.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Report all results, test commands, coverage percentages, and file paths in `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_d\handoff.md` and send a message back to parent.
