"""Integration and unit tests for Search API & Celery Indexing Task."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.ocr_block import OCRBlock
from app.models.ocr_page import OCRPage
from app.models.user import User
from app.services.embedding import MockEmbeddingStrategy
from app.worker.tasks import _async_index_document_chunks
from tests.conftest import auth_headers_for


@pytest.fixture
async def seeded_search_data(db_session_factory, admin_user: User) -> dict[str, str]:
    """Seed documents, versions, and document_chunks into DB."""
    strategy = MockEmbeddingStrategy()
    emb1 = await strategy.embed_query("Quy chế đào tạo đại học chính quy 2026")
    emb2 = await strategy.embed_query("Thông báo xét cấp học bổng khuyến khích học tập")

    async with db_session_factory() as session:
        doc1 = Document(
            id="doc_search_01",
            title="Quy chế đào tạo đại học 2026",
            type="QUY_CHE",
            status="APPROVED",
            scope="PUBLIC",
            code_number="QC-2026",
            author_id=admin_user.id,
        )
        ver1 = DocumentVersion(
            id="ver_search_01",
            document_id=doc1.id,
            version_number=1,
            status="APPROVED",
            file_url="/files/qc2026.pdf",
            file_size=1024,
            checksum="abc123hash",
            ocr_status="SUCCEEDED",
            created_by=admin_user.id,
        )

        doc2 = Document(
            id="doc_search_02",
            title="Thông báo học bổng HK1",
            type="THONG_BAO",
            status="APPROVED",
            scope="INTERNAL",
            code_number="TB-2026",
            author_id=admin_user.id,
        )
        ver2 = DocumentVersion(
            id="ver_search_02",
            document_id=doc2.id,
            version_number=1,
            status="APPROVED",
            file_url="/files/tb2026.pdf",
            file_size=2048,
            checksum="def456hash",
            ocr_status="SUCCEEDED",
            created_by=admin_user.id,
        )

        chunk1 = DocumentChunk(
            id="chunk_s1",
            version_id=ver1.id,
            document_id=doc1.id,
            chunk_index=0,
            page_number=1,
            block_ids=["blk_1"],
            text="Quy chế đào tạo đại học chính quy quy định về tín chỉ và điểm rèn luyện.",
            token_count=15,
            bbox=[10.0, 10.0, 200.0, 50.0],
            embedding=emb1,
            fulltext_tsv="Quy chế đào tạo đại học chính quy quy định về tín chỉ và điểm rèn luyện.",
        )
        chunk2 = DocumentChunk(
            id="chunk_s2",
            version_id=ver2.id,
            document_id=doc2.id,
            chunk_index=0,
            page_number=1,
            block_ids=["blk_2"],
            text="Thông báo xét cấp học bổng khuyến khích học tập cho sinh viên xuất sắc.",
            token_count=14,
            bbox=[15.0, 15.0, 210.0, 60.0],
            embedding=emb2,
            fulltext_tsv="Thông báo xét cấp học bổng khuyến khích học tập cho sinh viên xuất sắc.",
        )

        session.add_all([doc1, ver1, doc2, ver2, chunk1, chunk2])
        await session.commit()

    return {
        "doc1_id": doc1.id,
        "doc2_id": doc2.id,
        "ver1_id": ver1.id,
        "ver2_id": ver2.id,
    }


@pytest.mark.asyncio
async def test_search_get_success(
    api_client: AsyncClient, admin_user: User, seeded_search_data: dict[str, str]
) -> None:
    headers = auth_headers_for(admin_user)
    resp = await api_client.get("/api/v1/search?q=quy+chế", headers=headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["success"] is True
    assert "data" in body
    items = body["data"]["items"]
    assert len(items) > 0
    assert items[0]["document_id"] == seeded_search_data["doc1_id"]
    assert items[0]["document_title"] == "Quy chế đào tạo đại học 2026"


@pytest.mark.asyncio
async def test_search_post_success(
    api_client: AsyncClient, admin_user: User, seeded_search_data: dict[str, str]
) -> None:
    headers = auth_headers_for(admin_user)
    payload = {
        "query": "học bổng",
        "top_k": 5,
        "alpha": 0.5,
        "page": 1,
        "size": 10,
    }
    resp = await api_client.post("/api/v1/search", json=payload, headers=headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert len(items) > 0
    doc_ids = [item["document_id"] for item in items]
    assert seeded_search_data["doc2_id"] in doc_ids


@pytest.mark.asyncio
async def test_search_rbac_scope_access(
    api_client: AsyncClient,
    admin_user: User,
    student_user: User,
    seeded_search_data: dict[str, str],
) -> None:
    # Admin can search INTERNAL
    admin_headers = auth_headers_for(admin_user)
    resp_admin = await api_client.get(
        "/api/v1/search?q=học+bổng&scope=INTERNAL", headers=admin_headers
    )
    assert resp_admin.status_code == 200

    # Student requesting INTERNAL scope -> 403 Forbidden
    student_headers = auth_headers_for(student_user)
    resp_student_forbidden = await api_client.get(
        "/api/v1/search?q=học+bổng&scope=INTERNAL", headers=student_headers
    )
    assert resp_student_forbidden.status_code == 403

    # Student searching PUBLIC scope -> 200 OK
    resp_student_ok = await api_client.get(
        "/api/v1/search?q=quy+chế&scope=PUBLIC", headers=student_headers
    )
    assert resp_student_ok.status_code == 200
    assert (
        resp_student_ok.json()["data"]["items"][0]["document_id"] == seeded_search_data["doc1_id"]
    )


@pytest.mark.asyncio
async def test_search_filter_by_type(
    api_client: AsyncClient, admin_user: User, seeded_search_data: dict[str, str]
) -> None:
    headers = auth_headers_for(admin_user)
    resp = await api_client.get("/api/v1/search?q=đào+tạo&type=QUY_CHE", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    for item in items:
        assert item["document_type"] == "QUY_CHE"


@pytest.mark.asyncio
async def test_index_document_chunks_task_execution(db_session_factory, admin_user: User) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_idx_01",
            title="Tài liệu index tự động",
            type="QUY_DINH",
            status="APPROVED",
            scope="PUBLIC",
            author_id=admin_user.id,
        )
        ver = DocumentVersion(
            id="ver_idx_01",
            document_id=doc.id,
            version_number=1,
            status="APPROVED",
            file_url="/files/idx.pdf",
            file_size=1024,
            checksum="hashidx",
            ocr_status="SUCCEEDED",
            created_by=admin_user.id,
        )
        page = OCRPage(
            id="page_idx_01",
            version_id=ver.id,
            page_number=1,
            width=600,
            height=800,
            status="COMPLETED",
        )
        block1 = OCRBlock(
            id="blk_idx_01",
            version_id=ver.id,
            page_id=page.id,
            page_number=1,
            block_index=0,
            text_content="Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng quy định này.",
            confidence=0.95,
            bbox=[10.0, 10.0, 300.0, 40.0],
        )
        block2 = OCRBlock(
            id="blk_idx_02",
            version_id=ver.id,
            page_id=page.id,
            page_number=1,
            block_index=1,
            text_content="Điều 2. Nguyên tắc chung trong công tác sinh viên.",
            confidence=0.92,
            bbox=[10.0, 45.0, 300.0, 75.0],
        )

        session.add_all([doc, ver, page, block1, block2])
        await session.commit()

    res = await _async_index_document_chunks("ver_idx_01")
    assert res["status"] == "SUCCEEDED"
    assert res["chunk_count"] > 0

    async with db_session_factory() as session:
        from sqlalchemy import select

        chunks = (
            (
                await session.execute(
                    select(DocumentChunk).where(DocumentChunk.version_id == "ver_idx_01")
                )
            )
            .scalars()
            .all()
        )
        assert len(chunks) == res["chunk_count"]
        assert chunks[0].document_id == "doc_idx_01"
        assert "Điều 1" in chunks[0].text
