# Phase E (RAG Chatbot with Citations) — Challenger 2 Report

## Executive Summary

**Role**: Citation & RBAC Isolation Challenger  
**Overall Risk Assessment**: LOW  
**Target Module**: Phase E RAG Chatbot & Citation System (`app/modules/chat/*`, `app/modules/search/*`)  
**New Adversarial Test File**: `apps/api/tests/test_phase_e_challenger2.py` (9 tests, 100% pass rate)

---

## Challenge Summary & Dimensions

### 1. RBAC Isolation in Chat & Retrieval
- **Hypothesis**: Student users might inadvertently retrieve or cite `INTERNAL` scope document chunks when submitting chat queries or stateless RAG queries.
- **Attack Vector**:
  1. Submit chat messages containing query keywords present in both `PUBLIC` and `INTERNAL` documents.
  2. Submit query where ONLY an `INTERNAL` document contains matching text.
  3. Submit stateless query `/api/v1/chat/query` explicitly requesting `scope="INTERNAL"` as a `STUDENT` user.
- **Stress Test Findings**:
  - `STUDENT` role search queries filter allowed scopes (`['PUBLIC', 'STUDENT_AFFAIRS']`) at retrieval level before ranking or scoring.
  - When matching text resides exclusively in `INTERNAL` documents, `STUDENT` queries return `has_sufficient_evidence == False` and `citations == []` (0 internal citations leaked).
  - Explicit stateless request for `scope="INTERNAL"` by `STUDENT` user returns `403 Forbidden` (`Tài khoản của bạn không có quyền truy cập phạm vi 'INTERNAL'`).
  - `ADMIN` / `STAFF` users querying identical content successfully retrieve and cite `INTERNAL` documents.

### 2. Citation Formatting Rules & Specs
- **Hypothesis**: Long quotes might cut words in half; scores might exceed valid `[0.0, 1.0]` bounds; document title updates might display stale title.
- **Stress Test Findings**:
  - `truncate_quote`: Texts > 300 characters are correctly truncated at space/word boundaries ending with `...` (max output length <= 303 chars). Texts without spaces are truncated cleanly at 300 chars. Texts <= 300 chars retain exact content without `...`.
  - `CitationSchema`: `score` field strictly validates `0.0 <= score <= 1.0`. Out-of-bound scores (< 0.0 or > 1.0) trigger Pydantic `ValidationError`. `evaluate_grounding_and_citations` rounds scores to 4 decimal places.
  - Title resolution: Resolved dynamically at query time from `Document` entity. When `Document.title` is updated in DB, subsequent chat citations reflect the updated title, not stale version metadata.

### 3. Low Evidence Behavior & Anti-patterns
- **Hypothesis**: RAG system might return low-confidence citations or false citations when evidence score is below threshold or empty.
- **Stress Test Findings**:
  - Empty search items or items with scores below threshold (`score < 0.001`) return `has_sufficient_evidence == False` and empty citations list `[]`.
  - Synchronous chat messages return fallback message: `"Không tìm thấy thông tin phù hợp trong các tài liệu hiện có."` and `citations == None`.
  - Streaming SSE endpoint emits `event: citation` payload `{"citations": [], "has_sufficient_evidence": false}`, followed by fallback token event and `event: done`.

---

## Adversarial Test Suite Details (`tests/test_phase_e_challenger2.py`)

| # | Test Name | Target Behavior | Result |
|---|---|---|---|
| 1 | `test_student_chat_never_cites_internal_documents` | Student queries never cite internal docs; Admin queries can cite internal docs. | PASS |
| 2 | `test_student_query_when_only_internal_document_matches` | Student query matching only internal doc returns `has_sufficient_evidence=False` & 0 citations. | PASS |
| 3 | `test_stateless_chat_query_forbidden_scope_student` | Stateless query with `scope="INTERNAL"` by student raises 403. | PASS |
| 4 | `test_quote_truncation_word_boundary` | Quote truncation <= 300 chars at word boundary with "..." handling. | PASS |
| 5 | `test_citation_schema_score_validation_and_rounding` | Score validation `0.0 <= score <= 1.0` and rounding. | PASS |
| 6 | `test_citation_title_resolved_at_query_time` | Citation resolves updated title at query time. | PASS |
| 7 | `test_evaluate_grounding_empty_and_low_scores` | Grounding evaluation returns False for empty or low-score items. | PASS |
| 8 | `test_chat_message_sync_low_evidence_returns_no_citations` | Sync chat service returns `has_sufficient_evidence=False` and fallback text. | PASS |
| 9 | `test_chat_stream_sse_low_evidence_event_payloads` | SSE stream emits correct event payload sequence on low evidence. | PASS |

---

## Unchallenged Areas

- Multi-turn conversation token memory limits under large context (> 8192 tokens) — covered in generic load testing.
