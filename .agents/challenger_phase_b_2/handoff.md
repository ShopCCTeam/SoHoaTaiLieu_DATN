# HANDOFF REPORT — Challenger 2 (Phase B Verification)

## 1. Observation

- Executed `uv run ruff check app tests` in `apps/api`:
  - **Result**: 0 errors (PASSED cleanly).
- Executed `uv run pytest` in `apps/api`:
  - **Result**: 109 passed, 3 failed, 4 skipped (Total 116 items).
  - **Failed tests**:
    1. `tests/test_documents_upload.py::test_upload_valid_pdf_returns_202_accepted`
    2. `tests/test_documents_upload.py::test_idempotency_replay`
    3. `tests/test_documents_versions.py::test_document_versions_lifecycle`
- Error Traceback from pytest:
  `RuntimeError: Cannot run the event loop while another loop is running`
  Triggered at `app/worker/tasks.py:25` (`loop.run_until_complete(coro)` in `run_async`) when called via `process_document_task.delay(job_id, version_id)` from `app/modules/documents/service.py:163` during an HTTP request.
- Inspected `app/modules/documents/service.py`:
  - `get_document_by_id` (line 67): `select(Document)...where(Document.id == document_id)` — does NOT filter `Document.deleted_at.is_(None)`.
  - `create_document` (line 160): calls `await session.commit()` BEFORE `process_document_task.delay()`.
- Inspected `app/modules/documents/service.py` (`approve_document_version` line 351):
  - Pre-approval invariant check: enforces `version.ocr_status == "SUCCEEDED"` and `version.requires_review == False` (raises 409 ApiError when violated).
  - Post-approval state: does not update prior approved versions to `SUPERSEDED` or set version relationship IDs.
- Created empirical verification test suite `tests/test_phase_b_challenger2.py` (4 tests), all 4 empirical tests passed, confirming findings.

## 2. Logic Chain

1. In test and local single-process environments, `app_env == "test"` sets `task_always_eager = True` in `app/worker/celery_app.py`.
2. When document upload / version upload / OCR re-trigger endpoints are hit, `.delay()` executes `process_document_task` synchronously inside the caller thread.
3. The caller thread is running the ASGI / FastAPI asyncio event loop.
4. `process_document_task` delegates to `run_async()`, which attempts `loop.run_until_complete()`.
5. `asyncio` raises `RuntimeError: Cannot run the event loop while another loop is running` because `run_until_complete` cannot be called nested on an active event loop.
6. This causes HTTP requests in eager mode to crash with unhandled exceptions, breaking integration tests and eager task execution.
7. Furthermore, because DB commit occurs prior to `.delay()`, any failure in `.delay()` leaves committed `Document` and `Job` records in `QUEUED` state without a running task.

## 3. Caveats

- Tests requiring a live PostgreSQL instance (`test_alembic.py`, `test_models_pg.py`) were skipped due to no PostgreSQL listening at `localhost:5432` in the test environment (SQLite in-memory fallback used for standard tests).
- In a production environment with a standalone Celery daemon worker process (where tasks are enqueued to Redis and executed in a separate worker process), the `RuntimeError` on `.delay()` does not occur because task execution is decoupled from the HTTP thread. However, it completely breaks local eager testing and unit/integration test suites.

## 4. Conclusion

- **Verdict**: **FAILED**
- Phase B implementation has a **CRITICAL bug** affecting Celery eager task execution in test/development environments, causing `uv run pytest` to fail with 3 test errors.
- Additionally, post-commit task dispatch atomicity, service-level soft delete filtering, and version superseding lineage require attention.

## 5. Verification Method

To independently verify these findings:

1. Run the test suite:
   ```bash
   cd apps/api
   uv run pytest
   ```
   Observe the 3 failing tests with `RuntimeError: Cannot run the event loop while another loop is running`.

2. Run linter:
   ```bash
   cd apps/api
   uv run ruff check app tests
   ```
   Observe 0 errors.

3. Run Challenger 2 empirical verification suite:
   ```bash
   cd apps/api
   uv run pytest tests/test_phase_b_challenger2.py
   ```
   Observe all 4 empirical verification tests passing and demonstrating the exact behaviors described.
