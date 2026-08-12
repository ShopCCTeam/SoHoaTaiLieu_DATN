"""Integration tests for OCR Review APIs and Document Version Approval Invariants."""

from __future__ import annotations

from base64 import b64decode

import pytest
from httpx import AsyncClient

from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.ocr_block import OCRBlock
from app.models.ocr_page import OCRPage
from app.models.user import User
from app.services.storage import get_storage_service
from tests.conftest import auth_headers_for

PAGE_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9JHvsAAAAASUVORK5CYII="
)
PAGE_IMAGE_KEY = "documents/pages/ver_ocr_api_01/1.png"


@pytest.fixture
async def sample_ocr_version(db_session_factory, staff_user: User) -> tuple[str, str, str, str]:
    """Helper fixture creating a document, version, page, and suspicious/clean OCR blocks."""
    doc_id = "doc_ocr_api_01"
    ver_id = "ver_ocr_api_01"
    page_id = "page_ocr_api_01"
    suspicious_block_id = "block_suspicious_01"
    clean_block_id = "block_clean_01"

    async with db_session_factory() as session:
        doc = Document(
            id=doc_id,
            title="Quyết định OCR Review API Test",
            type="QUYET_DINH",
            status="DRAFT",
            scope="INTERNAL",
            author_id=staff_user.id,
        )
        ver = DocumentVersion(
            id=ver_id,
            document_id=doc_id,
            version_number=1,
            status="DRAFT",
            file_url="/storage/test_ocr.pdf",
            file_size=2048,
            checksum="sha256_checksum_ocr_api",
            ocr_status="SUCCEEDED",
            requires_review=True,  # Has suspicious blocks!
            created_by=staff_user.id,
        )
        ocr_page = OCRPage(
            id=page_id,
            version_id=ver_id,
            page_number=1,
            width=612,
            height=792,
            status="COMPLETED",
            block_count=2,
            has_warnings=True,
            image_key=PAGE_IMAGE_KEY,
        )
        suspicious_block = OCRBlock(
            id=suspicious_block_id,
            version_id=ver_id,
            page_id=page_id,
            page_number=1,
            block_index=0,
            text_content="CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM (nghi ngờ)",
            confidence=0.65,  # < 0.80!
            bbox=[50.0, 700.0, 500.0, 720.0],
            requires_review=True,
            review_status="PENDING",
            original_text="CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM (nghi ngờ)",
        )
        clean_block = OCRBlock(
            id=clean_block_id,
            version_id=ver_id,
            page_id=page_id,
            page_number=1,
            block_index=1,
            text_content="Độc lập - Tự do - Hạnh phúc",
            confidence=0.98,
            bbox=[180.0, 670.0, 420.0, 690.0],
            requires_review=False,
            review_status="APPROVED",
            original_text="Độc lập - Tự do - Hạnh phúc",
        )
        session.add_all([doc, ver, ocr_page, suspicious_block, clean_block])
        await session.commit()

    await get_storage_service().upload_file(PAGE_PNG, PAGE_IMAGE_KEY, content_type="image/png")
    return doc_id, ver_id, suspicious_block_id, clean_block_id


@pytest.mark.asyncio
async def test_get_version_ocr_detail_and_filtering(
    api_client: AsyncClient,
    staff_user: User,
    sample_ocr_version: tuple[str, str, str, str],
) -> None:
    doc_id, ver_id, suspicious_block_id, clean_block_id = sample_ocr_version
    headers = auth_headers_for(staff_user)

    # 1. Get all OCR blocks for version
    url = f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr"
    resp = await api_client.get(url, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["version_id"] == ver_id
    assert data["ocr_status"] == "SUCCEEDED"
    assert data["requires_review"] is True
    assert data["total_blocks"] == 2
    assert data["pending_reviews"] == 1
    assert len(data["blocks"]) == 2

    # 2. Filter by requires_review=true
    resp_req = await api_client.get(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr?requires_review=true",
        headers=headers,
    )
    assert resp_req.status_code == 200
    blocks_req = resp_req.json()["data"]["blocks"]
    assert len(blocks_req) == 1
    assert blocks_req[0]["id"] == suspicious_block_id

    # 3. Filter by review_status=APPROVED
    resp_app = await api_client.get(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr?review_status=APPROVED",
        headers=headers,
    )
    assert resp_app.status_code == 200
    blocks_app = resp_app.json()["data"]["blocks"]
    assert len(blocks_app) == 1
    assert blocks_app[0]["id"] == clean_block_id


@pytest.mark.asyncio
async def test_get_ocr_page_image_with_scope_checked_backend_proxy(
    api_client: AsyncClient,
    staff_user: User,
    sample_ocr_version: tuple[str, str, str, str],
) -> None:
    """Page image bytes are returned only after document scope authorization."""
    doc_id, ver_id, _, _ = sample_ocr_version

    response = await api_client.get(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/pages/1/image",
        headers=auth_headers_for(staff_user),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.content == PAGE_PNG


@pytest.mark.asyncio
async def test_get_ocr_page_image_rejects_user_outside_document_scope(
    api_client: AsyncClient,
    student_user: User,
    sample_ocr_version: tuple[str, str, str, str],
) -> None:
    """Storage cannot bypass document scope enforced by the API boundary."""
    doc_id, ver_id, _, _ = sample_ocr_version

    response = await api_client.get(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/pages/1/image",
        headers=auth_headers_for(student_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_single_ocr_block_correct_and_approve(
    api_client: AsyncClient,
    staff_user: User,
    sample_ocr_version: tuple[str, str, str, str],
) -> None:
    doc_id, ver_id, suspicious_block_id, _ = sample_ocr_version
    headers = auth_headers_for(staff_user)

    # Patch suspicious block to CORRECTED
    payload = {
        "review_status": "CORRECTED",
        "text": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM (đã hiệu chỉnh)",
    }
    resp = await api_client.patch(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/blocks/{suspicious_block_id}",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    block_data = resp.json()["data"]
    assert block_data["review_status"] == "CORRECTED"
    assert block_data["text_content"] == "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM (đã hiệu chỉnh)"
    assert block_data["original_text"] == "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM (nghi ngờ)"
    assert block_data["reviewed_by"] == staff_user.id

    # Verify version requires_review is now False because 0 pending suspicious blocks remain
    resp_ocr = await api_client.get(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr", headers=headers
    )
    assert resp_ocr.json()["data"]["requires_review"] is False
    assert resp_ocr.json()["data"]["pending_reviews"] == 0


@pytest.mark.asyncio
async def test_batch_review_accept_all_pending(
    api_client: AsyncClient,
    staff_user: User,
    sample_ocr_version: tuple[str, str, str, str],
) -> None:
    doc_id, ver_id, _, _ = sample_ocr_version
    headers = auth_headers_for(staff_user)

    payload = {"accept_all_pending": True, "actions": []}
    resp = await api_client.post(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/batch-review",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["reviewed_count"] == 1
    assert data["remaining_pending_count"] == 0
    assert data["version_requires_review"] is False


@pytest.mark.asyncio
async def test_approval_invariant_assertion_prevents_unreviewed_approval(
    api_client: AsyncClient,
    staff_user: User,
    sample_ocr_version: tuple[str, str, str, str],
) -> None:
    """Test approval fails with 409 Conflict when suspicious pending blocks exist."""
    doc_id, ver_id, suspicious_block_id, _ = sample_ocr_version
    headers = auth_headers_for(staff_user)

    # 1. Attempt to approve version while suspicious block is PENDING -> 409 Conflict
    resp_conflict = await api_client.post(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/approve",
        headers=headers,
    )
    assert resp_conflict.status_code == 409
    assert resp_conflict.json()["code"] == "CONFLICT"
    assert "block OCR nghi ngờ chưa được kiểm tra" in resp_conflict.json()["detail"]

    # 2. Review the suspicious block
    patch_resp = await api_client.patch(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/blocks/{suspicious_block_id}",
        json={"review_status": "APPROVED"},
        headers=headers,
    )
    assert patch_resp.status_code == 200

    # 3. Now approval should succeed
    resp_approve = await api_client.post(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/approve",
        headers=headers,
    )
    assert resp_approve.status_code == 200
    assert resp_approve.json()["data"]["status"] == "APPROVED"
