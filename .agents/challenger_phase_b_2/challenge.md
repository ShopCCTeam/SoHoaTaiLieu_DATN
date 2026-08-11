# Empirical Challenge Report — Phase B (Document Management & Storage)

**Challenger**: Challenger 2  
**Date**: 2026-08-11  
**Overall Verdict**: **FAILED** (3 test failures in `uv run pytest`, CRITICAL defect in Celery eager execution mode)

---

## 1. Summary of Verification Runs

| Command | Status | Details |
|---|---|---|
| `uv run ruff check app tests` | **PASSED** | 0 errors |
| `uv run pytest` | **FAILED** | 109 passed, 3 failed, 4 skipped (58.99s) |

### Failing Tests in standard test suite:
1. `tests/test_documents_upload.py::test_upload_valid_pdf_returns_202_accepted`
2. `tests/test_documents_upload.py::test_idempotency_replay`
3. `tests/test_documents_versions.py::test_document_versions_lifecycle`

---

## 2. Challenge Findings & Empirical Evidence

### Challenge 1 (CRITICAL): Celery Eager Task Execution Crash in Async Event Loop
- **Category**: Celery Task Eager Execution & Event Loop Concurrency
- **Location**: `app/worker/tasks.py:25` (`run_async`) & `app/worker/celery_app.py:29` (`task_always_eager`)
- **Empirical Observation**:
  - In testing/development mode (`app_env == "test"`), `task_always_eager = True` is set.
  - When `process_document_task.delay(job_id, version_id)` is invoked from an async FastAPI router endpoint, Celery executes `process_document_task` synchronously on the caller thread.
  - `process_document_task` calls `run_async(_async_process_document(...))` which attempts `loop.run_until_complete(...)` on a newly created event loop.
  - Python's `asyncio` raises:
    `RuntimeError: Cannot run the event loop while another loop is running`
- **Impact**:
  - All document upload (`POST /documents`), version upload (`POST /documents/{id}/versions`), and OCR re-trigger (`POST /documents/{id}/versions/{vid}/ocr`) endpoints fail immediately with internal server error in test/dev environment.
  - Test harness evidence: Reproducible via `uv run pytest tests/test_documents_upload.py`.

### Challenge 2 (HIGH): Non-Atomic Side Effect on Task Dispatch Failure
- **Category**: DB Transactions & Atomicity
- **Location**: `app/modules/documents/service.py:160` & `288`
- **Empirical Observation**:
  - In `create_document`, `create_document_version`, and `trigger_version_ocr`, `await session.commit()` is called **before** `process_document_task.delay()`.
  - When `process_document_task.delay()` raises `RuntimeError` (or broker connection error), the `Document`, `DocumentVersion`, and `Job` records are already committed to PostgreSQL in `QUEUED` state.
  - The HTTP request crashes with an exception, leaving orphaned `Job` records stuck in `QUEUED` status in DB forever.

### Challenge 3 (MEDIUM): Service Layer Does Not Filter Soft-Deleted Documents
- **Category**: Soft Deletion Invariants
- **Location**: `app/modules/documents/service.py:67` (`get_document_by_id`)
- **Empirical Observation**:
  - `get_document_by_id` queries `select(Document)...where(Document.id == document_id)` without checking `Document.deleted_at.is_(None)`.
  - While router handlers call `check_document_access` (which checks `doc.deleted_at`), any background Celery task, internal service function, or RAG module calling `get_document_by_id` retrieves soft-deleted document records.

### Challenge 4 (MEDIUM): Version Approval Superseding Invariant Missing
- **Category**: Version Approval Invariants
- **Location**: `app/modules/documents/service.py:351` (`approve_document_version`)
- **Empirical Observation**:
  - Pre-approval invariant checks (`ocr_status == "SUCCEEDED"` and `requires_review == False`) are correctly enforced and return 409 Conflict if violated.
  - However, approving version `N` does not update previous approved versions' status to `SUPERSEDED` / `ARCHIVED`, nor does it update `supersedes_version_id` or `superseded_by_version_id`.
  - If an older version is approved, `document.latest_version` is overwritten to the older version's version number.

---

## 3. Stress Test Results

| Scenario | Expected Behavior | Actual Behavior | Pass/Fail |
|---|---|---|---|
| Execute `uv run ruff check app tests` | 0 linter errors | 0 linter errors | **PASS** |
| Execute `uv run pytest` test suite | All 116 tests pass | 3 tests failed due to Celery eager loop exception | **FAIL** |
| Upload valid PDF in async request (Eager mode) | 202 Accepted with QUEUED/SUCCEEDED job | `RuntimeError: Cannot run the event loop while another loop is running` | **FAIL** |
| Service `get_document_by_id` on soft-deleted doc | Return None or filter deleted | Returns Document entity with `deleted_at` set | **FAIL (Inconsistency)** |
| Version approval on `ocr_status != SUCCEEDED` | 409 Conflict | 409 Conflict | **PASS** |
| Post-commit dispatch error state | Rollback or update Job status to FAILED | DB committed with `QUEUED` status, job orphaned | **FAIL** |

---

## 4. Recommendations & Mitigations

1. **Fix Celery Eager Async Execution**:
   - In `app/worker/tasks.py`, replace `run_async` with a check using `asyncio.get_event_loop()` or `asyncio.run()` or `asgiref.sync.async_to_sync`, or detect if a loop is already running and await/nest or run in threadpool (e.g. `concurrent.futures`).
2. **Atomic Dispatch / Transaction Safety**:
   - Move task dispatch inside transaction block or handle dispatch exceptions to update `job.status = "FAILED"` if enqueue fails.
3. **Soft Delete Filter in Service Layer**:
   - Add `include_deleted: bool = False` flag to `get_document_by_id` defaulting to `False` (`where(Document.deleted_at.is_(None))`).
4. **Version Approval Lifecycle Improvements**:
   - On approval of a new version, set prior approved versions to `SUPERSEDED` and update version lineage fields (`supersedes_version_id`).
