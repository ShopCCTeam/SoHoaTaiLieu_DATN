# Summary of Changes — Phase E (RAG Chatbot with Citations)

## Files Created / Modified

### 1. LLM Provider Adapter Pattern
- `apps/api/app/services/llm/base.py`: Created `AbstractLLMProvider` interface (`generate`, `stream_generate`).
- `apps/api/app/services/llm/ollama.py`: Created `OllamaLLMProvider` using `httpx.AsyncClient` targeting local Ollama `/api/chat` (supports sync generation and streaming response).
- `apps/api/app/services/llm/mock.py`: Created `MockLLMProvider` for deterministic testing and CI environment without requiring external model servers.
- `apps/api/app/services/llm/factory.py`: Created `get_llm_provider()` factory method configured via app settings.
- `apps/api/app/services/llm/__init__.py`: Package re-exports for LLM services.

### 2. Configuration Settings
- `apps/api/app/core/config.py`: Added LLM settings: `llm_provider`, `llm_ollama_base_url`, `llm_ollama_model_name`, `llm_temperature`, `llm_max_tokens`, `llm_timeout_seconds`.

### 3. Database Models & Alembic Migration
- `apps/api/app/models/chat_session.py`: `ChatSession` ORM model linked to `User`.
- `apps/api/app/models/chat_message.py`: `ChatMessage` ORM model with JSON `citations`, `has_sufficient_evidence`, `tokens_used`.
- `apps/api/app/models/__init__.py`: Re-exported `ChatSession` and `ChatMessage`.
- `apps/api/alembic/versions/0006_chat_sessions_and_messages.py`: Migration script for `chat_sessions` and `chat_messages` tables.

### 4. Chat Module & Endpoints
- `apps/api/app/modules/chat/schemas.py`: Pydantic schemas for `CitationSchema` (matching `docs/domain/citation-spec.md`), session management, message payloads, SSE streaming, and stateless queries.
- `apps/api/app/modules/chat/service.py`: RAG service combining search retrieval, grounding evidence evaluation, prompt building, citation metadata creation, sync completion, and SSE token streaming.
- `apps/api/app/modules/chat/router.py`: FastAPI router implementing:
  - `POST /api/v1/chat/sessions`
  - `GET /api/v1/chat/sessions`
  - `GET /api/v1/chat/sessions/{id}`
  - `DELETE /api/v1/chat/sessions/{id}`
  - `GET /api/v1/chat/sessions/{id}/messages`
  - `POST /api/v1/chat/sessions/{id}/messages`
  - `POST /api/v1/chat/sessions/{id}/messages/stream` (SSE: `event: citation`, `event: token`, `event: done`, `event: error`)
  - `POST /api/v1/chat/query`
- `apps/api/app/main.py`: Registered `chat_router` under `api_prefix`.

### 5. Unit & Integration Tests
- `apps/api/tests/test_llm_provider.py`: Unit tests for `MockLLMProvider`, `OllamaLLMProvider`, and `get_llm_provider()`.
- `apps/api/tests/test_chat_models.py`: Model unit tests for `ChatSession` and `ChatMessage` CRUD & cascade deletes.
- `apps/api/tests/test_chat_router.py`: Endpoint tests covering session CRUD, RBAC ownership checks, sync messaging, SSE streaming, stateless queries, and groundings.
- `apps/api/tests/test_alembic.py`: Updated revision chain tests for 0006.

## Quality Assurance Verification
- `uv run pytest`: 201 passed, 24 skipped (0 failures).
- `uv run ruff check .`: Clean (0 errors).
- `uv run ruff format --check .`: Clean (0 files to reformat).
- `uv run mypy app`: Clean (0 errors in 62 source files).
