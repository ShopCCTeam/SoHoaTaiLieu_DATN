## 2026-08-11T06:20:29Z
You are Worker Phase B (Coverage Boost) for the SoHoaTaiLieu_DATN project.

Your working directory is: E:\SoHoaTaiLieu_DATN\.agents\worker_phase_b_cov

Objective:
Add comprehensive unit tests in `apps/api/tests/test_coverage_boost.py` targeting unreached code branches in `app/modules/documents/`, `app/modules/jobs/`, and `app/services/storage.py`, to raise the global pytest coverage above 85% (exceeding the >= 80% quality gate).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Inspect coverage report output (`uv run pytest --cov=app --cov-report=term-missing`).
2. Identify missing line coverage in:
   - `app/modules/documents/service.py`
   - `app/modules/documents/router.py`
   - `app/modules/jobs/router.py`
   - `app/services/storage.py`
3. Write `apps/api/tests/test_coverage_boost.py` testing edge cases:
   - Soft-deleted document lookups with `include_deleted=True` and `False`.
   - Update document metadata with invalid / missing fields.
   - Version approval errors (e.g., OCR failed or pending review blocks).
   - Cancel job endpoint for existing vs non-existent jobs.
   - LocalStorageService methods (upload, delete, download, get_presigned_url).
   - Storage errors / MinioStorageService exception fallbacks.
   - Security PDF validation edge cases (e.g. empty file, truncated header).
4. Run verification commands in `apps/api`:
   - `uv run pytest --cov=app --cov-report=term-missing` (MUST pass 100% with global coverage >= 82%).
   - `uv run ruff check app tests`
   - `uv run ruff format --check app tests`
   - `uv run mypy app`

Output Requirements:
- Write implementation log to `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_b_cov\changes.md`.
- Write handoff report to `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_b_cov\handoff.md`.
- Send message to parent (conversation ID: 9f83b9ff-33a4-4ee5-a9e2-f52e7b90ad52) when finished.
