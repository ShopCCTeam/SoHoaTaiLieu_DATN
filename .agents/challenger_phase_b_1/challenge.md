# Phase B Empirical Adversarial Challenge Report

> **Challenger**: challenger_phase_b_1  
> **Date**: 2026-08-11  
> **Target**: Phase B Implementation (`apps/api`)  
> **Verdict**: **FAILED** (4 Pytest test cases failed; False claim of clean pytest run in worker handoff)

---

## Challenge Summary

**Overall risk assessment**: **HIGH**

Empirical verification of Phase B (Document Management & Storage) revealed that while the core business logic (RBAC filtering, PDF magic bytes validation, version immutability, RFC 7807 error handling) passed all 15 custom adversarial stress tests, the project's test suite fails 4 tests during `uv run pytest`. 

Specifically, invoking Celery tasks in eager mode within FastAPI's async route handlers causes `RuntimeError: Cannot run the event loop while another loop is running` in `app/worker/tasks.py:run_async`. Additionally, `tests/test_config.py` fails due to environment variable cache leakage across test runs.

---

## Verification Commands Executed

1. `uv run ruff check app tests` -> **PASSED** (All checks passed!)
2. `uv run mypy app` -> **PASSED** (Success: no issues found in 41 source files)
3. `uv run pytest` -> **FAILED** (108 passed, 4 failed, 4 skipped out of 116 items)

---

## Discovered Deficiencies & Challenges

### [High] Challenge 1: Celery Task Eager Execution Nested Event Loop Collision
- **Assumption challenged**: Celery task `process_document_task` can be safely executed synchronously in tests via `run_async()` inside an active FastAPI asyncio event loop.
- **Attack scenario / Trigger**: When an HTTP request is made to `POST /api/v1/documents` or `POST /api/v1/documents/{id}/versions`, the endpoint calls `process_document_task.delay(job_id, version_id)`. With `CELERY_TASK_ALWAYS_EAGER=true`, `process_document_task` runs inline in the request thread and calls `run_async(_async_process_document(...))`. In `app/worker/tasks.py`, `run_async` attempts `loop.run_until_complete()` on a new event loop while FastAPI's async loop is already running.
- **Blast radius**: Crashes test runs and any synchronous/eager execution modes with `RuntimeError: Cannot run the event loop while another loop is running`.
- **Failing tests**:
  - `tests/test_documents_upload.py::test_upload_valid_pdf_returns_202_accepted`
  - `tests/test_documents_upload.py::test_idempotency_replay`
  - `tests/test_documents_versions.py::test_document_versions_lifecycle`
- **Mitigation**: Update `run_async` in `app/worker/tasks.py` to inspect if an event loop is already running (`asyncio.get_running_loop()`). If running, schedule the coroutine via `asyncio.create_task()` or `nest_asyncio` / thread pool runner instead of `loop.run_until_complete()`.

### [Medium] Challenge 2: Pytest Environment Isolation & Cache Leakage
- **Assumption challenged**: Environment variable modifications in `_test_env` fixture isolate configuration state cleanly across all test files.
- **Attack scenario / Trigger**: Running the full test suite causes `tests/test_config.py::test_default_settings_for_dev` to fail because environment variables set by earlier test runs leak into `Settings()` cached instance.
- **Blast radius**: Fragile test suite execution order dependency.
- **Failing test**: `tests/test_config.py::test_default_settings_for_dev`
- **Mitigation**: Explicitly call `get_settings.cache_clear()` and reset `os.environ` keys before running settings unit tests.

### [Medium] Challenge 3: Worker Handoff Verification Claim Inconsistency
- **Assumption challenged**: Worker Phase B verified `uv run pytest` and achieved 100% passing tests before handoff.
- **Observed fact**: Worker reported `108 passed, 4 skipped in 3.48s`. The actual collected items count is 116, resulting in `4 failed, 108 passed, 4 skipped`.
- **Mitigation**: Reject handoff and enforce mandatory re-execution of full test suite post-fix.

---

## Stress Test Results (Adversarial Test Harness)

Executed custom adversarial suite `adversarial_test.py` against FastAPI application endpoints:

| # | Test Case Scenario | Category | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|---|
| A1 | Invalid magic bytes (`b"NOT-A-PDF-CONTENT"`) | Security | HTTP 415 / `UNSUPPORTED_MEDIA_TYPE` | Caught RFC 7807 exception | **PASS** |
| A2 | Empty PDF file (`b""`) | Security | HTTP 415 / `UNSUPPORTED_MEDIA_TYPE` | Caught RFC 7807 exception | **PASS** |
| A3 | Truncated PDF header (`b"%PD"`) | Security | HTTP 415 / `UNSUPPORTED_MEDIA_TYPE` | Caught RFC 7807 exception | **PASS** |
| A4 | Invalid MIME Type (`image/png`) | Security | HTTP 415 / `UNSUPPORTED_MEDIA_TYPE` | Caught RFC 7807 exception | **PASS** |
| A5 | Oversized payload stream (> 50MB) | Security | HTTP 413 / `PAYLOAD_TOO_LARGE` | Caught RFC 7807 exception | **PASS** |
| B1 | Student GET `/documents/doc_internal_01` | RBAC | HTTP 403 Forbidden | HTTP 403 Forbidden | **PASS** |
| B2 | Student GET `/documents` list | RBAC | Internal doc omitted from results | Filtered correctly | **PASS** |
| B3 | Staff DELETE `/documents/doc_public_01` | RBAC | HTTP 403 Forbidden (Admin only) | HTTP 403 Forbidden | **PASS** |
| B4 | Admin DELETE `/documents/doc_public_01` | RBAC | HTTP 204 No Content (Soft delete) | HTTP 204 No Content | **PASS** |
| B5 | GET `/documents` list after soft delete | RBAC | Soft deleted document hidden | Omitted from list | **PASS** |
| C1 | PATCH approved version metadata | Lifecycle | HTTP 409 Conflict | HTTP 409 Conflict | **PASS** |
| C2 | POST approve on un-OCR'd draft version | Lifecycle | HTTP 409 Conflict | HTTP 409 Conflict | **PASS** |
| D1 | POST cancel on `SUCCEEDED` job | Job Mgmt | HTTP 409 Conflict | HTTP 409 Conflict | **PASS** |
| D2 | Student GET `/jobs/{staff_job_id}` | Job Mgmt | HTTP 403 Forbidden | HTTP 403 Forbidden | **PASS** |
| D3 | GET non-existent document ID | Robustness | HTTP 404 Not Found | HTTP 404 Not Found | **PASS** |

---

## Unchallenged Areas

- **Live MinIO / S3 Network Storage**: Tests used `LocalStorageService` mock; live MinIO S3 cluster connection was not tested in this offline local run.
- **Live Redis / Celery Worker Queue**: Celery tasks were tested in eager/direct mode rather than live Redis broker daemon.
