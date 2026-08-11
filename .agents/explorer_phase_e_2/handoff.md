# Handoff Report — Phase E: RAG Chatbot with Citations (Explorer 2)

**Working Directory**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_2`  
**Role**: RAG Chatbot Specialist  
**Target Milestone**: Phase E — RAG Chatbot with Citations  
**Date**: 2026-08-11  

---

## 1. Observation

Direct observations from codebase inspection:

1. **Settings Config (`app/core/config.py:81-83`)**:
   ```python
   # ---- Embedding & RAG ----
   embedding_provider: Literal["bge-m3", "mock"] = "mock"
   embedding_api_url: str = "http://localhost:11434/api/embeddings"
   embedding_model_name: str = "bge-m3"
   ```
   *Observation*: Setting layer contains embedding config but does NOT yet contain LLM model/provider configuration parameters (`llm_provider`, `llm_ollama_base_url`, `llm_ollama_model_name`, `llm_temperature`, `llm_max_tokens`).

2. **Hybrid Search Service (`app/modules/search/service.py:29-39`)**:
   ```python
   async def search_documents(
       session: AsyncSession,
       query: str,
       allowed_scopes: list[str],
       requested_scope: str | None = None,
       doc_type: str | None = None,
       alpha: float = 0.5,
       top_k: int = 10,
       page: int = 1,
       size: int = 10,
   ) -> SearchResponse:
   ```
   *Observation*: `search_documents()` is fully implemented with RRF hybrid search (vector + full-text) and scope filtering (`allowed_scopes`). Returns `SearchResultItem` containing `chunk_id`, `document_id`, `version_id`, `document_title`, `page_number`, `text`, `bbox`, `score`.

3. **Citation Specification (`docs/domain/citation-spec.md:9-18`)**:
   ```typescript
   interface Citation {
     document_id: string;              // UUID
     document_version_id: string;      // UUID
     title: string;                    // Tiêu đề tài liệu (đã resolve, không phải ID)
     page_number: number;              // 1-based
     chunk_id: string;                 // UUID của chunk embedding
     quote: string;                    // Trích nguyên văn đoạn text được cite
     score: number;                    // 0..1, similarity score
     bbox?: [number, number, number, number]; // Optional: [x_min, y_min, x_max, y_max] trong PDF coordinate
   }
   ```
   *Observation*: Standard citation format is specified with 6 mandatory rules (resolve title at query time, 1-based PDF page, max 300 char quote, normalized score, bbox when available, scope-filtered).

4. **Frontend Mock Contract (`apps/web/app/api/chat/query/route.ts:27-52`)**:
   ```json
   {
     "success": true,
     "data": {
       "answer": "...",
       "citations": [...],
       "has_sufficient_evidence": true
     }
   }
   ```
   *Observation*: Frontend expects snake_case response containing `answer`, `citations`, and `has_sufficient_evidence`.

5. **Alembic Migrations (`apps/api/alembic/versions/`)**:
   - `0001_users_and_scopes.py`
   - `0002_refresh_sessions.py`
   - `0003_documents_versions_and_jobs.py`
   - `0004_ocr_pages_and_blocks.py`
   - `0005_document_chunks_pgvector.py`
   *Observation*: There are currently 5 migration scripts. `0006_chat_sessions_and_messages.py` needs to be created for Phase E.

---

## 2. Logic Chain

1. **From Observation 1**: Current settings lack LLM configuration parameters.
   *Reasoning*: To support swapping between local Ollama and mock LLMs without modifying source code, we must introduce `llm_provider`, `llm_ollama_base_url`, `llm_ollama_model_name`, `llm_temperature`, `llm_max_tokens` into `Settings` (`app/core/config.py`).
2. **From Observation 1 & SOLID principles**:
   *Reasoning*: Using an Abstract Base Class (`AbstractLLMProvider`) with `OllamaLLMProvider` and `MockLLMProvider` implementations allows decoupling business logic from external LLM services, enabling fast, isolated unit testing without requiring an active Ollama daemon.
3. **From Observation 2 & 3**: `search_documents()` returns all fields needed for `Citation`.
   *Reasoning*: The search service can be directly consumed by the RAG Chatbot Service to retrieve relevant context chunks filtered by user scopes (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`). The resulting search items map directly into `Citation` objects matching `docs/domain/citation-spec.md`.
4. **From Observation 4**: Frontend expects SSE streaming as well as synchronous query responses.
   *Reasoning*: FastAPI `StreamingResponse` emitting `event: token`, `event: citation`, `event: done`, `event: error` provides low-latency streaming to Next.js clients while maintaining compatibility with non-streaming clients via JSON endpoints.
5. **From Observation 5**: Chat history state needs persistence across client sessions.
   *Reasoning*: Creating `chat_sessions` and `chat_messages` tables via Alembic migration `0006_chat_sessions_and_messages.py` and ORM models (`ChatSession`, `ChatMessage`) will enable full CRUD API management (`/chat/sessions`, `/chat/sessions/{id}/messages`).

---

## 3. Caveats

1. **Ollama Availability in Dev/CI**: In local development or automated CI environments where Ollama is not installed or running, system must fall back seamlessly to `MockLLMProvider` (`llm_provider="mock"`).
2. **SQLite Test Compatibility**: SQLite does not support native `pgvector` or `tsvector`. However, `search_documents` already has SQLite fallback calculation, which ensures unit tests for chat service will run smoothly on SQLite in-memory during `pytest`.
3. **Token Usage Estimation**: Token counts for prompt and completion in `ChatMessage.tokens_used` are estimates based on word count/tiktoken, as local Ollama streaming chunks may not provide final token counters on every chunk.

---

## 4. Conclusion

Phase E RAG Chatbot architecture is fully designed, modular, and ready for implementation. The proposed strategy:
1. Enhances `app/core/config.py` with LLM settings.
2. Implements `AbstractLLMProvider` in `app/services/llm/` (`ollama.py`, `mock.py`, `factory.py`).
3. Defines DB models `ChatSession` and `ChatMessage` in `app/models/` and Alembic migration `0006_chat_sessions_and_messages.py`.
4. Implements `app/modules/chat/` (`schemas.py`, `service.py`, `dependencies.py`, `router.py`) supporting SSE streaming and citation tracking according to `docs/domain/citation-spec.md`.
5. Connects `router` to `app/main.py`.

A comprehensive architectural document has been produced at `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_2\analysis.md`.

---

## 5. Verification Method

To independently verify the implementation when built:

1. **Unit & Integration Tests**:
   ```bash
   cd apps/api
   uv run pytest tests/test_llm_provider.py tests/test_chat_models.py tests/test_chat_router.py -v
   ```
2. **Static Quality Check**:
   ```bash
   cd apps/api
   uv run ruff check app tests
   uv run mypy app
   ```
3. **OpenAPI Schema Check**:
   ```bash
   cd E:\SoHoaTaiLieu_DATN
   pnpm check
   ```
4. **SSE Stream Verification**:
   ```bash
   curl -N -X POST "http://localhost:8000/api/v1/chat/sessions/{session_id}/messages/stream" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"prompt": "Quy định đánh giá rèn luyện thế nào?"}'
   ```
   *Expected Output*: SSE sequence of `event: citation`, `event: token`, and `event: done`.
