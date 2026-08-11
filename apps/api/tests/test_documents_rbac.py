"""RBAC & Scope filtering unit/integration tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.document import Document
from app.models.user import User
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_student_cannot_see_internal_documents(
    api_client: AsyncClient,
    admin_user: User,
    student_user: User,
    db_session_factory,
) -> None:
    async with db_session_factory() as session:
        doc_pub = Document(
            id="doc_rbac_pub",
            title="Tài liệu công khai",
            type="THONG_BAO",
            status="APPROVED",
            scope="PUBLIC",
            author_id=admin_user.id,
        )
        doc_sa = Document(
            id="doc_rbac_sa",
            title="Tài liệu công tác sinh viên",
            type="HUONG_DAN",
            status="APPROVED",
            scope="STUDENT_AFFAIRS",
            author_id=admin_user.id,
        )
        doc_int = Document(
            id="doc_rbac_int",
            title="Tài liệu nội bộ phòng",
            type="QUY_DINH",
            status="APPROVED",
            scope="INTERNAL",
            author_id=admin_user.id,
        )
        session.add_all([doc_pub, doc_sa, doc_int])
        await session.commit()

    # Admin list sees all 3
    admin_headers = auth_headers_for(admin_user)
    resp_admin = await api_client.get("/api/v1/documents", headers=admin_headers)
    assert resp_admin.status_code == 200
    assert resp_admin.json()["total"] == 3

    # Student list sees only PUBLIC and STUDENT_AFFAIRS (total = 2)
    student_headers = auth_headers_for(student_user)
    resp_student = await api_client.get("/api/v1/documents", headers=student_headers)
    assert resp_student.status_code == 200
    assert resp_student.json()["total"] == 2
    scopes = {doc["scope"] for doc in resp_student.json()["data"]}
    assert "INTERNAL" not in scopes


@pytest.mark.asyncio
async def test_student_get_internal_document_returns_403(
    api_client: AsyncClient,
    admin_user: User,
    student_user: User,
    db_session_factory,
) -> None:
    async with db_session_factory() as session:
        doc_int = Document(
            id="doc_rbac_int_2",
            title="Nội bộ bảo mật",
            type="QUYET_DINH",
            status="APPROVED",
            scope="INTERNAL",
            author_id=admin_user.id,
        )
        session.add(doc_int)
        await session.commit()

    student_headers = auth_headers_for(student_user)
    resp = await api_client.get("/api/v1/documents/doc_rbac_int_2", headers=student_headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_student_cannot_upload_or_delete(api_client: AsyncClient, student_user: User) -> None:
    headers = auth_headers_for(student_user)
    headers["Idempotency-Key"] = "11111111-2222-3333-4444-555555555555"

    # Upload attempt -> 403
    files = {"file": ("test.pdf", b"%PDF-1.7 ...", "application/pdf")}
    data = {"title": "Test upload", "type": "THONG_BAO", "scope": "PUBLIC"}
    resp_upload = await api_client.post(
        "/api/v1/documents", files=files, data=data, headers=headers
    )
    assert resp_upload.status_code == 403

    # Delete attempt -> 403
    resp_delete = await api_client.delete("/api/v1/documents/some_doc_id", headers=headers)
    assert resp_delete.status_code == 403


@pytest.mark.asyncio
async def test_staff_cannot_delete_document(
    api_client: AsyncClient, staff_user: User, admin_user: User, db_session_factory
) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_rbac_staff_del",
            title="Tài liệu staff không được xoá",
            type="THONG_BAO",
            status="DRAFT",
            scope="PUBLIC",
            author_id=admin_user.id,
        )
        session.add(doc)
        await session.commit()

    staff_headers = auth_headers_for(staff_user)
    resp = await api_client.delete("/api/v1/documents/doc_rbac_staff_del", headers=staff_headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"
