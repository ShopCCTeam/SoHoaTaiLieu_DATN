"""Integration tests for Document Versions API & Lifecycle Invariants."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.user import User
from tests.conftest import auth_headers_for

VALID_PDF_BYTES = (
    b"%PDF-1.7 header\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
)


@pytest.mark.asyncio
async def test_document_versions_lifecycle(
    api_client: AsyncClient, staff_user: User, db_session_factory
) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_ver_test_01",
            title="Quyết định ban hành 2026",
            type="QUYET_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
            latest_version=1,
        )
        ver1 = DocumentVersion(
            id="ver_01",
            document_id="doc_ver_test_01",
            version_number=1,
            status="DRAFT",
            file_url="/storage/v1.pdf",
            file_size=1024,
            checksum="abc123sha256",
            ocr_status="NOT_STARTED",
            created_by=staff_user.id,
        )
        session.add_all([doc, ver1])
        await session.commit()

    headers = auth_headers_for(staff_user)

    # 1. List versions
    resp_list = await api_client.get("/api/v1/documents/doc_ver_test_01/versions", headers=headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()["data"]) == 1

    # 2. Get version detail
    resp_detail = await api_client.get(
        "/api/v1/documents/doc_ver_test_01/versions/ver_01", headers=headers
    )
    assert resp_detail.status_code == 200
    assert resp_detail.json()["data"]["id"] == "ver_01"

    # 3. Patch version metadata
    resp_patch = await api_client.patch(
        "/api/v1/documents/doc_ver_test_01/versions/ver_01/metadata",
        json={"change_summary": "Sửa đổi nội dung điều 3"},
        headers=headers,
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["data"]["change_summary"] == "Sửa đổi nội dung điều 3"

    # 4. Trigger OCR
    headers["Idempotency-Key"] = "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b"
    resp_ocr = await api_client.post(
        "/api/v1/documents/doc_ver_test_01/versions/ver_01/ocr", headers=headers
    )
    assert resp_ocr.status_code == 202
    assert resp_ocr.json()["data"]["job_id"].startswith("job_")

    # 5. Upload version 2
    headers["Idempotency-Key"] = "f6a7b89c-0d1e-2f3a-4b5c-6d7e8f9a0b1c"
    files = {"file": ("v2.pdf", VALID_PDF_BYTES, "application/pdf")}
    data = {"change_summary": "Cập nhật bản v2 hoàn chỉnh"}
    resp_v2 = await api_client.post(
        "/api/v1/documents/doc_ver_test_01/versions",
        files=files,
        data=data,
        headers=headers,
    )
    assert resp_v2.status_code == 202


@pytest.mark.asyncio
async def test_approve_version_invariants_check(
    api_client: AsyncClient, staff_user: User, db_session_factory
) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_ver_app_01",
            title="Quy định chờ duyệt",
            type="QUY_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
        )
        ver_pending_ocr = DocumentVersion(
            id="ver_pending_ocr",
            document_id="doc_ver_app_01",
            version_number=1,
            status="DRAFT",
            file_url="/storage/v1.pdf",
            file_size=1024,
            checksum="checksum_hash",
            ocr_status="PROCESSING",  # Not succeeded yet!
            created_by=staff_user.id,
        )
        session.add_all([doc, ver_pending_ocr])
        await session.commit()

    headers = auth_headers_for(staff_user)

    # Attempting to approve while ocr_status != SUCCEEDED -> 409 Conflict
    resp_conflict = await api_client.post(
        "/api/v1/documents/doc_ver_app_01/versions/ver_pending_ocr/approve",
        headers=headers,
    )
    assert resp_conflict.status_code == 409
    assert resp_conflict.json()["code"] == "CONFLICT"

    # Set ocr_status = SUCCEEDED
    async with db_session_factory() as session:
        v = await session.get(DocumentVersion, "ver_pending_ocr")
        v.ocr_status = "SUCCEEDED"
        await session.commit()

    # Now approve should succeed
    resp_approve = await api_client.post(
        "/api/v1/documents/doc_ver_app_01/versions/ver_pending_ocr/approve",
        headers=headers,
    )
    assert resp_approve.status_code == 200
    assert resp_approve.json()["data"]["status"] == "APPROVED"

    # Patch metadata on APPROVED version -> 409 Conflict
    resp_patch_approved = await api_client.patch(
        "/api/v1/documents/doc_ver_app_01/versions/ver_pending_ocr/metadata",
        json={"change_summary": "Sửa sau khi đã duyệt"},
        headers=headers,
    )
    assert resp_patch_approved.status_code == 409
    assert resp_patch_approved.json()["code"] == "CONFLICT"
