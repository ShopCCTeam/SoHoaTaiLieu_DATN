## 2026-08-11T06:01:18Z

You are Worker for Phase B (Document Management & Storage) of the SoHoaTaiLieu_DATN project.

Your working directory is: E:\SoHoaTaiLieu_DATN\.agents\worker_phase_b

Objective:
Implement Phase B: Document Management & Storage APIs, MinIO S3 storage integration, SQLAlchemy models & Alembic migration, Celery async processing pipeline, PDF magic bytes validation, RBAC scope filtering, RFC 7807 error handling, and comprehensive unit/integration tests.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Context & Design References:
- Explorer 1 Analysis: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_1\analysis.md`
- Explorer 3 Analysis: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_3\analysis.md`
- OpenAPI Specification: `docs/api/openapi.yaml`
- Project Rules: `AGENTS.md` and `.agents/rules/` (Clean Architecture, Async SQLAlchemy, RFC 7807)

Tasks to Implement (in `apps/api/`):
1. **Models & Migrations**:
   - `apps/api/app/models/document.py` (`Document` model)
   - `apps/api/app/models/document_version.py` (`DocumentVersion` model)
   - `apps/api/app/models/job.py` (`Job` model)
   - Update `apps/api/app/models/__init__.py`
   - Alembic migration script for `documents`, `document_versions`, `jobs` tables in `apps/api/alembic/versions/` (run `uv run alembic upgrade head` or ensure migration is clean and applied during tests).
2. **Storage & Validation**:
   - `apps/api/app/services/storage.py` (MinIO S3 / Local fallback storage service)
   - `apps/api/app/modules/documents/security.py` (PDF magic bytes `%PDF-` check, 50MB size limit, MIME `application/pdf` check).
3. **Celery Worker & Async Pipeline**:
   - `apps/api/app/worker/celery_app.py` & `apps/api/app/worker/tasks.py` (Celery app setup, Redis broker config in `core/config.py`, async `process_document_task` updating job status `QUEUED` -> `PROCESSING` -> `SUCCEEDED`/`FAILED`).
4. **API Modules & Routers**:
   - `apps/api/app/modules/documents/schemas.py`, `service.py`, `dependencies.py`, `router.py`
     Endpoints:
     - `GET /api/v1/documents` (list with pagination & RBAC scope filter: student sees PUBLIC/STUDENT_AFFAIRS only; staff/admin see all; filter deleted_at)
     - `POST /api/v1/documents` (upload PDF, Idempotency-Key header, returns 202 Accepted + job_id)
     - `GET /api/v1/documents/{id}` (detail, RBAC scope check)
     - `PATCH /api/v1/documents/{id}` (update metadata)
     - `DELETE /api/v1/documents/{id}` (admin only soft-delete)
     - `GET /api/v1/documents/{id}/versions`
     - `POST /api/v1/documents/{id}/versions`
     - `GET /api/v1/documents/{id}/versions/{vid}`
     - `PATCH /api/v1/documents/{id}/versions/{vid}/metadata`
     - `POST /api/v1/documents/{id}/versions/{vid}/ocr` (trigger OCR job, 202 Accepted)
     - `POST /api/v1/documents/{id}/versions/{vid}/approve` (approve version invariant check)
   - `apps/api/app/modules/jobs/schemas.py`, `router.py`
     - `GET /api/v1/jobs/{id}` (polling job status)
     - `POST /api/v1/jobs/{id}/cancel`
   - Register routers in `apps/api/app/main.py`.
5. **Unit & Integration Tests**:
   - Implement test files in `apps/api/tests/`: `test_documents_router.py`, `test_documents_rbac.py`, `test_documents_upload.py`, `test_documents_versions.py`, `test_jobs_router.py`, `test_pdf_validator.py`.
   - Use `CELERY_TASK_ALWAYS_EAGER = True` for testing async tasks synchronously in pytest.

Verification Requirements:
- Execute and pass all quality gates:
  1. `uv run pytest` (must pass with >= 80% global coverage)
  2. `uv run ruff check app tests`
  3. `uv run ruff format --check app tests`
  4. `uv run mypy app`

Output Requirements:
- Write implementation log to `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_b\changes.md`.
- Write handoff report to `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_b\handoff.md` including exact build/test output and verification evidence.
- Send message to parent (conversation ID: 9f83b9ff-33a4-4ee5-a9e2-f52e7b90ad52) when finished.
