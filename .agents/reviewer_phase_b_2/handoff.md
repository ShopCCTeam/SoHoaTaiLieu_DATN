# Handoff Report — Reviewer Phase B 2

## 1. Observation

- **Command Execution & Static Analysis**:
  - `uv run pytest` executed in `apps/api`:
    - Result: `FAILED tests/test_config.py::test_default_settings_for_dev`, `FAILED tests/test_documents_upload.py::test_upload_valid_pdf_returns_202_accepted`, `FAILED tests/test_documents_upload.py::test_idempotency_replay`, `FAILED tests/test_documents_versions.py::test_document_versions_lifecycle`
    - Summary: `4 failed, 108 passed, 4 skipped in 44.09s`
    - Verbatim exception traceback from test output:
      `RuntimeError: Cannot run the event loop while another loop is running`
      at `apps/api/app/worker/tasks.py:25` (`loop.run_until_complete(coro)`).
  - `uv run ruff check app tests`: `All checks passed!` (0 errors)
  - `uv run ruff format --check app tests`: `59 files already formatted`
  - `uv run mypy app`: `Success: no issues found in 41 source files`

- **Code Inspection Observations**:
  - `app/worker/tasks.py` lines 20-27:
    ```python
    def run_async(coro: Any) -> Any:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    ```
  - `app/modules/documents/service.py` lines 160-163, 288-290, 345-347:
    ```python
    await session.commit()
    process_document_task.delay(job_id, version_id)
    ```
  - `app/modules/documents/service.py` lines 67-73:
    ```python
    async def get_document_by_id(session: AsyncSession, document_id: str) -> Document | None:
        stmt = (
            select(Document).options(selectinload(Document.versions)).where(Document.id == document_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    ```
  - `app/modules/documents/security.py` lines 32, 57:
    ```python
    if content_type and content_type.lower() != ALLOWED_MIME_TYPE:
    ```

---

## 2. Logic Chain

1. **Observation**: `uv run pytest` returns exit code 1 with 4 test failures.
2. **Observation**: Traceback shows `RuntimeError: Cannot run the event loop while another loop is running` inside `app/worker/tasks.py:25` during `process_document_task.delay()` invocation.
3. **Reasoning**: When Celery runs in eager mode (`CELERY_TASK_ALWAYS_EAGER=true`), calling `.delay()` triggers synchronous execution inside the FastAPI request handler's running asyncio event loop. Calling `asyncio.new_event_loop()` + `loop.run_until_complete()` inside an already running event loop is rejected by Python asyncio.
4. **Observation**: `service.create_document` executes `await session.commit()` BEFORE calling `process_document_task.delay(...)`.
5. **Reasoning**: If `.delay(...)` fails (due to eager event loop error or Celery Redis broker connection failure), the HTTP request crashes with HTTP 500, but `Document` and `Job` records are committed to DB and remain orphaned in `QUEUED` state.
6. **Observation**: `service.get_document_by_id` queries `Document` without `Document.deleted_at.is_(None)`.
7. **Reasoning**: Endpoints calling `get_document_by_id` (`GET /documents/{id}`, `/versions`, etc.) expose soft-deleted documents, violating soft-deletion access control isolation.
8. **Conclusion**: The Phase B implementation fails test suite execution and contains critical architectural defects. The appropriate verdict is **VETO**.

---

## 3. Caveats

- Tests requiring live PostgreSQL service (`test_models_pg.py` and `test_alembic.py` Postgres migrations) were skipped during local execution due to absent local Docker Postgres container; however, SQLite in-memory integration test fixtures were executed.
- MinIO S3 integration was verified via mock storage backend service abstraction.

---

## 4. Conclusion

**Verdict: VETO**

Phase B cannot be approved until:
1. `uv run pytest` passes 100% cleanly without errors.
2. `app/worker/tasks.py` event loop handling is fixed to support eager test execution within running asyncio event loops.
3. Task dispatch in `app/modules/documents/service.py` is made resilient against Celery broker errors.
4. `get_document_by_id` filters soft-deleted documents (`deleted_at.is_(None)`).
5. Idempotency request payload signature verification is implemented.

---

## 5. Verification Method

To independently verify these findings:
1. Run `uv run pytest` in `apps/api/` — verify that 4 tests fail with exit code 1.
2. Run `uv run ruff check app tests` and `uv run mypy app` — verify static checkers pass.
3. Inspect `apps/api/app/worker/tasks.py` lines 20-27 — verify `loop.run_until_complete()` inside active event loop.
4. Inspect `apps/api/app/modules/documents/service.py` lines 67-73 — verify `get_document_by_id` lacks `deleted_at.is_(None)` filter.
