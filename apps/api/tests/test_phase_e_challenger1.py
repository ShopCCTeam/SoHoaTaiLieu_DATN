"""Adversarial stress tests for Phase E: Chat API & SSE Streaming.

Challenger 1 focus:
- Chat session edge cases: empty titles, long titles (boundary & overflow),
  cascade delete of messages, soft/hard delete verification, invalid ID operations.
- SSE streaming endpoint (/chat/sessions/{id}/messages/stream):
  exact SSE event structure, mock provider stream generation & DB persistence,
  error handling on invalid session ID, cross-user ownership violation in stream,
  and exceptions inside LLM provider stream.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.user import User
from app.modules.search.schemas import SearchResponse
from app.services.embedding import EmbeddingService
from app.services.llm import AbstractLLMProvider
from tests.conftest import auth_headers_for


@pytest.fixture
async def sample_doc_for_challenger(
    db_session_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> Document:
    """Seed a chunk whose deterministic test embedding clears the cosine guardrail."""

    async def _embed_query(_: EmbeddingService, __: str) -> list[float]:
        return [0.2] * 1024

    monkeypatch.setattr(EmbeddingService, "embed_query", _embed_query)

    async with db_session_factory() as session:
        doc = Document(
            id="doc_challenger_01",
            title="Quy định Công tác Sinh viên 2026",
            type="QUY_DINH",
            status="APPROVED",
            scope="PUBLIC",
            author_id="usr_admin_01",
        )
        version = DocumentVersion(
            id="ver_challenger_01",
            document_id=doc.id,
            version_number=1,
            file_url="http://localhost:9000/ctsv-documents/ctsv.pdf",
            file_size=2048,
            checksum="b" * 64,
            created_by="usr_admin_01",
        )
        chunk = DocumentChunk(
            id="chk_challenger_01",
            version_id=version.id,
            document_id=doc.id,
            chunk_index=0,
            page_number=1,
            block_ids=[],
            text="Sinh viên được quyền khiếu nại kết quả rèn luyện trong thời hạn 7 ngày làm việc.",
            token_count=20,
            bbox=[5.0, 10.0, 200.0, 40.0],
            embedding=[0.2] * 1024,
        )
        session.add_all([doc, version, chunk])
        await session.commit()
        await session.refresh(doc)
        return doc


class MockStreamingLLMProvider(AbstractLLMProvider):
    """Mock LLM Provider yielding custom streamed tokens."""

    def __init__(
        self,
        tokens: list[str] | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        self.tokens = tokens or ["Thời ", "hạn ", "khiếu ", "nại ", "là ", "7 ", "ngày."]
        self.raise_exc = raise_exc

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if self.raise_exc:
            raise self.raise_exc
        return "".join(self.tokens)

    async def stream_generate(self, prompt: str, system_prompt: str | None = None):
        if self.raise_exc:
            raise self.raise_exc
        for token in self.tokens:
            yield token


# ============================================================================
# Section 1: Chat Session Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_session_create_empty_or_whitespace_title(
    api_client: AsyncClient,
    student_user: User,
):
    """Test creating session with empty string, whitespace, or null title."""
    headers = auth_headers_for(student_user)

    # 1. Empty string -> fallback to "Hội thoại mới"
    res1 = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": ""},
        headers=headers,
    )
    assert res1.status_code == 201
    assert res1.json()["data"]["title"] == "Hội thoại mới"

    # 2. Whitespace string -> fallback to "Hội thoại mới"
    res2 = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "     "},
        headers=headers,
    )
    assert res2.status_code == 201
    assert res2.json()["data"]["title"] == "Hội thoại mới"

    # 3. None / missing title -> fallback to "Hội thoại mới"
    res3 = await api_client.post(
        "/api/v1/chat/sessions",
        json={},
        headers=headers,
    )
    assert res3.status_code == 201
    assert res3.json()["data"]["title"] == "Hội thoại mới"


@pytest.mark.asyncio
async def test_session_create_title_length_boundaries(
    api_client: AsyncClient,
    student_user: User,
):
    """Test title max_length boundaries: 255 chars succeeds, 256+ chars fails with 422."""
    headers = auth_headers_for(student_user)

    # 1. Boundary max allowed: 255 chars
    title_255 = "A" * 255
    res_ok = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": title_255},
        headers=headers,
    )
    assert res_ok.status_code == 201
    assert res_ok.json()["data"]["title"] == title_255

    # 2. Boundary overflow: 256 chars -> 422 Unprocessable Entity
    title_256 = "B" * 256
    res_overflow = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": title_256},
        headers=headers,
    )
    assert res_overflow.status_code == 422

    # 3. Extreme overflow: 1000 chars -> 422
    title_1000 = "C" * 1000
    res_huge = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": title_1000},
        headers=headers,
    )
    assert res_huge.status_code == 422


@pytest.mark.asyncio
async def test_session_cascade_delete_messages_db(
    api_client: AsyncClient,
    student_user: User,
    db_session_factory,
    sample_doc_for_challenger: Document,
):
    """Test session deletion cascades to remove all associated chat messages from DB."""
    headers = auth_headers_for(student_user)

    # Create session
    res_s = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Cascade Test"},
        headers=headers,
    )
    session_id = res_s.json()["data"]["id"]

    # Send 2 messages (sync)
    await api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Câu hỏi 1?"},
        headers=headers,
    )
    await api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Câu hỏi 2?"},
        headers=headers,
    )

    # Verify messages exist in DB directly
    async with db_session_factory() as session:
        stmt_before = select(ChatMessage).where(ChatMessage.session_id == session_id)
        res_before = await session.execute(stmt_before)
        msgs_before = list(res_before.scalars().all())
        assert len(msgs_before) >= 4  # 2 user + 2 assistant messages

    # Delete session via API
    res_del = await api_client.delete(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert res_del.status_code == 204

    # Verify session and messages are deleted from DB
    async with db_session_factory() as session:
        s_obj = await session.get(ChatSession, session_id)
        assert s_obj is None

        stmt_after = select(ChatMessage).where(ChatMessage.session_id == session_id)
        res_after = await session.execute(stmt_after)
        msgs_after = list(res_after.scalars().all())
        assert len(msgs_after) == 0


@pytest.mark.asyncio
async def test_session_delete_nonexistent_or_already_deleted(
    api_client: AsyncClient,
    student_user: User,
):
    """Test deleting non-existent ID or deleting same session twice yields 404."""
    headers = auth_headers_for(student_user)

    # 1. Non-existent session
    res_fake = await api_client.delete(
        "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert res_fake.status_code == 404

    # 2. Delete session twice
    res_s = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Double Delete"},
        headers=headers,
    )
    session_id = res_s.json()["data"]["id"]

    res_del1 = await api_client.delete(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert res_del1.status_code == 204

    res_del2 = await api_client.delete(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert res_del2.status_code == 404


# ============================================================================
# Section 2: SSE Streaming Endpoint Stress & Edge Cases
# ============================================================================


def parse_sse_events(sse_raw_text: str) -> list[dict[str, Any]]:
    """Helper to parse SSE string into list of event dicts with 'event' and 'data' keys."""
    events = []
    blocks = sse_raw_text.strip().split("\n\n")
    for block in blocks:
        if not block.strip():
            continue
        lines = block.strip().split("\n")
        evt_type = None
        evt_data = None
        for line in lines:
            if line.startswith("event:"):
                evt_type = line.replace("event:", "").strip()
            elif line.startswith("data:"):
                data_str = line.replace("data:", "").strip()
                try:
                    evt_data = json.loads(data_str)
                except json.JSONDecodeError:
                    evt_data = data_str
        if evt_type:
            events.append({"event": evt_type, "data": evt_data})
    return events


@pytest.mark.asyncio
async def test_sse_stream_exact_event_structure(
    api_client: AsyncClient,
    student_user: User,
    sample_doc_for_challenger: Document,
):
    """Test SSE streaming structure and data format with custom mocked LLM tokens."""
    headers = auth_headers_for(student_user)
    res_s = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "SSE Structure Test"},
        headers=headers,
    )
    session_id = res_s.json()["data"]["id"]

    mock_llm = MockStreamingLLMProvider(tokens=["Trích ", "yếu: ", "7 ngày."])

    with patch("app.modules.chat.service.get_llm_provider", return_value=mock_llm):
        res_stream = await api_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages/stream",
            json={"content": "Thời hạn khiếu nại kết quả rèn luyện?"},
            headers=headers,
        )
        assert res_stream.status_code == 200
        assert "text/event-stream" in res_stream.headers["content-type"]

        events = parse_sse_events(res_stream.text)
        assert len(events) >= 5  # 1 citation, 3 tokens, 1 done

        # 1. Event 0: citation
        assert events[0]["event"] == "citation"
        assert events[0]["data"]["has_sufficient_evidence"] is True
        assert len(events[0]["data"]["citations"]) > 0
        c0 = events[0]["data"]["citations"][0]
        assert "document_id" in c0
        assert "page_number" in c0
        assert "quote" in c0

        # 2. Middle events: tokens
        token_events = [e for e in events if e["event"] == "token"]
        streamed_text = "".join(t["data"]["token"] for t in token_events)
        assert streamed_text == "Trích yếu: 7 ngày."

        # 3. Last event: done
        done_event = events[-1]
        assert done_event["event"] == "done"
        assert "message_id" in done_event["data"]
        assert "tokens_used" in done_event["data"]
        assert done_event["data"]["tokens_used"] > 0


@pytest.mark.asyncio
async def test_sse_stream_persists_assistant_message_in_db(
    api_client: AsyncClient,
    student_user: User,
    db_session_factory,
    sample_doc_for_challenger: Document,
):
    """Test stream assistant answer is saved in DB and queryable via GET messages."""
    headers = auth_headers_for(student_user)
    res_s = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Stream DB Persistence"},
        headers=headers,
    )
    session_id = res_s.json()["data"]["id"]

    mock_llm = MockStreamingLLMProvider(tokens=["Nội ", "dung ", "streamed."])

    with patch("app.modules.chat.service.get_llm_provider", return_value=mock_llm):
        res_stream = await api_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages/stream",
            json={"content": "Test persistent stream"},
            headers=headers,
        )
        assert res_stream.status_code == 200
        events = parse_sse_events(res_stream.text)
        done_evt = [e for e in events if e["event"] == "done"][0]
        msg_id = done_evt["data"]["message_id"]

    # Verify message detail via GET messages endpoint
    res_msgs = await api_client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
    )
    assert res_msgs.status_code == 200
    msg_list = res_msgs.json()["data"]
    assert len(msg_list) == 2
    assistant_msg = msg_list[1]
    assert assistant_msg["id"] == msg_id
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"] == "Nội dung streamed."
    assert assistant_msg["has_sufficient_evidence"] is True


@pytest.mark.asyncio
async def test_sse_stream_no_evidence_fallback(
    api_client: AsyncClient,
    student_user: User,
):
    """Test SSE streaming behavior when RAG returns 0 evidence."""
    headers = auth_headers_for(student_user)
    res_s = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Stream No Evidence"},
        headers=headers,
    )
    session_id = res_s.json()["data"]["id"]

    empty_search_resp = SearchResponse(items=[], total=0, page=1, size=10, query="XYZ999")
    with patch("app.modules.chat.service.search_documents", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = empty_search_resp

        res_stream = await api_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages/stream",
            json={"content": "Câu hỏi không có trong DB XYZ999?"},
            headers=headers,
        )
        assert res_stream.status_code == 200
        events = parse_sse_events(res_stream.text)

        # Event 0: citation with False
        assert events[0]["event"] == "citation"
        assert events[0]["data"]["has_sufficient_evidence"] is False
        assert len(events[0]["data"]["citations"]) == 0

        # Event 1: token with fallback message
        assert events[1]["event"] == "token"
        assert "Không tìm thấy thông tin phù hợp" in events[1]["data"]["token"]

        # Event 2: done
        assert events[2]["event"] == "done"


@pytest.mark.asyncio
async def test_sse_stream_invalid_session_id_or_unauthorized(
    api_client: AsyncClient,
    student_user: User,
    admin_user: User,
):
    """Test SSE streaming with non-existent session ID and cross-user ownership violation."""
    headers_student = auth_headers_for(student_user)
    headers_admin = auth_headers_for(admin_user)

    # 1. Non-existent session ID -> returns event: error in stream
    res_fake = await api_client.post(
        "/api/v1/chat/sessions/invalid-session-id-9999/messages/stream",
        json={"content": "Hello?"},
        headers=headers_student,
    )
    assert res_fake.status_code == 200
    events_fake = parse_sse_events(res_fake.text)
    assert len(events_fake) == 1
    assert events_fake[0]["event"] == "error"
    assert "Không tìm thấy" in events_fake[0]["data"]["error"]

    # 2. Student attempting stream on Admin's session ID -> ownership error in stream
    res_admin_session = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Admin Confidential Session"},
        headers=headers_admin,
    )
    admin_session_id = res_admin_session.json()["data"]["id"]

    res_cross_user = await api_client.post(
        f"/api/v1/chat/sessions/{admin_session_id}/messages/stream",
        json={"content": "Attempting cross-user access"},
        headers=headers_student,
    )
    assert res_cross_user.status_code == 200
    events_cross = parse_sse_events(res_cross_user.text)
    assert len(events_cross) == 1
    assert events_cross[0]["event"] == "error"
    assert "Không tìm thấy" in events_cross[0]["data"]["error"]


@pytest.mark.asyncio
async def test_sse_stream_empty_content_payload(
    api_client: AsyncClient,
    student_user: User,
):
    """Test stream endpoint with empty string message content -> 422 validation error."""
    headers = auth_headers_for(student_user)
    res_s = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Empty Msg Test"},
        headers=headers,
    )
    session_id = res_s.json()["data"]["id"]

    res_empty = await api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages/stream",
        json={"content": ""},
        headers=headers,
    )
    assert res_empty.status_code == 422


@pytest.mark.asyncio
async def test_sse_stream_exception_during_llm_generation(
    api_client: AsyncClient,
    student_user: User,
    sample_doc_for_challenger: Document,
):
    """Test stream behavior when LLM provider raises an exception mid-stream."""
    headers = auth_headers_for(student_user)
    res_s = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "LLM Error Test"},
        headers=headers,
    )
    session_id = res_s.json()["data"]["id"]

    mock_failing_llm = MockStreamingLLMProvider(
        raise_exc=RuntimeError("Ollama provider connection timeout")
    )

    with patch("app.modules.chat.service.get_llm_provider", return_value=mock_failing_llm):
        res_stream = await api_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages/stream",
            json={"content": "Test stream error handling"},
            headers=headers,
        )
        assert res_stream.status_code == 200
        events = parse_sse_events(res_stream.text)

        # 1. Event 0: citation was yielded before error
        assert events[0]["event"] == "citation"

        # 2. Event 1: error event caught by sse_generator wrapper
        assert events[1]["event"] == "error"
        assert "Ollama provider connection timeout" in events[1]["data"]["error"]
