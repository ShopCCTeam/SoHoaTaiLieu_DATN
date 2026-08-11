# Phase B Code Review Report — Document Management & Storage

**Reviewer**: Reviewer 2 (Phase B)  
**Date**: 2026-08-11  
**Target Scope**: Phase B implementation in `apps/api/` (Document Management, Storage, PDF Validation, Jobs Polling, RFC 7807, Idempotency)  
**Verdict**: **VETO**

---

## Executive Summary

As Reviewer 2 for Phase B, an independent, adversarial critic evaluation of the Phase B implementation in `apps/api/` was conducted. While static analysis tools (`ruff check`, `ruff format`, `mypy`) pass cleanly, **the test suite fails when executed (`uv run pytest` has 4 failing tests)** due to event loop conflicts in Celery task execution. Furthermore, critical architecture defects in task dispatch atomicity, soft-deletion filtering, and idempotency payload mismatch validation were identified.

---

## Static Analysis & Verification Summary

| Check | Command | Status | Result / Details |
|---|---|---|---|
| Test Suite | `uv run pytest` | ❌ **FAIL** | 4 failed, 108 passed, 4 skipped |
| Linter | `uv run ruff check app tests` | ✅ PASS | All checks passed (0 errors) |
| Formatter | `uv run ruff format --check app tests` | ✅ PASS | 59 files already formatted |
| Type Checker | `uv run mypy app` | ✅ PASS | Success: no issues found in 41 source files |

---

## Detailed Findings

### Finding 1 [CRITICAL]: Test Suite Failures & Celery Eager Execution Event Loop Conflict
- **What**: Executing `uv run pytest` fails with 4 test failures:
  - `tests/test_documents_upload.py::test_upload_valid_pdf_returns_202_accepted`
  - `tests/test_documents_upload.py::test_idempotency_replay`
  - `tests/test_documents_versions.py::test_document_versions_lifecycle`
  - `tests/test_config.py::test_default_settings_for_dev`
- **Location**: `app/worker/tasks.py` (`run_async`), `app/modules/documents/service.py`, `tests/conftest.py`
- **Why**:
  - In `app/worker/tasks.py`, `run_async` executes:
    ```python
    def run_async(coro: Any) -> Any:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    ```
  - When Celery runs in eager mode (`CELERY_TASK_ALWAYS_EAGER=true`, default in `conftest.py`), `process_document_task.delay(job_id, version_id)` executes synchronously in the SAME thread as the FastAPI ASGI handler.
  - Python's `asyncio` raises `RuntimeError: Cannot run the event loop while another loop is running` because an active event loop is already handling the HTTP request.
  - In addition, `test_default_settings_for_dev` in `test_config.py` fails due to uncleaned environment variables / cached settings mutated across test modules.
- **Suggestion**:
  - In `app/worker/tasks.py`, detect whether an event loop is already running (e.g. `asyncio.get_event_loop()` / `asyncio.get_running_loop()`). If running, schedule the coroutine via `asyncio.create_task()` or `asyncio.run_coroutine_threadsafe()`; if not, use `asyncio.run()`.
  - Isolate environment variable mutations in `test_config.py` so test settings do not bleed across modules.

---

### Finding 2 [MAJOR]: DB Transaction & Task Dispatch Atomicity Flaw
- **What**: `service.create_document`, `service.create_document_version`, and `service.trigger_version_ocr` execute `await session.commit()` BEFORE invoking `process_document_task.delay(...)` without error handling.
- **Location**: `app/modules/documents/service.py` (lines 160-163, 288-290, 345-347)
- **Why**:
  - If Celery broker (Redis) is unreachable or `process_document_task.delay(...)` raises an exception, the HTTP request crashes with HTTP 500.
  - However, the `Document` (DRAFT), `DocumentVersion` (DRAFT, ocr_status=QUEUED), and `Job` (status=QUEUED) records are already committed to PostgreSQL and remain permanently orphaned in `QUEUED` state.
- **Suggestion**:
  - Wrap task dispatch in a `try...except` block post-commit to mark the Job status as `FAILED` with a description ("Task queue dispatch failed"), or adopt an outbox pattern / background worker polling loop to retry `QUEUED` jobs.

---

### Finding 3 [MAJOR]: Soft-Deletion Data Isolation Leakage
- **What**: `service.get_document_by_id` fetches documents matching `Document.id == document_id` WITHOUT checking `Document.deleted_at.is_(None)`.
- **Location**: `app/modules/documents/service.py` (lines 67-73), `app/modules/documents/router.py` (line 140)
- **Why**:
  - While `service.list_documents` correctly filters `deleted_at.is_(None)`, `get_document_by_id` retrieves soft-deleted documents.
  - As a result, endpoints including `GET /documents/{id}`, `PATCH /documents/{id}`, `GET /documents/{id}/versions`, `POST /documents/{id}/versions`, `POST /documents/{id}/versions/{vid}/ocr`, and `POST /documents/{id}/versions/{vid}/approve` accept and return soft-deleted documents instead of returning HTTP 404 `NOT_FOUND`.
- **Suggestion**:
  - Update `get_document_by_id(session, document_id, include_deleted=False)` to default to filtering out soft-deleted documents (`Document.deleted_at.is_(None)`).

---

### Finding 4 [MINOR]: Idempotency Key Payload Mismatch Unhandled
- **What**: Reusing an `Idempotency-Key` header returns the existing `document_id` and `job_id` regardless of whether the request payload matches.
- **Location**: `app/modules/documents/service.py` (lines 96-104, 240-248)
- **Why**:
  - `ErrorCode.IDEMPOTENCY_KEY_MISMATCH` is defined in `app/core/errors.py`, but `create_document` does not store or verify the SHA-256 hash/checksum of the request payload against existing jobs.
  - If a user sends a different file or title with the same `Idempotency-Key`, the API silently returns the previous document instead of returning HTTP 409 `IDEMPOTENCY_KEY_MISMATCH`.
- **Suggestion**:
  - Store request payload hash (e.g. SHA-256 of file checksum + metadata) in the `Job` record or idempotency record and verify payload match on replay, raising `idempotency_mismatch` if they differ.

---

### Finding 5 [MINOR]: Content-Type Parsing Strictness Edge Case
- **What**: `validate_pdf_bytes` and `validate_upload_file` check `content_type.lower() != "application/pdf"`.
- **Location**: `app/modules/documents/security.py` (lines 32, 57)
- **Why**:
  - Standard HTTP Content-Type headers can include media type parameters (e.g. `application/pdf; name="report.pdf"` or `application/pdf; charset=binary`). Exact string equality fails and rejects valid requests with HTTP 415.
- **Suggestion**:
  - Parse media type with `content_type.split(";")[0].strip().lower()` before comparing against `application/pdf`.

---

## Verified Claims & Conformance Matrix

| Claim / Requirement | Verified Via | Status | Notes |
|---|---|---|---|
| PDF Magic Bytes (`%PDF-`) | `validate_pdf_bytes` & `validate_upload_file` | ✅ PASS | Validated at byte stream start |
| 50MB Limit (HTTP 413) | `validate_pdf_bytes` & chunked stream | ✅ PASS | Raises HTTP 413 `FILE_SIZE_EXCEEDED` |
| Content-Type check | `security.py` | ⚠️ PARTIAL | Fails when header includes parameters |
| RFC 7807 Error Format | `app/core/errors.py` | ✅ PASS | `application/problem+json` response |
| Jobs Polling (`GET /jobs/{id}`) | `app/modules/jobs/router.py` | ✅ PASS | Returns `JobResponseEnvelope` |
| Idempotency Key Header | `POST /documents` header requirement | ⚠️ PARTIAL | Missing request payload signature validation |
| Static Analysis Clean | `ruff`, `mypy` | ✅ PASS | Lint, format, and typecheck clean |
| Pytest Test Suite | `uv run pytest` | ❌ FAIL | 4 test failures |

---

## Conclusion & Verdict

**Verdict: VETO**

The implementation cannot be approved in its current state due to test suite failures (`uv run pytest` failure exit code 1), Celery task execution crash in eager/test mode, soft-deletion data leakage, and unhandled task dispatch failures. The implementation team must address these issues before Phase B can be approved.
