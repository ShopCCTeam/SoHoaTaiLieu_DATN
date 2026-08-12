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


VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\x0dIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.mark.asyncio
async def test_upload_valid_jpeg_returns_202(api_client: AsyncClient, staff_user: User) -> None:
    headers = auth_headers_for(staff_user)
    headers["Idempotency-Key"] = "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b"
    files = {"file": ("thong_bao.jpg", VALID_JPEG_BYTES, "image/jpeg")}
    data = {"title": "Thông báo dạng ảnh", "type": "THONG_BAO", "scope": "PUBLIC"}

    response = await api_client.post("/api/v1/documents", files=files, data=data, headers=headers)

    assert response.status_code == 202
    assert response.json()["data"]["status"] in {"QUEUED", "SUCCEEDED"}

    document_id = response.json()["data"]["document_id"]
    versions_response = await api_client.get(
        f"/api/v1/documents/{document_id}/versions", headers=headers
    )
    assert versions_response.status_code == 200
    version_id = versions_response.json()["data"][0]["id"]

    ocr_response = await api_client.get(
        f"/api/v1/documents/{document_id}/versions/{version_id}/ocr", headers=headers
    )
    assert ocr_response.status_code == 200
    ocr_data = ocr_response.json()["data"]
    assert len(ocr_data["blocks"]) > 0
    assert ocr_data["pages"][0]["image_key"] == f"documents/pages/{version_id}/1.png"


@pytest.mark.asyncio
async def test_upload_valid_png_returns_202(api_client: AsyncClient, staff_user: User) -> None:
    headers = auth_headers_for(staff_user)
    headers["Idempotency-Key"] = "f6a7b8c9-d0e1-2f3a-4b5c-6d7e8f9a0b1c"
    files = {"file": ("quy_dinh.png", VALID_PNG_BYTES, "image/png")}
    data = {"title": "Quy định dạng ảnh", "type": "QUY_DINH", "scope": "PUBLIC"}

    response = await api_client.post("/api/v1/documents", files=files, data=data, headers=headers)

    assert response.status_code == 202
    assert response.json()["data"]["status"] in {"QUEUED", "SUCCEEDED"}

    document_id = response.json()["data"]["document_id"]
    versions_response = await api_client.get(
        f"/api/v1/documents/{document_id}/versions", headers=headers
    )
    assert versions_response.status_code == 200
    version_id = versions_response.json()["data"][0]["id"]

    ocr_response = await api_client.get(
        f"/api/v1/documents/{document_id}/versions/{version_id}/ocr", headers=headers
    )
    assert ocr_response.status_code == 200
    ocr_data = ocr_response.json()["data"]
    assert len(ocr_data["blocks"]) > 0
    assert ocr_data["pages"][0]["image_key"] == f"documents/pages/{version_id}/1.png"

    image_response = await api_client.get(
        f"/api/v1/documents/{document_id}/versions/{version_id}/ocr/pages/1/image",
        headers=headers,
    )
    assert image_response.status_code == 200
    assert image_response.content.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.asyncio
async def test_upload_png_larger_than_10mb_rejected(
    api_client: AsyncClient, staff_user: User
) -> None:
    headers = auth_headers_for(staff_user)
    headers["Idempotency-Key"] = "9a0b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d"
    oversized_png = b"\x89PNG\r\n\x1a\n" + b"X" * (10 * 1024 * 1024)
    files = {"file": ("vuot_gioi_han.png", oversized_png, "image/png")}
    data = {"title": "Ảnh quá cỡ", "type": "THONG_BAO", "scope": "PUBLIC"}

    response = await api_client.post("/api/v1/documents", files=files, data=data, headers=headers)

    assert response.status_code == 413
    assert response.json()["code"] == "FILE_SIZE_EXCEEDED"


@pytest.mark.asyncio
async def test_upload_fake_jpeg_renamed_from_exe_rejected(
    api_client: AsyncClient, staff_user: User
) -> None:
    headers = auth_headers_for(staff_user)
    headers["Idempotency-Key"] = "a7b8c9d0-e1f2-3a4b-5c6d-7e8f9a0b1c2d"
    fake_executable = b"MZ\x90\x00this-is-not-an-image"
    files = {"file": ("gia_mao.jpg", fake_executable, "image/jpeg")}
    data = {"title": "Tệp giả đổi đuôi", "type": "THONG_BAO", "scope": "PUBLIC"}

    response = await api_client.post("/api/v1/documents", files=files, data=data, headers=headers)

    assert response.status_code == 415
    assert response.json()["code"] == "INVALID_FILE_TYPE"
