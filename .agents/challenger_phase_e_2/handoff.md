# Handoff Report — Phase E Challenger 2

## 1. Observation

- **New Test File**: `apps/api/tests/test_phase_e_challenger2.py`
  - Created 9 comprehensive adversarial tests covering RBAC isolation, citation formatting (word boundary truncation, score bounds, title resolution), and low evidence fallback behavior.
- **Verification Commands Executed**:
  - `uv run pytest tests/test_phase_e_challenger2.py`: Passed 9/9 tests in 5.65s.
  - `uv run ruff check .`: Passed cleanly with zero lint errors (`All checks passed!`).
  - `uv run ruff format --check .`: Passed with 97 files formatted.
  - `uv run mypy app`: Passed cleanly with zero type errors (`Success: no issues found in 62 source files`).
- **Target Source Code Inspected**:
  - `apps/api/app/modules/chat/service.py`: `truncate_quote`, `evaluate_grounding_and_citations`, `process_send_message`, `process_send_message_stream`, `process_stateless_query`.
  - `apps/api/app/modules/chat/schemas.py`: `CitationSchema`, `ChatMessageResponse`, `ChatQueryResponse`.
  - `apps/api/app/modules/documents/dependencies.py`: `get_allowed_scopes_for_user`.
  - `apps/api/app/modules/search/service.py`: `search_documents`.

## 2. Logic Chain

1. **RBAC Scope Isolation in Chat**:
   - `get_allowed_scopes_for_user(user)` restricts `STUDENT` role to `['PUBLIC', 'STUDENT_AFFAIRS']`.
   - `search_documents` enforces `Document.scope.in_(allowed_scopes)` at SQL/OR level, preventing `INTERNAL` chunks from entering retrieval results for students.
   - When a student asks about content existing ONLY in an internal document, retrieval yields 0 items, triggering `evaluate_grounding_and_citations` to return `(False, [])`.
   - Result: Students cannot access or cite internal document content via chat or stateless query. Requesting `scope="INTERNAL"` via stateless query explicitly raises HTTP 403 Forbidden.

2. **Citation Formatting**:
   - `truncate_quote` trims text and truncates at max 300 characters at the last space boundary, appending `...`. Single long words without spaces are truncated at 300 characters + `...`. Texts <= 300 chars remain unchanged without `...`.
   - `CitationSchema` enforces `0.0 <= score <= 1.0` via Pydantic model validation. Scores are rounded to 4 decimals in BE evaluation.
   - Title resolution queries current `Document.title` entity at runtime, ensuring title updates are immediately reflected in citations.

3. **Low Evidence Handling**:
   - When search results are empty or have scores below `score_threshold` (0.001), `evaluate_grounding_and_citations` returns `(False, [])`.
   - Both synchronous and SSE streaming chat service paths emit `has_sufficient_evidence = False`, return empty citations, and present fallback text: `"Không tìm thấy thông tin phù hợp trong các tài liệu hiện có."`

## 3. Caveats

- SQLite in-memory engine is used for pytest execution. Hybrid search relies on Python cosine similarity fallback on SQLite. Postgres pgvector integration tests require running Postgres stack via Docker.
- No caveats regarding test validity or coverage of Phase E requirements.

## 4. Conclusion

- Phase E RAG Chatbot with Citations implementation fully complies with `docs/domain/citation-spec.md` and RBAC security requirements.
- RBAC scope isolation is strictly enforced prior to citation generation.
- Quote truncation, score validation, title resolution, and low evidence handling behave correctly under adversarial inputs.

## 5. Verification Method

To independently verify these results, run the following commands in `apps/api`:

```bash
cd apps/api
uv run pytest tests/test_phase_e_challenger2.py
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```
