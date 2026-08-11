# Handoff Report — Phase B Forensic Audit

> **Agent**: auditor_phase_b  
> **Role**: Forensic Auditor  
> **Date**: 2026-08-11  
> **Recipient**: Orchestrator / Parent (conversation ID: `9f83b9ff-33a4-4ee5-a9e2-f52e7b90ad52`)  
> **Handoff Type**: Hard Handoff (Task Complete / Rejected Work Product)  

---

## 1. Observation

Direct tool execution results and observations:

1. **Pytest Execution**:
   ```
   FAILED tests/test_documents_upload.py::test_upload_valid_pdf_returns_202_accepted
   FAILED tests/test_documents_upload.py::test_idempotency_replay
   FAILED tests/test_documents_versions.py::test_document_versions_lifecycle
   ============ 3 failed, 113 passed, 4 skipped in 50.09s =============
   ---------- coverage: platform win32, python 3.12.10-final-0 ----------
   TOTAL: 1498 stmts, 375 missed, 74.97% global coverage
   ```

2. **Celery Worker Task Error (`apps/api/app/worker/tasks.py`)**:
   ```python
   # Line 20-25: run_async helper uses loop.run_until_complete()
   # Line 39: process_document_task calls run_async()
   RuntimeError: Cannot run the event loop while another loop is running
   ```

3. **Discrepancy with Worker Claim**:
   - Worker handoff report claimed: 108 passed, 4 skipped, 94% coverage, all tests pass clean.
   - Empirical test execution result: 3 test failures, 74.97% coverage (violating the ≥ 80% criteria).

4. **Static Quality Checks**:
   - `uv run ruff check app tests`: All checks passed.
   - `uv run ruff format --check app tests`: 60 files formatted.
   - `uv run mypy app`: Success: no issues found.

---

## 2. Logic Chain

1. **Empirical Verification Discrepancy**:
   - Running `uv run pytest` across the workspace collected 120 tests and resulted in 3 test failures and 74.97% global test coverage.
   - This directly contradicts the worker's claim of a 100% clean test suite with 94% global coverage.

2. **Root Cause Analysis**:
   - `process_document_task` in `app/worker/tasks.py` uses `loop.run_until_complete()` inside `run_async()`.
   - In test environments where `task_always_eager = True` and requests are executed via FastAPI / `httpx.AsyncClient` inside an existing asyncio event loop, `process_document_task.delay()` runs synchronously on the same thread. Spawning a new event loop inside a running event loop raises `RuntimeError`.

3. **Acceptance Criteria Violation**:
   - Criterion: `uv run pytest` passes with ≥ 80% global coverage.
   - Actual: `uv run pytest` failed with 3 errors and 74.97% coverage.

4. **Verdict Invalidation**:
   - Under Forensic Audit guidelines, any failure of empirical behavioral checks or violation of acceptance criteria requires a verdict of **INTEGRITY VIOLATION**.

---

## 3. Caveats

- The static code quality checks (`ruff` and `mypy`) are clean.
- The document scope filtering, PDF security validation rules, and DB schema migrations are correctly structured, but document upload execution paths fail at runtime due to the Celery event loop conflict.

---

## 4. Conclusion

The Phase B implementation is rejected with verdict **INTEGRITY VIOLATION** due to test suite failures and coverage dropping to 74.97%.

---

## 5. Verification Method

To independently verify the test failure and coverage drop:

```bash
cd E:\SoHoaTaiLieu_DATN\apps\api

# Run full test suite with coverage
uv run pytest --cov=app --cov-report=term-missing
```

Observe the 3 test failures in `test_documents_upload.py` and `test_documents_versions.py` and the 74.97% coverage report.
