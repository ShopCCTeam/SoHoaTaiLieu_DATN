# Implementation Log — Phase B Fix Iteration 1

## Overview of Changes

1. **Celery Eager Execution Event Loop Collision (`apps/api/app/worker/tasks.py`)**:
   - Updated `run_async(coro)` to check if an event loop is currently running in the current thread (`asyncio.get_running_loop()`).
   - If an event loop is running (such as when `process_document_task.delay()` runs in eager mode inside FastAPI async HTTP handlers during tests/dev), the coroutine is executed in a dedicated worker thread via `concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(lambda: asyncio.run(coro)).result()`.
   - If no event loop is running, `asyncio.run(coro)` is called directly.
   - Prevents `RuntimeError: Cannot run the event loop while another loop is running` during eager Celery execution in FastAPI endpoints.

2. **Post-Commit Task Dispatch Error Safety (`apps/api/app/modules/documents/service.py`)**:
   - Wrapped `process_document_task.delay()` invocations in `try...except Exception as exc:` blocks inside `create_document()`, `create_document_version()`, and `trigger_version_ocr()`.
   - Logs task submission failures gracefully without crashing HTTP requests or rolling back committed DB records.

3. **Soft Delete Service-Level Filtering (`apps/api/app/modules/documents/service.py`)**:
   - Updated `get_document_by_id(session, document_id, include_deleted=False)` to append `.where(Document.deleted_at.is_(None))` when `include_deleted` is `False`.
   - Ensures soft-deleted documents are hidden from standard service lookups while allowing explicit opt-in via `include_deleted=True` when required.

4. **Version Approval Lineage Tracking (`apps/api/app/modules/documents/service.py`)**:
   - Updated `approve_document_version()` to query previous `APPROVED` versions of the document.
   - Sets previous approved version status to `"SUPERSEDED"` and updates `superseded_by_version_id` to the newly approved version ID.
   - Sets the newly approved version's `supersedes_version_id` to the previously active approved version ID.
   - Updates document `latest_version` and status to `"APPROVED"`.

5. **Test Suite Alignment (`apps/api/tests/test_phase_b_challenger2.py`)**:
   - Updated empirical challenger tests to assert the fixed behavior (eager task execution success, soft delete filtering default, version lineage pointers).

## Verification Results

- **pytest**: 116 passed, 4 skipped (Postgres DB integration tests skipped without running DB server), 0 failed.
- **Coverage**: 91% total (exceeds >= 80% threshold).
- **ruff check**: Passed cleanly.
- **ruff format --check**: Passed cleanly (60 files formatted).
- **mypy**: Success (no issues found in 41 source files).
