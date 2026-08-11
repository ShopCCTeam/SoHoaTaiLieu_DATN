## 2026-08-11T06:14:39Z
You are Worker Phase B (Fix Iteration) for the SoHoaTaiLieu_DATN project.

Your working directory is: E:\SoHoaTaiLieu_DATN\.agents\worker_phase_b_fix1

Objective:
Fix the Celery eager task execution bug, service-level soft delete filtering, and version lineage update in `apps/api/`, so that all tests pass 100% cleanly.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Detailed Bug Breakdown & Fix Requirements:

1. **CRITICAL FIX — Celery Eager Execution Event Loop Collision in `app/worker/tasks.py`**:
   - Issue: When `task_always_eager = True` in test/dev mode, `process_document_task.delay()` runs synchronously inside the active FastAPI asyncio event loop thread. Calling `loop.run_until_complete(coro)` or `asyncio.run(coro)` in the same thread raises `RuntimeError: Cannot run the event loop while another loop is running`.
   - Fix in `run_async(coro)` inside `app/worker/tasks.py`:
     Check if an event loop is currently running in the current thread (`asyncio.get_event_loop()` / `asyncio._get_running_loop()`).
     If an event loop IS running in the current thread:
       Execute the coroutine in a separate worker thread using `concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(lambda: asyncio.run(coro)).result()`.
     If NO event loop is running in the current thread:
       Call `asyncio.run(coro)`.
     This cleanly prevents event loop collisions when Celery tasks run eagerly inside FastAPI async HTTP requests!

2. **HIGH FIX — Post-commit Task Dispatch Atomicity in `app/modules/documents/service.py`**:
   - Wrap `.delay()` task dispatch in try-except block so that task submission errors are logged gracefully or handled without breaking DB session state or crashing request.

3. **MEDIUM FIX — Soft Delete Filtering in `app/modules/documents/service.py`**:
   - Update `get_document_by_id()` in `app/modules/documents/service.py` to add `.where(Document.deleted_at.is_(None))` by default (or accept `include_deleted: bool = False`), ensuring internal service calls and background workers do not retrieve soft-deleted documents by mistake.

4. **MEDIUM FIX — Version Approval Lineage in `app/modules/documents/service.py`**:
   - In `approve_document_version()`: When a new version is approved, query all previous versions of the document with status `APPROVED`, set their status to `SUPERSEDED` (or `ARCHIVED`), and set `superseded_by_version_id` to the newly approved version ID. Also set `version.supersedes_version_id` to the previous approved version ID if applicable.

5. **Verification**:
   Run and pass all quality gates in `apps/api`:
   1. `uv run pytest` (MUST pass 100% with >= 80% coverage, including all upload tests, idempotency tests, version lifecycle tests, and challenger tests in `tests/test_phase_b_challenger2.py`).
   2. `uv run ruff check app tests`
   3. `uv run ruff format --check app tests`
   4. `uv run mypy app`

Output Requirements:
- Write implementation log to `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_b_fix1\changes.md`.
- Write handoff report to `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_b_fix1\handoff.md`.
- Send message to parent (conversation ID: 9f83b9ff-33a4-4ee5-a9e2-f52e7b90ad52) when finished.
