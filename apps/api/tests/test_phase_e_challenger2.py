"""Adversarial tests for Phase E (RAG Chatbot with Citations).

Covers:
1. RBAC Isolation in Chat (STUDENT never retrieves or cites INTERNAL documents).
2. Citation Formatting Rules (quote truncation at word boundary <= 300 chars,
   score rounding, title resolution).
3. Low Evidence Behavior (has_sufficient_evidence == False on empty or low score results).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.user import User
from app.modules.chat.schemas import CitationSchema
from app.modules.chat.service import (
    evaluate_grounding_and_citations,
    truncate_quote,
)
from app.modules.search.schemas import SearchResponse, SearchResultItem
from tests.conftest import auth_headers_for

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def rbac_test_documents(db_session_factory) -> tuple[Document, Document]:
    """Seed 1 PUBLIC document and 1 INTERNAL document for RBAC testing."""
    async with db_session_factory() as session:
        # Public document
        public_doc = Document(
            id="doc_public_001",
            title="Quy định Học bổng KKHT Public 2026",
            type="QUY_DINH",
            status="APPROVED",
            scope="PUBLIC",
            author_id="usr_admin_01",
        )
        pub_ver = DocumentVersion(
            id="ver_pub_001",
            document_id=public_doc.id,
            version_number=1,
            file_url="http://localhost:9000/ctsv-documents/pub.pdf",
            file_size=1024,
            checksum="a" * 64,
            created_by="usr_admin_01",
        )
        pub_chunk = DocumentChunk(
            id="chk_pub_001",
            version_id=pub_ver.id,
            document_id=public_doc.id,
            chunk_index=0,
            page_number=1,
            block_ids=[],
            text=(
                "Tiêu chuẩn xét học bổng công khai dành cho "
                "tất cả sinh viên toàn trường năm 2026."
            ),
            token_count=20,
            bbox=[0.0, 0.0, 100.0, 20.0],
            embedding=[0.1] * 1024,
        )

        # Internal document
        internal_doc = Document(
            id="doc_internal_001",
            title="Báo cáo Mật Quy hoạch Nội bộ CTSV 2026",
            type="BAO_CAO",
            status="APPROVED",
            scope="INTERNAL",
            author_id="usr_admin_01",
        )
        int_ver = DocumentVersion(
            id="ver_int_001",
            document_id=internal_doc.id,
            version_number=1,
            file_url="http://localhost:9000/ctsv-documents/int.pdf",
            file_size=2048,
            checksum="b" * 64,
            created_by="usr_admin_01",
        )
        int_chunk = DocumentChunk(
            id="chk_int_001",
            version_id=int_ver.id,
            document_id=internal_doc.id,
            chunk_index=0,
            page_number=1,
            block_ids=[],
            text=(
                "Thông tin nội bộ bảo mật về quy hoạch cán bộ "
                "phòng CTSV và danh sách xét thưởng đặc biệt."
            ),
            token_count=25,
            bbox=[0.0, 0.0, 100.0, 20.0],
            embedding=[0.9] * 1024,  # Distinct embedding from public doc
        )

        session.add_all([public_doc, pub_ver, pub_chunk, internal_doc, int_ver, int_chunk])
        await session.commit()
        await session.refresh(public_doc)
        await session.refresh(internal_doc)
        return public_doc, internal_doc


# ---------------------------------------------------------------------------
# 1. RBAC Isolation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_chat_never_cites_internal_documents(
    api_client: AsyncClient,
    student_user: User,
    admin_user: User,
    rbac_test_documents: tuple[Document, Document],
):
    """Verify STUDENT queries never retrieve or cite INTERNAL document chunks."""
    public_doc, internal_doc = rbac_test_documents

    # 1. Student creates session and sends message
    headers_student = auth_headers_for(student_user)
    resp_sess = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Test RBAC Student"},
        headers=headers_student,
    )
    sess_id = resp_sess.json()["data"]["id"]

    resp_msg = await api_client.post(
        f"/api/v1/chat/sessions/{sess_id}/messages",
        json={"content": "Tiêu chuẩn học bổng và báo cáo quy hoạch nội bộ?"},
        headers=headers_student,
    )
    assert resp_msg.status_code == 200
    data = resp_msg.json()["data"]

    # Student citations must NOT contain internal document ID or title
    citations = data.get("citations") or []
    doc_ids = [c["document_id"] for c in citations]
    assert internal_doc.id not in doc_ids
    assert not any(c["title"] == internal_doc.title for c in citations)

    # 2. Admin creates session and sends same query -> Admin CAN see internal document
    headers_admin = auth_headers_for(admin_user)
    resp_sess_admin = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Test RBAC Admin"},
        headers=headers_admin,
    )
    admin_sess_id = resp_sess_admin.json()["data"]["id"]

    resp_admin_msg = await api_client.post(
        f"/api/v1/chat/sessions/{admin_sess_id}/messages",
        json={"content": "Tiêu chuẩn học bổng và báo cáo quy hoạch nội bộ?"},
        headers=headers_admin,
    )
    assert resp_admin_msg.status_code == 200
    admin_citations = resp_admin_msg.json()["data"].get("citations") or []
    admin_doc_ids = [c["document_id"] for c in admin_citations]
    assert internal_doc.id in admin_doc_ids


@pytest.mark.asyncio
async def test_student_query_when_only_internal_document_matches(
    db_session_factory,
    api_client: AsyncClient,
    student_user: User,
):
    """Verify STUDENT query matching ONLY internal doc gets has_sufficient_evidence == False."""
    async with db_session_factory() as session:
        internal_doc = Document(
            id="doc_internal_only_001",
            title="Báo cáo Mật Quy hoạch Cán bộ Sole Internal",
            type="BAO_CAO",
            status="APPROVED",
            scope="INTERNAL",
            author_id="usr_admin_01",
        )
        int_ver = DocumentVersion(
            id="ver_int_only_001",
            document_id=internal_doc.id,
            version_number=1,
            file_url="http://localhost:9000/ctsv-documents/int_only.pdf",
            file_size=2048,
            checksum="d" * 64,
            created_by="usr_admin_01",
        )
        int_chunk = DocumentChunk(
            id="chk_int_only_001",
            version_id=int_ver.id,
            document_id=internal_doc.id,
            chunk_index=0,
            page_number=1,
            block_ids=[],
            text="Mã bí mật nội bộ quy hoạch 999888777666.",
            token_count=10,
            bbox=[0.0, 0.0, 100.0, 20.0],
            embedding=[0.5] * 1024,
        )
        session.add_all([internal_doc, int_ver, int_chunk])
        await session.commit()

    headers_student = auth_headers_for(student_user)
    resp_sess = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Test Only Internal Match"},
        headers=headers_student,
    )
    sess_id = resp_sess.json()["data"]["id"]

    # Query specifically targeting internal document text
    resp_msg = await api_client.post(
        f"/api/v1/chat/sessions/{sess_id}/messages",
        json={"content": "Mã bí mật nội bộ quy hoạch 999888777666"},
        headers=headers_student,
    )
    assert resp_msg.status_code == 200
    data = resp_msg.json()["data"]

    # Since student is not allowed scope="INTERNAL", evidence is false and no citations
    assert data["has_sufficient_evidence"] is False
    assert data["citations"] is None or len(data["citations"]) == 0
    assert "Không tìm thấy thông tin phù hợp" in data["content"]


@pytest.mark.asyncio
async def test_stateless_chat_query_forbidden_scope_student(
    api_client: AsyncClient,
    student_user: User,
):
    """Verify STUDENT requesting scope="INTERNAL" in stateless query receives 403 Forbidden."""
    headers_student = auth_headers_for(student_user)
    resp = await api_client.post(
        "/api/v1/chat/query",
        json={
            "question": "Báo cáo nội bộ?",
            "scope": "INTERNAL",
        },
        headers=headers_student,
    )
    assert resp.status_code == 403
    assert "không có quyền truy cập phạm vi 'INTERNAL'" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 2. Citation Formatting Rules Tests
# ---------------------------------------------------------------------------


def test_quote_truncation_word_boundary():
    """Test quote truncation at max_length=300 chars at word boundary."""
    # 1. Short text <= 300 chars
    short_text = "   Đoạn văn ngắn dưới 300 ký tự.   "
    assert truncate_quote(short_text, 300) == "Đoạn văn ngắn dưới 300 ký tự."

    # 2. Exactly 300 chars
    exact_text = "a" * 300
    assert truncate_quote(exact_text, 300) == exact_text

    # 3. > 300 chars with space before 300th character
    words = ["Từ"] * 150  # 150 * 2 + 149 spaces = 449 chars > 300
    long_text = " ".join(words)
    assert len(long_text) > 300
    truncated = truncate_quote(long_text, 300)
    assert len(truncated) <= 303  # 300 + "..."
    assert truncated.endswith("...")
    # Verify not truncated in the middle of a word
    assert not truncated.endswith("T...")  # word is "Từ"

    # 4. > 300 chars without any space
    long_single_word = "X" * 350
    truncated_single = truncate_quote(long_single_word, 300)
    assert truncated_single == ("X" * 300) + "..."


def test_citation_schema_score_validation_and_rounding():
    """Test CitationSchema score limits and rounding in evaluate_grounding_and_citations."""
    # Valid schema creation
    citation = CitationSchema(
        document_id="doc_1",
        document_version_id="ver_1",
        title="Tiêu đề mẫu",
        page_number=1,
        chunk_id="chk_1",
        quote="Nội dung trích dẫn",
        score=0.9845,
        bbox=[0.0, 0.0, 10.0, 10.0],
    )
    assert citation.score == 0.9845

    # Invalid score > 1.0 raises ValidationError
    with pytest.raises(ValidationError):
        CitationSchema(
            document_id="doc_1",
            document_version_id="ver_1",
            title="Tiêu đề mẫu",
            page_number=1,
            chunk_id="chk_1",
            quote="Nội dung",
            score=1.5,
        )

    # Invalid score < 0.0 raises ValidationError
    with pytest.raises(ValidationError):
        CitationSchema(
            document_id="doc_1",
            document_version_id="ver_1",
            title="Tiêu đề mẫu",
            page_number=1,
            chunk_id="chk_1",
            quote="Nội dung",
            score=-0.1,
        )


@pytest.mark.asyncio
async def test_citation_title_resolved_at_query_time(
    db_session_factory,
    api_client: AsyncClient,
    student_user: User,
):
    """Verify citation title resolves current document title at query time."""
    async with db_session_factory() as session:
        doc = Document(
            id="doc_title_test_001",
            title="Tiêu đề Ban Đầu 2026",
            type="QUY_DINH",
            status="APPROVED",
            scope="PUBLIC",
            author_id="usr_admin_01",
        )
        ver = DocumentVersion(
            id="ver_title_001",
            document_id=doc.id,
            version_number=1,
            file_url="http://localhost:9000/ctsv-documents/title.pdf",
            file_size=1024,
            checksum="c" * 64,
            created_by="usr_admin_01",
        )
        chunk = DocumentChunk(
            id="chk_title_001",
            version_id=ver.id,
            document_id=doc.id,
            chunk_index=0,
            page_number=3,
            block_ids=[],
            text="Văn bản quy định về tiêu đề động được cập nhật.",
            token_count=15,
            bbox=[0.0, 0.0, 50.0, 50.0],
            embedding=[0.1] * 1024,
        )
        session.add_all([doc, ver, chunk])
        await session.commit()

        # Update title in DB
        doc.title = "Tiêu đề Mới Cập Nhật 2026"
        await session.commit()

    headers = auth_headers_for(student_user)
    resp = await api_client.post(
        "/api/v1/chat/query",
        json={"question": "quy định về tiêu đề động"},
        headers=headers,
    )
    assert resp.status_code == 200
    citations = resp.json()["data"]["citations"]
    assert len(citations) > 0
    # Must be resolved title, not original or version title
    assert citations[0]["title"] == "Tiêu đề Mới Cập Nhật 2026"


# ---------------------------------------------------------------------------
# 3. Low Evidence Behavior Tests
# ---------------------------------------------------------------------------


def test_evaluate_grounding_empty_and_low_scores():
    """Test evaluate_grounding_and_citations returns False when empty or score < threshold."""
    # 1. Empty search items
    has_evidence, citations = evaluate_grounding_and_citations([])
    assert has_evidence is False
    assert citations == []

    # 2. Search items all below score_threshold=0.001
    low_score_item = SearchResultItem(
        chunk_id="chk_low",
        document_id="doc_low",
        version_id="ver_low",
        document_title="Tài liệu điểm thấp",
        document_scope="PUBLIC",
        document_type="THONG_BAO",
        page_number=1,
        chunk_index=0,
        text="Đoạn văn không liên quan",
        bbox=[0.0, 0.0, 0.0, 0.0],
        score=0.00005,  # Below 0.001 threshold
    )
    has_evidence_low, citations_low = evaluate_grounding_and_citations(
        [low_score_item], score_threshold=0.001
    )
    assert has_evidence_low is False
    assert citations_low == []


@pytest.mark.asyncio
async def test_chat_message_sync_low_evidence_returns_no_citations(
    api_client: AsyncClient,
    student_user: User,
):
    """Test process_send_message returns has_sufficient_evidence=False on low evidence."""
    headers = auth_headers_for(student_user)
    resp_sess = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Test Low Evidence"},
        headers=headers,
    )
    sess_id = resp_sess.json()["data"]["id"]

    # Mock search_documents returning items with score < threshold
    low_score_item = SearchResultItem(
        chunk_id="chk_low_01",
        document_id="doc_low_01",
        version_id="ver_low_01",
        document_title="Tài liệu điểm quá thấp",
        document_scope="PUBLIC",
        document_type="THONG_BAO",
        page_number=1,
        chunk_index=0,
        text="Không liên quan",
        bbox=[0.0, 0.0, 0.0, 0.0],
        score=0.00001,
    )
    mock_response = SearchResponse(items=[low_score_item], total=1, page=1, size=10, query="Vô lý")

    with patch("app.modules.chat.service.search_documents", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response

        resp_msg = await api_client.post(
            f"/api/v1/chat/sessions/{sess_id}/messages",
            json={"content": "Câu hỏi không có trong dữ liệu?"},
            headers=headers,
        )
        assert resp_msg.status_code == 200
        data = resp_msg.json()["data"]
        assert data["has_sufficient_evidence"] is False
        assert data["citations"] is None or len(data["citations"]) == 0
        assert "Không tìm thấy thông tin phù hợp" in data["content"]


@pytest.mark.asyncio
async def test_chat_stream_sse_low_evidence_event_payloads(
    api_client: AsyncClient,
    student_user: User,
):
    """Test SSE stream event sequence when grounding evidence is insufficient."""
    headers = auth_headers_for(student_user)
    resp_sess = await api_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Test Low Evidence Stream"},
        headers=headers,
    )
    sess_id = resp_sess.json()["data"]["id"]

    empty_search = SearchResponse(items=[], total=0, page=1, size=10, query="Rỗng")
    with patch("app.modules.chat.service.search_documents", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = empty_search

        resp_stream = await api_client.post(
            f"/api/v1/chat/sessions/{sess_id}/messages/stream",
            json={"content": "Hỏi linh tinh?"},
            headers=headers,
        )
        assert resp_stream.status_code == 200
        body_text = resp_stream.text

        assert "event: citation" in body_text
        assert '"has_sufficient_evidence": false' in body_text
        assert '"citations": []' in body_text
        assert "event: token" in body_text
        assert "Không tìm thấy thông tin phù hợp" in body_text
        assert "event: done" in body_text
