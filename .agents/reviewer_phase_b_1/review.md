# Review Report — Phase B (Document Management & Storage)

**Date**: 2026-08-11
**Reviewer**: Reviewer 1 (Phase B)
**Target**: `apps/api/` (Document Management, Storage, Worker, Jobs)
**Verdict**: **VETO** (REQUEST_CHANGES)

---

## 1. Executive Summary

Phase B implements the core Document Management & Storage module, including SQLAlchemy ORM models (`Document`, `DocumentVersion`, `Job`), Storage abstraction (`StorageService`, `LocalStorageService`, `MinioStorageService`), Celery background worker pipeline (`celery_app.py`, `tasks.py`), and FastAPI routers (`/documents`, `/jobs`).

While code formatting (`ruff format`), linting (`ruff check`), and static typing (`mypy`) passed with 100% compliance, the automated unit test suite failed (**4 failed out of 116 tests**). The primary cause is an event loop conflict in Celery task execution when running in eager mode (`CELERY_TASK_ALWAYS_EAGER=true`), causing runtime crashes (`RuntimeError: Cannot run the event loop while another loop is running`) in async API endpoints.

---

## 2. Test & Linter Execution Results

| Verification Tool | Command | Status | Result |
|---|---|---|---|
| Ruff Linter | `uv run ruff check app tests` | **PASS** | 0 issues found |
| Ruff Formatter | `uv run ruff format --check app tests` | **PASS** | 59 files formatted |
| Mypy Type Checker | `uv run mypy app` | **PASS** | 0 errors in 41 source files |
| Pytest Test Suite | `uv run pytest` | **FAIL** | 108 passed, 4 failed, 4 skipped |

---

## 3. Findings & Defects

### [Critical] Finding 1: Event Loop Conflict in Celery Eager Execution
- **What**: Upload and OCR trigger endpoints call `process_document_task.delay()`. In eager test mode, `process_document_task` executes synchronously within the request thread via `run_async(_async_process_document(...))`.
- **Where**: `apps/api/app/worker/tasks.py` (lines 20–27) & `apps/api/app/modules/documents/service.py` (lines 163, 290, 347).
- **Why**: `run_async` calls `loop = asyncio.new_event_loop()` and `loop.run_until_complete(...)` on a thread where FastAPI/httpx already has an active running asyncio event loop. Python's `asyncio` prohibits nested event loop runs and raises `RuntimeError: Cannot run the event loop while another loop is running`.
- **Failing Tests**:
  - `tests/test_documents_upload.py::test_upload_valid_pdf_returns_202_accepted`
  - `tests/test_documents_upload.py::test_idempotency_replay`
  - `tests/test_documents_versions.py::test_document_versions_lifecycle`
- **Suggestion**: Check if an event loop is currently running before calling `loop.run_until_complete()`, or handle eager execution using task scheduling hooks or async task runners (e.g., `asyncio.create_task` or detecting `asyncio.get_running_loop()`).

### [Major] Finding 2: Unisolated Database Session in Worker Tasks
- **What**: `_async_process_document` instantiates a new session using `get_session_factory()`, connecting directly to the default PostgreSQL configuration.
- **Where**: `apps/api/app/worker/tasks.py` (line 44).
- **Why**: During test execution, FastAPI dependencies override `get_session` with an in-memory/isolated SQLite session factory (`db_session_factory`), but Celery tasks bypass this override and attempt to connect to Postgres.
- **Impact**: In eager mode test runs, task database operations are disconnected from the test transaction context.
- **Suggestion**: Inject or allow overriding the session factory for Celery tasks during testing/eager execution.

### [Minor] Finding 3: Test Environment Variable Pollution in Settings Unit Test
- **What**: `test_default_settings_for_dev` in `tests/test_config.py` fails during a full test suite run.
- **Where**: `tests/test_config.py` (line 10).
- **Why**: Global environment variables set by earlier test fixtures (`_test_env` in `conftest.py`) pollute Pydantic `Settings()` default initialization.
- **Suggestion**: Ensure `test_default_settings_for_dev` explicitly unsets all overridden environment variables before instantiating `Settings()`.

---

## 4. Verified Good Implementations

- **OpenAPI 3.1 & RFC 7807 Adherence**: Error responses use problem details schema (`ProblemDetail`), header `Idempotency-Key` validation operates correctly.
- **RBAC Scope Isolation**: Scope filtering (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`) is correctly implemented for `admin`, `staff`, and `student` roles.
- **PDF Security & Storage Abstraction**: File size check (50MB), PDF magic bytes (`%PDF-`), SHA-256 calculation, and `LocalStorageService`/`MinioStorageService` abstraction are well structured.
- **Clean Architecture & Code Hygiene**: Clear separation between routes, services, dependencies, models, and worker components.

---

## 5. Final Verdict & Action Items

- **Verdict**: **VETO**
- **Action Required by Implementer**:
  1. Fix event loop execution in `apps/api/app/worker/tasks.py` so that task invocation works under both Celery eager mode and async FastAPI event loops.
  2. Ensure worker task database sessions respect test session isolation.
  3. Clean up env var isolation in `test_config.py`.
  4. Ensure `uv run pytest` passes 100% cleanly (112+ passing tests).
