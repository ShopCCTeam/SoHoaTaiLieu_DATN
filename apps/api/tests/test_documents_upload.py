"""Integration tests for Document Upload & PDF Validation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import auth_headers_for

VALID_PDF_BYTES = (
    b"%PDF-1.7 header\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
)


@pytest.mark.asyncio
async def test_upload_valid_pdf_returns_202_accepted(
    api_client: AsyncClient, staff_user: User
) -> None:
    headers = auth_headers_for(staff_user)
    headers["Idempotency-Key"] = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"

    files = {"file": ("quy_che_2026.pdf", VALID_PDF_BYTES, "application/pdf")}
    data = {
        "title": "Quy chế Công tác Sinh viên 2026",
        "type": "QUY_CHE",
        "scope": "PUBLIC",
        "issuing_body": "Trường Đại học ABC",
        "tags": "quy_che, sinh_vien",
    }

    resp = await api_client.post("/api/v1/documents", files=files, data=data, headers=headers)
    assert resp.status_code == 202
    res_data = resp.json()
    assert res_data["success"] is True
    assert res_data["data"]["document_id"].startswith("doc_")
    assert res_data["data"]["job_id"].startswith("job_")
    assert res_data["data"]["status"] == "SUCCEEDED" or res_data["data"]["status"] == "QUEUED"


@pytest.mark.asyncio
async def test_upload_missing_idempotency_key(api_client: AsyncClient, staff_user: User) -> None:
    headers = auth_headers_for(staff_user)
    files = {"file": ("test.pdf", VALID_PDF_BYTES, "application/pdf")}
    data = {"title": "Thiếu Idempotency-Key", "type": "THONG_BAO", "scope": "PUBLIC"}

    resp = await api_client.post("/api/v1/documents", files=files, data=data, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_invalid_magic_bytes(api_client: AsyncClient, staff_user: User) -> None:
    headers = auth_headers_for(staff_user)
    headers["Idempotency-Key"] = "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e"

    invalid_pdf = b"INVALID_HEADER_NOT_PDF"
    files = {"file": ("fake.pdf", invalid_pdf, "application/pdf")}
    data = {"title": "File giả mạo PDF", "type": "THONG_BAO", "scope": "PUBLIC"}

    resp = await api_client.post("/api/v1/documents", files=files, data=data, headers=headers)
    assert resp.status_code == 415
    assert resp.json()["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_file_too_large(api_client: AsyncClient, staff_user: User) -> None:
    headers = auth_headers_for(staff_user)
    headers["Idempotency-Key"] = "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f"

    large_pdf = b"%PDF-" + b"X" * (50 * 1024 * 1024 + 1)
    files = {"file": ("large.pdf", large_pdf, "application/pdf")}
    data = {"title": "File quá cỡ", "type": "THONG_BAO", "scope": "PUBLIC"}

    resp = await api_client.post("/api/v1/documents", files=files, data=data, headers=headers)
    assert resp.status_code == 413
    assert resp.json()["code"] == "FILE_SIZE_EXCEEDED"


@pytest.mark.asyncio
async def test_idempotency_replay(api_client: AsyncClient, staff_user: User) -> None:
    headers = auth_headers_for(staff_user)
    idempotency_key = "d4e5f6a7-b89c-0d1e-2f3a-4b5c6d7e8f9a"
    headers["Idempotency-Key"] = idempotency_key

    files = {"file": ("test.pdf", VALID_PDF_BYTES, "application/pdf")}
    data = {"title": "Idempotent upload", "type": "QUY_DINH", "scope": "PUBLIC"}

    # 1st call
    resp1 = await api_client.post("/api/v1/documents", files=files, data=data, headers=headers)
    assert resp1.status_code == 202
    doc_id_1 = resp1.json()["data"]["document_id"]
    job_id_1 = resp1.json()["data"]["job_id"]

    # 2nd call with same idempotency key
    files2 = {"file": ("test.pdf", VALID_PDF_BYTES, "application/pdf")}
    data2 = {"title": "Idempotent upload", "type": "QUY_DINH", "scope": "PUBLIC"}
    resp2 = await api_client.post("/api/v1/documents", files=files2, data=data2, headers=headers)
    assert resp2.status_code == 202
    assert resp2.json()["data"]["document_id"] == doc_id_1
    assert resp2.json()["data"]["job_id"] == job_id_1
