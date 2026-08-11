# Handoff Report — Phase B Fix Iteration 1

## 1. Observation

- **Celery Event Loop Collision**: In `apps/api/app/worker/tasks.py`, `run_async(coro)` previously created a new event loop and called `loop.run_until_complete(coro)`. When running Celery eager tasks (`task_always_eager = True`) inside FastAPI async request handlers, this threw `RuntimeError: Cannot run the event loop while another loop is running`.
- **Task Dispatch Atomicity**: In `apps/api/app/modules/documents/service.py`, `process_document_task.delay()` calls were executed after `await session.commit()` without error handling. Unhandled task submission exceptions would crash the request after the database transaction committed.
- **Soft Delete Isolation**: `get_document_by_id()` in `apps/api/app/modules/documents/service.py` retrieved documents without checking `deleted_at`, allowing soft-deleted records to be retrieved by default.
- **Version Approval Lineage**: `approve_document_version()` in `apps/api/app/modules/documents/service.py` set the version status to `APPROVED` without marking previously approved versions as `SUPERSEDED` or setting `supersedes_version_id` / `superseded_by_version_id`.
- **Content-Type Validation**: `validate_pdf_bytes` and `validate_upload_file` in `apps/api/app/modules/documents/security.py` checked `content_type != "application/pdf"`, failing for Content-Type headers containing parameters like `application/pdf; name=doc.pdf`.
- **Idempotency Payload Replay**: In `apps/api/app/modules/documents/service.py`, replaying an `Idempotency-Key` returned the existing document/job status without checking whether the payload attributes (checksum or title) matched the original request.
- **Verification Outputs**:
  - `uv run pytest --cov=app`: `116 passed, 4 skipped in 17.58s` with **90% coverage** (exceeds >= 80% requirement).
  - `uv run ruff check app tests`: `All checks passed!`.
  - `uv run ruff format --check app tests`: `60 files already formatted`.
  - `uv run mypy app`: `Success: no issues found in 41 source files`.

## 2. Logic Chain

1. **Event Loop Collision Fix**:
   - `asyncio.get_running_loop()` detects if an asyncio event loop is currently active on the executing thread.
   - If an event loop is running (eager Celery mode inside FastAPI route), executing the coroutine via `concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(lambda: asyncio.run(coro)).result()` offloads event loop initialization to a separate worker thread, avoiding `RuntimeError` while waiting synchronously for the result.
   - If no event loop is running (standard background worker), `asyncio.run(coro)` executes directly.

2. **Dispatch Error Handling**:
   - Wrapping `.delay()` calls in `try...except Exception as exc:` and logging exceptions via `logger.exception()` prevents Celery queueing failures from crashing HTTP endpoints or causing request handler rollbacks post-commit.

3. **Soft Delete Filtering**:
   - Adding `include_deleted: bool = False` parameter and conditional `.where(Document.deleted_at.is_(None))` to `get_document_by_id()` ensures service functions exclude soft-deleted documents by default while preserving an explicit parameter for administrative access.

4. **Version Lineage Pointers**:
   - Querying all existing `APPROVED` versions for the document before approval allows setting `version.supersedes_version_id` to the previous approved version ID and setting previous approved versions' status to `"SUPERSEDED"` with `superseded_by_version_id` set to the new version ID.

5. **Content-Type & Idempotency Refinements**:
   - Changing `!= "application/pdf"` to `not content_type.startswith("application/pdf")` supports standard HTTP content type parameter suffixes.
   - Checking stored version checksum / document title on idempotency key replay ensures 409 `IDEMPOTENCY_KEY_MISMATCH` is raised if a matching key is reused with modified payload.

## 3. Caveats

- **Postgres DB Integration Tests**: 4 integration tests in `test_alembic.py` and `test_models_pg.py` were skipped because a local PostgreSQL database server was not running. These tests are configured to run automatically in CI environments with Postgres services enabled (`_skip_or_fail`).

## 4. Conclusion

All Celery eager execution bugs, service-level soft delete filtering gaps, version approval lineage pointers, Content-Type startswith validations, and idempotency payload mismatch checks in `apps/api/` have been fully resolved. All quality gates (pytest 100% pass, 90% coverage, ruff lint, ruff format, mypy static typing) pass cleanly.

## 5. Verification Method

To verify independently from `apps/api/`:

```bash
cd apps/api
uv run pytest --cov=app
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
```
