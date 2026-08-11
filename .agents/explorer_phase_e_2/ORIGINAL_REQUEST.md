## 2026-08-11T09:03:31Z
You are Explorer 2 for Phase E (RAG Chatbot with Citations) in SoHoaTaiLieu_DATN.

Your working directory is: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_2`
Identity: Archetype `teamwork_preview_explorer`, Role: RAG Chatbot Specialist

Objective:
1. Deep-dive into RAG Chatbot requirements (Phase E):
   - Ollama local LLM integration with Provider Adapter Pattern (e.g. `OllamaLLMProvider` implementing an `AbstractLLMProvider` interface to allow swapping models/providers like Qwen2.5/Llama-3.1/mock/Ollama).
   - LangChain pipeline: user query -> retrieve top-k chunks from search module (`app/modules/search/service.py`) with metadata -> format prompt -> generate response.
   - Streaming SSE responses: FastAPI `StreamingResponse(..., media_type="text/event-stream")` emitting formatted events: `event: token`, `event: citation`, `event: done`, `event: error`.
   - Citation tracking: extract document title/id, page number, bounding box coordinates (`bbox`) from retrieved vector chunks and include them in response metadata/citations.
   - Conversation history: database models (`ChatSession`, `ChatMessage`), Alembic migration, CRUD APIs (`POST /chat/sessions`, `GET /chat/sessions`, `GET /chat/sessions/{id}/messages`, `POST /chat/completions` or `POST /chat/stream`).
2. Check existing DB models, migrations (`apps/api/alembic/versions`), search service integration.
3. Deliver a detailed design and implementation strategy report in `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_2\analysis.md` and `handoff.md`. Send a message back to parent when done.
