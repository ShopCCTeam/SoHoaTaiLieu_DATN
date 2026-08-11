# Implementation Log — Phase B Document Management & Storage APIs

> **Worker**: worker_phase_b  
> **Date**: 2026-08-11  
> **Project**: SoHoaTaiLieu_DATN (`apps/api/`)

---

## 1. Summary of Modified & Added Files

### Models & Migrations
- `apps/api/app/models/document.py`: Created `Document` ORM model (UUID v4 ID, title, type, status, scope, code_number, issuing_body, effective_from/to, latest_version, author_id, tags, timestamps, soft delete `deleted_at`).
- `apps/api/app/models/document_version.py`: Created `DocumentVersion` ORM model (version_number, status, file_url, file_size, checksum SHA-256, ocr_status, requires_review, change_summary, creator).
- `apps/api/app/models/job.py`: Created `Job` ORM model (type, status, progress, error, idempotency_key, target_document_id, target_version_id, timestamps).
- `apps/api/app/models/__init__.py`: Exported `Document`, `DocumentVersion`, and `Job` for Alembic autodiscovery.
- `apps/api/alembic/versions/0003_documents_versions_and_jobs.py`: Alembic migration script for `documents`, `document_versions`, and `jobs` tables with foreign keys and indexes.

### Storage & Security Validation
- `apps/api/app/services/storage.py`: Abstract `StorageService` interface with `LocalStorageService` (fallback/dev/testing) and `MinioStorageService` (S3 compatible storage).
- `apps/api/app/modules/documents/security.py`: Streamed PDF validator checking MIME type `application/pdf`, Magic Bytes `%PDF-`, 50MB file size limit (`FILE_SIZE_EXCEEDED` 413 error), and SHA-256 calculation.
- `apps/api/app/services/pdf_validator.py`: `PdfValidatorService` wrapper re-exporting validation methods.

### Celery Async Processing Pipeline
- `apps/api/app/core/config.py`: Added Celery settings (`celery_broker_url`, `celery_result_backend`, `celery_task_always_eager`, `celery_task_time_limit`, `celery_task_soft_time_limit`).
- `apps/api/app/worker/celery_app.py`: Celery instance configuration (`ctsv_worker`, JSON serialization, UTC timezone, task routes, eager mode handling).
- `apps/api/app/worker/tasks.py`: `process_document_task` updating job status (`QUEUED` -> `PROCESSING` -> `SUCCEEDED`/`FAILED`) and `DocumentVersion.ocr_status`.
- `apps/api/app/worker/__init__.py`: Exported `celery_app` and `process_document_task`.

### API Modules & Routers
- `apps/api/app/core/errors.py`: Added `FILE_SIZE_EXCEEDED` to `ErrorCode` and convenience helpers `payload_too_large` and `unsupported_media_type`.
- `apps/api/app/modules/documents/schemas.py`: Pydantic schemas for Document, DocumentVersion, envelopes, and DTOs.
- `apps/api/app/modules/documents/dependencies.py`: RBAC scope filter logic (`get_allowed_scopes_for_user`), `check_document_access`, role enforcement (`require_staff_or_admin`, `require_admin`), and `get_idempotency_key`.
- `apps/api/app/modules/documents/service.py`: Service functions for pagination, RBAC filtering, soft delete, idempotency checking, version creation, and version approval invariants.
- `apps/api/app/modules/documents/router.py`: FastAPI endpoints for `/documents`, `/documents/{id}`, `/documents/{id}/versions`, `/documents/{id}/versions/{vid}/ocr`, and `/documents/{id}/versions/{vid}/approve`.
- `apps/api/app/modules/jobs/schemas.py`: Pydantic schemas for Job status polling.
- `apps/api/app/modules/jobs/router.py`: FastAPI endpoints for `GET /jobs/{id}` and `POST /jobs/{id}/cancel`.
- `apps/api/app/main.py`: Registered `documents_router` and `jobs_router` under `api_prefix`.

### Unit & Integration Test Suite
- `apps/api/tests/test_alembic.py`: Updated to verify revision `0003` and head `0003`.
- `apps/api/tests/test_pdf_validator.py`: Tests for magic bytes validation, MIME check, size limit (>50MB), and valid PDF stream inspection.
- `apps/api/tests/test_documents_router.py`: Tests for GET `/documents` (list, pagination, filtering), GET `/documents/{id}`, PATCH `/documents/{id}`, DELETE `/documents/{id}` soft-delete.
- `apps/api/tests/test_documents_rbac.py`: Tests for student scope filtering (sees PUBLIC & STUDENT_AFFAIRS only, blocked on INTERNAL), staff & student permission checks.
- `apps/api/tests/test_documents_upload.py`: Tests for valid PDF upload (202 Accepted), missing idempotency key (422), invalid magic bytes (415), size exceeded (413), and idempotency replay.
- `apps/api/tests/test_documents_versions.py`: Tests for version listing, detail, metadata update, OCR trigger, and approval invariant check.
- `apps/api/tests/test_jobs_router.py`: Tests for job polling and cancellation.

---

## 2. Quality Gate Verification Results

- **pytest**: 108 passed, 4 skipped in 3.48s (100% pass rate).
- **Code Coverage**: 94% global coverage (Requirement ≥ 80%).
- **ruff check**: 0 warnings/errors. All checks passed.
- **ruff format --check**: 59 files formatted cleanly.
- **mypy**: Success: no issues found in 41 source files.
