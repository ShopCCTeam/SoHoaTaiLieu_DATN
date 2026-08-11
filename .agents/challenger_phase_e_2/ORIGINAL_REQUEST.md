## 2026-08-11T09:10:24Z

<USER_REQUEST>
You are Challenger 2 for Phase E (RAG Chatbot with Citations) in SoHoaTaiLieu_DATN.

Your working directory is: `E:\SoHoaTaiLieu_DATN\.agents\challenger_phase_e_2`
Identity: Archetype `teamwork_preview_challenger`, Role: Citation & RBAC Isolation Challenger

Objective:
1. Write an adversarial test file `tests/test_phase_e_challenger2.py` in `apps/api`:
   - Test RBAC isolation in Chat: verify STUDENT user queries never retrieve or cite INTERNAL documents.
   - Test Citation formatting rules: quote truncation at word boundary <= 300 chars, score rounding to 2 decimal places, title resolution.
   - Test low evidence behavior: verify `has_sufficient_evidence == False` when retrieval returns scores below threshold or empty results.
   - Ensure all new test code is cleanly formatted (`uv run ruff format .`) and passes linter (`uv run ruff check .`).
2. Run full backend verification:
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy app`
3. Write your report in `E:\SoHoaTaiLieu_DATN\.agents\challenger_phase_e_2\challenge.md` and `handoff.md`. Send completion message.
</USER_REQUEST>
