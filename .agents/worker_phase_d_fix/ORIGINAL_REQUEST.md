## 2026-08-11T08:39:21Z

<USER_REQUEST>
You are Fix Worker Phase D for 'Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên' (SoHoaTaiLieu_DATN).
Your working directory is `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_d_fix`.

## Objectives
Remediate Phase D (RAG Vector Search Engine) audit failures in `apps/api/`:
1. Fix Linter & Formatting Errors in Challenger Test Files:
   - Inspect and clean `tests/test_phase_d_challenger1.py` and `tests/test_phase_d_challenger2.py`.
   - Remove unused imports (e.g. `F401`).
   - Fix all line-length violations (`E501`).
   - Run `uv run ruff format app tests`.
   - Run `uv run ruff check --fix app tests`.
2. BBox Calculation Edge Case Handling:
   - Inspect `compute_envelope_bbox` in `app/services/chunking.py`.
   - Ensure it gracefully handles empty block/bbox lists or bboxes with missing coordinates without throwing unhandled exceptions.
3. Verification & Quality Gate Checks:
   - Run `uv run pytest --cov=app --cov-report=term-missing` (verify ALL tests pass, 0 failures, coverage >= 80%).
   - Run `uv run ruff check app tests` (must be 100% CLEAN with 0 errors).
   - Run `uv run ruff format --check app tests` (must be 100% CLEAN).
   - Run `uv run mypy app` (must be 100% CLEAN with 0 errors).

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Report all results, test commands, coverage percentages, and file paths in `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_d_fix\handoff.md` and send a message back to parent.

</USER_REQUEST>
