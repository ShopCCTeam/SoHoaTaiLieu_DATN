"""Tests for Chat endpoints, SSE streaming, RBAC citation filtering, and RAG grounding."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.user import User
from app.modules.search.schemas import SearchResponse
from tests.conftest import auth_headers_for


@pytest.fixture
async def sample_document_and_chunks(db_session_factory) -> Document:
    """Seed sample document and chunks for RAG grounding tests."""
    async with db_session_factory() as session:
        doc = Document(
            id="doc_hoc_bong_01",
            title="Quy định Học bổng KKHT 2026",
            type="QUY_DINH",
            status="APPROVED",
            scope="PUBLIC",
            author_id="usr_admin_01",
        )
        version = DocumentVersion(
            id="ver_hb_01",
            document_id=doc.id,
            version_number=1,
            file_url="http://localhost:9000/ctsv-documents/hb.pdf",
            file_size=1024,
            checksum="a" * 64,
            created_by="usr_admin_01",
        )
        chunk = DocumentChunk(
            id="chk_hb_01",
            version_id=version.id,
            document_id=doc.id,
            chunk_index=0,
            page_number=2,
            block_ids=[],
            text=(
                "Học bổng KKHT loại Khá xét cho sinh viên có ĐTB học tập từ 2.50 trở lên "
                "và điểm rèn luyện từ 70 trở lên."
            ),
            token_count=30,
            bbox=[10.0, 20.0, 300.0, 50.0],
            embedding=[0.1] * 1024,
        )
        session.add_all([doc, version, chunk])
        await session.commit()
        await session.refresh(doc)
        return doc


@pytest.mark.asyncio
async def test_create_and_list_chat_sessions(
    api_client: AsyncClient,
    student_user: User,
):
    headers = auth_headers_for(student_user)

    # 1. Create session
    resp_create = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Hỏi về học phí"},
        headers=headers,
    )
    assert resp_create.status_code == 201
    data_create = resp_create.json()
    assert data_create["success"] is True
    session_id = data_create["data"]["id"]
    assert data_create["data"]["title"] == "Hỏi về học phí"
    assert data_create["data"]["user_id"] == student_user.id

    # 2. List sessions
    resp_list = await api_client.get("/api/v1/chat/sessions", headers=headers)
    assert resp_list.status_code == 200
    data_list = resp_list.json()
    assert data_list["total"] >= 1
    assert any(s["id"] == session_id for s in data_list["data"])

    # 3. Get session detail
    resp_detail = await api_client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert resp_detail.status_code == 200
    assert resp_detail.json()["data"]["id"] == session_id

    # 4. Delete session
    resp_del = await api_client.delete(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert resp_del.status_code == 204

    # 5. Verify deleted
    resp_get_deleted = await api_client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert resp_get_deleted.status_code == 404


@pytest.mark.asyncio
async def test_session_ownership_protection(
    api_client: AsyncClient,
    student_user: User,
    admin_user: User,
):
    # Admin creates session
    headers_admin = auth_headers_for(admin_user)
    resp_create = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Session Admin"},
        headers=headers_admin,
    )
    admin_session_id = resp_create.json()["data"]["id"]

    # Student tries to access admin session
    headers_student = auth_headers_for(student_user)
    resp_student_access = await api_client.get(
        f"/api/v1/chat/sessions/{admin_session_id}",
        headers=headers_student,
    )
    assert resp_student_access.status_code == 404

    # Student tries to delete admin session
    resp_student_delete = await api_client.delete(
        f"/api/v1/chat/sessions/{admin_session_id}",
        headers=headers_student,
    )
    assert resp_student_delete.status_code == 404


@pytest.mark.asyncio
async def test_send_chat_message_sync_with_evidence(
    api_client: AsyncClient,
    student_user: User,
    sample_document_and_chunks: Document,
):
    headers = auth_headers_for(student_user)
    resp_session = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Học bổng KKHT"},
        headers=headers,
    )
    session_id = resp_session.json()["data"]["id"]

    # Send chat message
    resp_msg = await api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Học bổng KKHT cần bao nhiêu điểm?"},
        headers=headers,
    )
    assert resp_msg.status_code == 200
    data = resp_msg.json()["data"]
    assert data["role"] == "assistant"
    assert data["has_sufficient_evidence"] is True
    assert data["citations"] is not None
    assert len(data["citations"]) > 0
    assert data["citations"][0]["title"] == "Quy định Học bổng KKHT 2026"
    assert data["citations"][0]["page_number"] == 2

    # Verify message history list
    resp_list_msg = await api_client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
    )
    assert resp_list_msg.status_code == 200
    messages = resp_list_msg.json()["data"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_send_chat_message_sync_without_evidence(
    api_client: AsyncClient,
    student_user: User,
):
    headers = auth_headers_for(student_user)
    resp_session = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Câu hỏi không có trong DB"},
        headers=headers,
    )
    session_id = resp_session.json()["data"]["id"]

    # Mock search returning no items
    empty_search_resp = SearchResponse(items=[], total=0, page=1, size=10, query="XYZ123")
    with patch("app.modules.chat.service.search_documents", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = empty_search_resp

        resp_msg = await api_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Một câu hỏi hoàn toàn vô lý XYZ123?"},
            headers=headers,
        )
        assert resp_msg.status_code == 200
        data = resp_msg.json()["data"]
        assert data["role"] == "assistant"
        assert data["has_sufficient_evidence"] is False
        assert data["citations"] is None or len(data["citations"]) == 0
        assert "Không tìm thấy thông tin phù hợp" in data["content"]


@pytest.mark.asyncio
async def test_send_chat_message_stream_sse(
    api_client: AsyncClient,
    student_user: User,
    sample_document_and_chunks: Document,
):
    headers = auth_headers_for(student_user)
    resp_session = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "SSE Stream test"},
        headers=headers,
    )
    session_id = resp_session.json()["data"]["id"]

    resp_stream = await api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages/stream",
        json={"content": "Quy định học bổng KKHT?"},
        headers=headers,
    )
    assert resp_stream.status_code == 200
    assert "text/event-stream" in resp_stream.headers["content-type"]

    body_text = resp_stream.text
    assert "event: citation" in body_text
    assert "event: token" in body_text
    assert "event: done" in body_text


@pytest.mark.asyncio
async def test_stateless_chat_query(
    api_client: AsyncClient,
    student_user: User,
    sample_document_and_chunks: Document,
):
    headers = auth_headers_for(student_user)

    # Valid query
    resp = await api_client.post(
        "/api/v1/chat/query",
        json={
            "question": "Quy định điểm học bổng?",
            "top_k": 3,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "answer" in data
    assert data["has_sufficient_evidence"] is True
    assert len(data["citations"]) > 0

    # Query with forbidden scope for student (STUDENT_AFFAIRS / INTERNAL)
    resp_forbidden = await api_client.post(
        "/api/v1/chat/query",
        json={
            "question": "Báo cáo nội bộ?",
            "scope": "INTERNAL",
        },
        headers=headers,
    )
    assert resp_forbidden.status_code == 403
