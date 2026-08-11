## 2026-08-11T09:10:24Z
You are Reviewer 2 for Phase E (RAG Chatbot with Citations) gate verification in SoHoaTaiLieu_DATN.

Your working directory is: `E:\SoHoaTaiLieu_DATN\.agents\reviewer_phase_e_2`
Identity: Archetype `teamwork_preview_reviewer`, Role: Security & Citation Spec Reviewer

Objective:
1. Inspect Phase E implementation for security and spec compliance:
   - Citation tracking compliance with `docs/domain/citation-spec.md` (document_id, document_version_id, title, page_number, chunk_id, quote <= 300 chars, score round(2), bbox).
   - RBAC scope isolation: verify Chat RAG search passes `allowed_scopes` derived from user role.
   - SSE streaming format (`event: citation`, `event: token`, `event: done`, `event: error`).
2. Run backend verification commands:
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy app`
3. Write your review report in `E:\SoHoaTaiLieu_DATN\.agents\reviewer_phase_e_2\review.md` and `handoff.md`. Send completion message with your verdict (APPROVE / VETO).
