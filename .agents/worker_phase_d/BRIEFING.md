# BRIEFING — 2026-08-11T15:34:00+07:00

## Mission
Implement Phase D (RAG Vector Search Engine) for SoHoaTaiLieu_DATN in `apps/api/`.

## 🔒 My Identity
- Archetype: implementer/qa/specialist
- Roles: implementer, qa, specialist
- Working directory: E:\SoHoaTaiLieu_DATN\.agents\worker_phase_d
- Original parent: 5e173a0b-bf4c-477a-806c-026661dd5ad1
- Milestone: Phase D - RAG Vector Search Engine

## 🔒 Key Constraints
- Dual SQLite (json vector fallback) & PostgreSQL pgvector (Vector(1024)) and full-text search (tsvector).
- Alembic migration 0005_document_chunks_pgvector.py with HNSW cosine index and GIN tsvector index.
- EmbeddingService (BGE-M3 1024-dim primary adapter, deterministic SHA-256 Mock fallback adapter for pytest/dev).
- ChunkingService with recursive text splitting preserving chunk_index, page_number, block_ids, text, min-max envelope bbox [x0, y0, x1, y1].
- Celery task index_document_chunks_task triggered automatically after OCR succeeds.
- REST APIs POST /search & GET /search with RRF hybrid search and RBAC scope filtering (PUBLIC, STUDENT_AFFAIRS, INTERNAL).
- OpenAPI spec update docs/api/openapi.yaml.
- Unit & integration tests in tests/test_search.py, tests/test_chunking.py, tests/test_embedding.py.
- Quality checks: uv run pytest (>= 80% coverage), uv run ruff check app tests, uv run ruff format --check app tests, uv run mypy app.
- Icon rule: SVG icons only (Lucide React or SVG). Communication: 100% Vietnamese with user.

## Current Parent
- Conversation ID: 5e173a0b-bf4c-477a-806c-026661dd5ad1
- Updated: 2026-08-11T15:34:00+07:00

## Task Summary
- **What to build**: Phase D RAG Vector Search Engine (DocumentChunk ORM, Migration, EmbeddingService, ChunkingService, Celery Task, Search API, OpenAPI spec, tests).
- **Success criteria**: All tests pass (186 passed, 4 skipped, 80.18% coverage), ruff check/format clean, mypy clean, RRF hybrid search + RBAC scope filter working genuine logic.
- **Interface contracts**: `docs/api/openapi.yaml`, FastAPI app structure in `apps/api/app`.

## Key Decisions Made
- Created `DocumentChunk` model with `Vector(1024).with_variant(JSON, "sqlite")` and `TSVECTOR().with_variant(Text, "sqlite")`.
- Created Alembic migration `0005_document_chunks_pgvector.py` supporting pgvector HNSW cosine index and GIN tsvector index on PostgreSQL, with SQLite fallback.
- Implemented `EmbeddingService` with Strategy pattern: `BGEM3EmbeddingStrategy` (1024-dim BGE-M3 primary adapter) and `MockEmbeddingStrategy` (deterministic SHA-256 L2-normalized 1024-dim vector for dev/test).
- Implemented `ChunkingService` with recursive text splitting and min-max envelope bounding box calculation `[x0, y0, x1, y1]`.
- Implemented Celery task `index_document_chunks_task` and integrated auto-indexing into document OCR completion pipeline.
- Implemented REST APIs `GET /search` and `POST /search` using RRF (Reciprocal Rank Fusion) hybrid search combining vector similarity and full-text keyword search with RBAC scope checking.
- Updated `docs/api/openapi.yaml` with search endpoints and schemas.
- Written thorough test suites in `tests/test_embedding.py`, `tests/test_chunking.py`, `tests/test_search.py`, and updated `tests/test_alembic.py` & `tests/test_phase_c_challenger2_stress.py`.
- Quality verification completed: `pytest` passed 186/190 (80.18% coverage), `ruff check` passed, `ruff format` clean, `mypy` 0 errors.

## Artifact Index
- `.agents/worker_phase_d/ORIGINAL_REQUEST.md` — Original Request
- `.agents/worker_phase_d/BRIEFING.md` — Current Briefing
- `.agents/worker_phase_d/progress.md` — Progress log
- `.agents/worker_phase_d/handoff.md` — Handoff report

## Change Tracker
- **Files modified**:
  - `apps/api/pyproject.toml` (Added pgvector dependency)
  - `apps/api/app/models/document_chunk.py` (Created DocumentChunk ORM model)
  - `apps/api/app/models/__init__.py` (Re-exported DocumentChunk)
  - `apps/api/alembic/env.py` (Imported models for Alembic autodiscovery)
  - `apps/api/alembic/versions/0005_document_chunks_pgvector.py` (Created 0005 migration)
  - `apps/api/app/core/config.py` (Added embedding settings)
  - `apps/api/app/services/embedding.py` (Implemented EmbeddingService & strategies)
  - `apps/api/app/services/chunking.py` (Implemented ChunkingService & envelope bbox)
  - `apps/api/app/worker/tasks.py` (Implemented index_document_chunks_task & auto-trigger)
  - `apps/api/app/modules/search/schemas.py` (Created Search API schemas)
  - `apps/api/app/modules/search/service.py` (Implemented RRF Hybrid Search & scope filter)
  - `apps/api/app/modules/search/router.py` (Implemented GET & POST /search endpoints)
  - `apps/api/app/modules/search/__init__.py` (Created search module package)
  - `apps/api/app/main.py` (Registered search_router)
  - `docs/api/openapi.yaml` (Updated OpenAPI spec with search paths & schemas)
  - `apps/api/tests/test_alembic.py` (Updated migration tests for 0005)
  - `apps/api/tests/test_phase_c_challenger2_stress.py` (Updated head revision check to 0005)
  - `apps/api/tests/test_embedding.py` (Created embedding unit tests)
  - `apps/api/tests/test_chunking.py` (Created chunking unit tests)
  - `apps/api/tests/test_search.py` (Created search & indexing integration tests)
- **Build status**: PASS
- **Pending issues**: None

## Quality Status
- **Build/test result**: PASS (186 passed, 4 skipped, 80.18% coverage)
- **Lint status**: CLEAN (ruff check clean, ruff format clean, mypy clean)
- **Tests added/modified**: `test_embedding.py`, `test_chunking.py`, `test_search.py`, `test_alembic.py`, `test_phase_c_challenger2_stress.py`
