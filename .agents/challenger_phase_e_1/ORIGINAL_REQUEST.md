## 2026-08-11T16:10:24Z
You are Challenger 1 for Phase E (RAG Chatbot with Citations) in SoHoaTaiLieu_DATN.

Your working directory is: `E:\SoHoaTaiLieu_DATN\.agents\challenger_phase_e_1`
Identity: Archetype `teamwork_preview_challenger`, Role: Chat API & SSE Stress Challenger

Objective:
1. Write an adversarial stress test file `tests/test_phase_e_challenger1.py` in `apps/api`:
   - Test edge cases for chat sessions: empty titles, long titles, cascade delete of messages when session deleted, soft delete behavior.
   - Test SSE streaming endpoint `/chat/sessions/{id}/messages/stream`: stream response events structure, mock provider stream generation, error handling on invalid session ID.
   - Ensure all new test code is cleanly formatted (`uv run ruff format .`) and passes linter (`uv run ruff check .`).
2. Run full backend verification:
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy app`
3. Write your report in `E:\SoHoaTaiLieu_DATN\.agents\challenger_phase_e_1\challenge.md` and `handoff.md`. Send completion message.
