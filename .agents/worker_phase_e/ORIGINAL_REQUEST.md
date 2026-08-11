## 2026-08-11T09:05:26Z
Implement Phase E (RAG Chatbot with Citations) in `apps/api`:

1. LLM Provider Adapter Pattern:
   - `app/services/llm/base.py` (`AbstractLLMProvider`)
   - `app/services/llm/ollama.py` (`OllamaLLMProvider`)
   - `app/services/llm/mock.py` (`MockLLMProvider`)
   - `app/services/llm/factory.py` (`get_llm_provider()`)
2. Configuration Settings in `app/core/config.py`.
3. DB Models & Migration: `ChatSession`, `ChatMessage`, migration script `alembic/versions/0006_chat_sessions_and_messages.py`.
4. Chat Module `app/modules/chat/`: `schemas.py`, `service.py`, `router.py`. Register router in `app/main.py`.
5. Tests in `tests/test_llm_provider.py`, `tests/test_chat_models.py`, `tests/test_chat_router.py`. pytest, ruff, mypy verification.
6. Documentation & Handoff in `.agents/worker_phase_e/`.
