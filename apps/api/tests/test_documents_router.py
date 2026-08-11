"""Integration tests for Document Management router endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.document import Document
from app.models.user import User
from tests.conftest import auth_headers_for

VALID_PDF_BYTES = (
    b"%PDF-1.7 header\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
)


@pytest.mark.asyncio
async def test_list_documents_empty(api_client: AsyncClient, admin_user: User) -> None:
    headers = auth_headers_for(admin_user)
    resp = await api_client.get("/api/v1/documents", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["limit"] == 20


@pytest.mark.asyncio
async def test_list_documents_pagination_and_filters(
    api_client: AsyncClient, admin_user: User, db_session_factory
) -> None:
    async with db_session_factory() as session:
        doc1 = Document(
            id="doc_test_01",
            title="Quy chế đào tạo đại học 2026",
            type="QUY_CHE",
            status="APPROVED",
            scope="PUBLIC",
            code_number="QC-01/2026",
            author_id=admin_user.id,
            tags=["dao_tao", "quy_che"],
        )
        doc2 = Document(
            id="doc_test_02",
            title="Thông báo học bổng học tập HK1",
            type="THONG_BAO",
            status="DRAFT",
            scope="STUDENT_AFFAIRS",
            code_number="TB-02/2026",
            author_id=admin_user.id,
            tags=["hoc_bong"],
        )
        session.add_all([doc1, doc2])
        await session.commit()

    headers = auth_headers_for(admin_user)

    # All list
    resp = await api_client.get("/api/v1/documents", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2

    # Filter by type
    resp_type = await api_client.get("/api/v1/documents?type=QUY_CHE", headers=headers)
    assert resp_type.status_code == 200
    assert resp_type.json()["total"] == 1
    assert resp_type.json()["data"][0]["id"] == "doc_test_01"

    # Filter by status
    resp_status = await api_client.get("/api/v1/documents?status=DRAFT", headers=headers)
    assert resp_status.status_code == 200
    assert resp_status.json()["total"] == 1

    # Search query
    resp_q = await api_client.get("/api/v1/documents?q=học+bổng", headers=headers)
    assert resp_q.status_code == 200
    assert resp_q.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_document_detail_success_and_not_found(
    api_client: AsyncClient, admin_user: User, db_session_factory
) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_detail_01",
            title="Tài liệu chi tiết",
            type="QUY_DINH",
            status="APPROVED",
            scope="PUBLIC",
            author_id=admin_user.id,
        )
        session.add(doc)
        await session.commit()

    headers = auth_headers_for(admin_user)

    # Success
    resp = await api_client.get("/api/v1/documents/doc_detail_01", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == "doc_detail_01"

    # Not found
    resp_nf = await api_client.get("/api/v1/documents/non_existent_id", headers=headers)
    assert resp_nf.status_code == 404
    assert resp_nf.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_document_metadata(
    api_client: AsyncClient, staff_user: User, db_session_factory
) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_patch_01",
            title="Tiêu đề cũ",
            type="THONG_BAO",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
        )
        session.add(doc)
        await session.commit()

    headers = auth_headers_for(staff_user)
    payload = {"title": "Tiêu đề mới đã cập nhật", "scope": "STUDENT_AFFAIRS"}

    resp = await api_client.patch("/api/v1/documents/doc_patch_01", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "Tiêu đề mới đã cập nhật"
    assert data["scope"] == "STUDENT_AFFAIRS"


@pytest.mark.asyncio
async def test_delete_document_soft_delete(
    api_client: AsyncClient, admin_user: User, db_session_factory
) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_del_01",
            title="Tài liệu sắp xoá",
            type="KHAC",
            status="DRAFT",
            scope="PUBLIC",
            author_id=admin_user.id,
        )
        session.add(doc)
        await session.commit()

    headers = auth_headers_for(admin_user)

    # Soft delete
    resp = await api_client.delete("/api/v1/documents/doc_del_01", headers=headers)
    assert resp.status_code == 204

    # Should no longer be visible in detail or list
    resp_detail = await api_client.get("/api/v1/documents/doc_del_01", headers=headers)
    assert resp_detail.status_code == 404

    resp_list = await api_client.get("/api/v1/documents", headers=headers)
    assert resp_list.json()["total"] == 0
