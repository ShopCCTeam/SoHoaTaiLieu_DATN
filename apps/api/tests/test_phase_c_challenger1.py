"""Phase C Challenger 1 Empirical Stress Testing and Invariant Verification Suite.

Tests cover:
1. Version approval invariants.
2. OCR block review APIs.
3. Edge cases: empty text, zero confidence score, bounding boxes.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.ocr_block import OCRBlock
from app.models.ocr_page import OCRPage
from app.models.user import User
from app.services.ocr_engine import (
    OCR_CONFIDENCE_THRESHOLD,
    OcrBlockResult,
    OcrEngineService,
    OcrEngineStrategy,
    OcrPageResult,
)
from tests.conftest import auth_headers_for

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def phase_c_ocr_setup(db_session_factory, staff_user: User) -> dict[str, str]:
    """Helper fixture creating a multi-page document version with clean & suspicious blocks."""
    doc_id = "doc_phase_c_chal1"
    ver_id = "ver_phase_c_chal1"
    page1_id = "page_c_chal1_p1"
    page2_id = "page_c_chal1_p2"
    block_susp1 = "blk_c_suspicious_01"
    block_susp2 = "blk_c_suspicious_02"
    block_clean1 = "blk_c_clean_01"
    block_clean2 = "blk_c_clean_02"

    async with db_session_factory() as session:
        doc = Document(
            id=doc_id,
            title="Quyết định Thử nghiệm Phase C OCR",
            type="QUYET_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
        )
        ver = DocumentVersion(
            id=ver_id,
            document_id=doc_id,
            version_number=1,
            status="DRAFT",
            file_url="/storage/phase_c_test.pdf",
            file_size=4096,
            checksum="checksum_phase_c_chal1",
            ocr_status="SUCCEEDED",
            requires_review=True,
            created_by=staff_user.id,
        )

        # Page 1: 1 clean, 1 suspicious
        p1 = OCRPage(
            id=page1_id,
            version_id=ver_id,
            page_number=1,
            width=612,
            height=792,
            status="COMPLETED",
            block_count=2,
            has_warnings=True,
        )
        b_susp1 = OCRBlock(
            id=block_susp1,
            version_id=ver_id,
            page_id=page1_id,
            page_number=1,
            block_index=0,
            text_content="CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM (mờ nét)",
            confidence=0.60,
            bbox=[50.0, 720.0, 550.0, 740.0],
            requires_review=True,
            review_status="PENDING",
            original_text="CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM (mờ nét)",
        )
        b_clean1 = OCRBlock(
            id=block_clean1,
            version_id=ver_id,
            page_id=page1_id,
            page_number=1,
            block_index=1,
            text_content="Độc lập - Tự do - Hạnh phúc",
            confidence=0.96,
            bbox=[180.0, 690.0, 420.0, 710.0],
            requires_review=False,
            review_status="APPROVED",
            original_text="Độc lập - Tự do - Hạnh phúc",
        )

        # Page 2: 1 clean, 1 suspicious
        p2 = OCRPage(
            id=page2_id,
            version_id=ver_id,
            page_number=2,
            width=612,
            height=792,
            status="COMPLETED",
            block_count=2,
            has_warnings=True,
        )
        b_susp2 = OCRBlock(
            id=block_susp2,
            version_id=ver_id,
            page_id=page2_id,
            page_number=2,
            block_index=0,
            text_content="Điều 1: Khen thưởng sinh viên Nguyễn Văn A (nhiễu)",
            confidence=0.72,
            bbox=[60.0, 600.0, 500.0, 620.0],
            requires_review=True,
            review_status="PENDING",
            original_text="Điều 1: Khen thưởng sinh viên Nguyễn Văn A (nhiễu)",
        )
        b_clean2 = OCRBlock(
            id=block_clean2,
            version_id=ver_id,
            page_id=page2_id,
            page_number=2,
            block_index=1,
            text_content="Điều 2: Quyết định có hiệu lực kể từ ngày ký",
            confidence=0.99,
            bbox=[60.0, 550.0, 500.0, 570.0],
            requires_review=False,
            review_status="APPROVED",
            original_text="Điều 2: Quyết định có hiệu lực kể từ ngày ký",
        )

        session.add_all([doc, ver, p1, p2, b_susp1, b_clean1, b_susp2, b_clean2])
        await session.commit()

    return {
        "doc_id": doc_id,
        "ver_id": ver_id,
        "page1_id": page1_id,
        "page2_id": page2_id,
        "block_susp1": block_susp1,
        "block_susp2": block_susp2,
        "block_clean1": block_clean1,
        "block_clean2": block_clean2,
    }


# ============================================================================
# 1. APPROVAL INVARIANT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_approval_invariant_returns_409_when_pending_suspicious_blocks_exist(
    api_client: AsyncClient,
    staff_user: User,
    phase_c_ocr_setup: dict[str, str],
) -> None:
    """Invariant 1: Document version with pending suspicious blocks
    MUST fail approval with 409 Conflict.
    """
    doc_id = phase_c_ocr_setup["doc_id"]
    ver_id = phase_c_ocr_setup["ver_id"]
    headers = auth_headers_for(staff_user)

    # Attempt to approve
    resp = await api_client.post(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/approve",
        headers=headers,
    )

    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == "CONFLICT"
    assert "block OCR nghi ngờ chưa được kiểm tra" in body["detail"]
    assert "2" in body["detail"]  # Exactly 2 pending suspicious blocks


@pytest.mark.asyncio
async def test_approval_invariant_returns_409_when_ocr_not_succeeded(
    api_client: AsyncClient,
    staff_user: User,
    db_session_factory,
) -> None:
    """Invariant 2: Document version with ocr_status != 'SUCCEEDED'
    MUST fail approval with 409 Conflict.
    """
    doc_id = "doc_ocr_pending_status"
    ver_id = "ver_ocr_pending_status"
    async with db_session_factory() as session:
        doc = Document(
            id=doc_id,
            title="Tài liệu OCR đang chạy",
            type="QUYET_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
        )
        ver = DocumentVersion(
            id=ver_id,
            document_id=doc_id,
            version_number=1,
            status="DRAFT",
            file_url="/storage/pending.pdf",
            file_size=1024,
            checksum="checksum_pending",
            ocr_status="PROCESSING",
            requires_review=False,
            created_by=staff_user.id,
        )
        session.add_all([doc, ver])
        await session.commit()

    headers = auth_headers_for(staff_user)
    resp = await api_client.post(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/approve",
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "CONFLICT"
    assert "ocr_status == 'SUCCEEDED'" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approval_succeeds_only_after_all_suspicious_blocks_reviewed(
    api_client: AsyncClient,
    staff_user: User,
    phase_c_ocr_setup: dict[str, str],
) -> None:
    """Invariant 3: Once all pending suspicious blocks are reviewed, version approval succeeds."""
    doc_id = phase_c_ocr_setup["doc_id"]
    ver_id = phase_c_ocr_setup["ver_id"]
    block_susp1 = phase_c_ocr_setup["block_susp1"]
    block_susp2 = phase_c_ocr_setup["block_susp2"]
    headers = auth_headers_for(staff_user)

    # 1. Review first suspicious block
    resp1 = await api_client.patch(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/blocks/{block_susp1}",
        json={"review_status": "APPROVED"},
        headers=headers,
    )
    assert resp1.status_code == 200

    # Attempt approval - still 1 pending block left
    resp_mid = await api_client.post(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/approve",
        headers=headers,
    )
    assert resp_mid.status_code == 409
    assert "1 block OCR nghi ngờ" in resp_mid.json()["detail"]

    # 2. Review second suspicious block
    resp2 = await api_client.patch(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/blocks/{block_susp2}",
        json={
            "review_status": "CORRECTED",
            "text": "Điều 1: Khen thưởng sinh viên Nguyễn Văn A (đã sửa)",
        },
        headers=headers,
    )
    assert resp2.status_code == 200

    # 3. Approval should now succeed with 200 OK
    resp_app = await api_client.post(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/approve",
        headers=headers,
    )
    assert resp_app.status_code == 200
    assert resp_app.json()["data"]["status"] == "APPROVED"


# ============================================================================
# 2. OCR BLOCK REVIEW APIS & FILTERING
# ============================================================================


@pytest.mark.asyncio
async def test_single_ocr_block_patch_approved_and_corrected(
    api_client: AsyncClient,
    staff_user: User,
    phase_c_ocr_setup: dict[str, str],
) -> None:
    """Test single block review API with APPROVED and CORRECTED status transitions."""
    doc_id = phase_c_ocr_setup["doc_id"]
    ver_id = phase_c_ocr_setup["ver_id"]
    block_susp1 = phase_c_ocr_setup["block_susp1"]
    headers = auth_headers_for(staff_user)

    # Patch block to CORRECTED with text replacement
    new_text = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
    resp = await api_client.patch(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/blocks/{block_susp1}",
        json={"review_status": "CORRECTED", "text": new_text},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == block_susp1
    assert data["review_status"] == "CORRECTED"
    assert data["text_content"] == new_text
    assert data["edited_text"] == new_text
    assert data["original_text"] == "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM (mờ nét)"
    assert data["reviewed_by"] == staff_user.id


@pytest.mark.asyncio
async def test_batch_review_ocr_accept_all_pending(
    api_client: AsyncClient,
    staff_user: User,
    phase_c_ocr_setup: dict[str, str],
) -> None:
    """Test batch review API with accept_all_pending=True."""
    doc_id = phase_c_ocr_setup["doc_id"]
    ver_id = phase_c_ocr_setup["ver_id"]
    headers = auth_headers_for(staff_user)

    payload = {"accept_all_pending": True, "actions": []}
    resp = await api_client.post(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/batch-review",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["reviewed_count"] == 2
    assert data["remaining_pending_count"] == 0
    assert data["version_requires_review"] is False

    # Verify OCR detail endpoint reflects zero pending reviews
    detail_resp = await api_client.get(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr",
        headers=headers,
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()["data"]
    assert detail_data["pending_reviews"] == 0
    assert detail_data["requires_review"] is False


@pytest.mark.asyncio
async def test_ocr_detail_page_filtering_and_query_params(
    api_client: AsyncClient,
    staff_user: User,
    phase_c_ocr_setup: dict[str, str],
) -> None:
    """Test GET /ocr with page, requires_review, and review_status filters."""
    doc_id = phase_c_ocr_setup["doc_id"]
    ver_id = phase_c_ocr_setup["ver_id"]
    headers = auth_headers_for(staff_user)

    # 1. Filter by page=1
    resp_p1 = await api_client.get(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr?page=1",
        headers=headers,
    )
    assert resp_p1.status_code == 200
    p1_blocks = resp_p1.json()["data"]["blocks"]
    assert len(p1_blocks) == 2
    assert all(b["page_number"] == 1 for b in p1_blocks)

    # 2. Filter by page=2
    resp_p2 = await api_client.get(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr?page=2",
        headers=headers,
    )
    assert resp_p2.status_code == 200
    p2_blocks = resp_p2.json()["data"]["blocks"]
    assert len(p2_blocks) == 2
    assert all(b["page_number"] == 2 for b in p2_blocks)

    # 3. Filter page=1 & requires_review=true
    resp_p1_req = await api_client.get(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr?page=1&requires_review=true",
        headers=headers,
    )
    assert resp_p1_req.status_code == 200
    p1_req_blocks = resp_p1_req.json()["data"]["blocks"]
    assert len(p1_req_blocks) == 1
    assert p1_req_blocks[0]["id"] == phase_c_ocr_setup["block_susp1"]


# ============================================================================
# 3. EDGE CASES & BOUNDARY CONDITIONS
# ============================================================================


def test_edge_case_zero_confidence_score() -> None:
    """Edge Case: Zero confidence score (0.0) MUST flag block as requiring review."""

    class ZeroConfidenceStrategy(OcrEngineStrategy):
        def process_pdf(self, pdf_bytes: bytes) -> list[OcrPageResult]:
            return [
                OcrPageResult(
                    page_number=1,
                    blocks=[
                        OcrBlockResult(
                            page_number=1,
                            block_index=0,
                            text_content="Unreadable zero confidence noise block",
                            confidence=0.0,
                            bbox=[0.0, 0.0, 100.0, 20.0],
                        ),
                    ],
                )
            ]

    service = OcrEngineService(
        primary_engine=ZeroConfidenceStrategy(),
        confidence_threshold=OCR_CONFIDENCE_THRESHOLD,
    )
    pages = service.process_pdf(b"dummy_bytes")
    assert len(pages) == 1
    page = pages[0]
    assert page.has_warnings is True
    assert len(page.blocks) == 1
    zero_block = page.blocks[0]
    assert zero_block.confidence == 0.0
    assert zero_block.requires_review is True
    assert zero_block.review_status == "PENDING"


@pytest.mark.asyncio
async def test_edge_case_empty_text_content(
    api_client: AsyncClient,
    staff_user: User,
    db_session_factory,
) -> None:
    """Edge Case: OCR block with empty text string and updating block text to empty string."""
    doc_id = "doc_ocr_empty_text"
    ver_id = "ver_ocr_empty_text"
    block_id = "blk_ocr_empty_text_01"

    async with db_session_factory() as session:
        doc = Document(
            id=doc_id,
            title="Tài liệu có block rỗng",
            type="KHAC",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
        )
        ver = DocumentVersion(
            id=ver_id,
            document_id=doc_id,
            version_number=1,
            status="DRAFT",
            file_url="/storage/empty_text.pdf",
            file_size=500,
            checksum="checksum_empty",
            ocr_status="SUCCEEDED",
            requires_review=True,
            created_by=staff_user.id,
        )
        empty_block = OCRBlock(
            id=block_id,
            version_id=ver_id,
            page_number=1,
            block_index=0,
            text_content="",  # Empty string text content
            confidence=0.50,
            bbox=[0.0, 0.0, 0.0, 0.0],
            requires_review=True,
            review_status="PENDING",
            original_text="",
        )
        session.add_all([doc, ver, empty_block])
        await session.commit()

    headers = auth_headers_for(staff_user)
    # Patch block text to empty string
    resp = await api_client.patch(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/blocks/{block_id}",
        json={"review_status": "CORRECTED", "text": ""},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["text_content"] == ""
    assert resp.json()["data"]["review_status"] == "CORRECTED"


@pytest.mark.asyncio
async def test_edge_case_out_of_bounds_bounding_boxes(
    api_client: AsyncClient,
    staff_user: User,
    db_session_factory,
) -> None:
    """Edge Case: OCR block with negative, inverted, or huge
    out-of-bounds bounding boxes [x0, y0, x1, y1].
    """
    doc_id = "doc_ocr_oob_bbox"
    ver_id = "ver_ocr_oob_bbox"
    block_neg = "blk_bbox_neg"
    block_inv = "blk_bbox_inv"
    block_huge = "blk_bbox_huge"

    async with db_session_factory() as session:
        doc = Document(
            id=doc_id,
            title="Tài liệu test out of bounds bbox",
            type="QUYET_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
        )
        ver = DocumentVersion(
            id=ver_id,
            document_id=doc_id,
            version_number=1,
            status="DRAFT",
            file_url="/storage/oob.pdf",
            file_size=1000,
            checksum="checksum_oob",
            ocr_status="SUCCEEDED",
            requires_review=False,
            created_by=staff_user.id,
        )

        b1 = OCRBlock(
            id=block_neg,
            version_id=ver_id,
            page_number=1,
            block_index=0,
            text_content="Block tọa độ âm",
            confidence=0.90,
            bbox=[-50.0, -20.0, 100.0, 50.0],  # Negative coords
            requires_review=False,
            review_status="APPROVED",
            original_text="Block tọa độ âm",
        )
        b2 = OCRBlock(
            id=block_inv,
            version_id=ver_id,
            page_number=1,
            block_index=1,
            text_content="Block tọa độ bị đảo ngược x0 > x1",
            confidence=0.92,
            bbox=[500.0, 700.0, 50.0, 600.0],  # Inverted x0 > x1
            requires_review=False,
            review_status="APPROVED",
            original_text="Block tọa độ bị đảo ngược x0 > x1",
        )
        b3 = OCRBlock(
            id=block_huge,
            version_id=ver_id,
            page_number=1,
            block_index=2,
            text_content="Block kích thước vượt trang",
            confidence=0.95,
            bbox=[0.0, 0.0, 99999.0, 99999.0],  # Out of bounds page size
            requires_review=False,
            review_status="APPROVED",
            original_text="Block kích thước vượt trang",
        )

        session.add_all([doc, ver, b1, b2, b3])
        await session.commit()

    headers = auth_headers_for(staff_user)
    resp = await api_client.get(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr",
        headers=headers,
    )
    assert resp.status_code == 200
    blocks = resp.json()["data"]["blocks"]
    assert len(blocks) == 3

    bbox_map = {b["id"]: b["bbox"] for b in blocks}
    assert bbox_map[block_neg] == [-50.0, -20.0, 100.0, 50.0]
    assert bbox_map[block_inv] == [500.0, 700.0, 50.0, 600.0]
    assert bbox_map[block_huge] == [0.0, 0.0, 99999.0, 99999.0]


@pytest.mark.asyncio
async def test_edge_case_non_existent_block_id(
    api_client: AsyncClient,
    staff_user: User,
    phase_c_ocr_setup: dict[str, str],
) -> None:
    """Edge Case: Patching a non-existent block ID returns 404 Not Found."""
    doc_id = phase_c_ocr_setup["doc_id"]
    ver_id = phase_c_ocr_setup["ver_id"]
    headers = auth_headers_for(staff_user)

    resp = await api_client.patch(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/blocks/non_existent_block_9999",
        json={"review_status": "APPROVED"},
        headers=headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"
    assert "OCR block với ID 'non_existent_block_9999' không tồn tại" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_edge_case_student_forbidden_from_ocr_review(
    api_client: AsyncClient,
    student_user: User,
    phase_c_ocr_setup: dict[str, str],
) -> None:
    """Edge Case: Student user attempting OCR review API returns 403 Forbidden."""
    doc_id = phase_c_ocr_setup["doc_id"]
    ver_id = phase_c_ocr_setup["ver_id"]
    block_susp1 = phase_c_ocr_setup["block_susp1"]
    headers = auth_headers_for(student_user)

    # 1. Patch single block
    patch_resp = await api_client.patch(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/blocks/{block_susp1}",
        json={"review_status": "APPROVED"},
        headers=headers,
    )
    assert patch_resp.status_code == 403
    assert patch_resp.json()["code"] == "FORBIDDEN"

    # 2. Batch review
    batch_resp = await api_client.post(
        f"/api/v1/documents/{doc_id}/versions/{ver_id}/ocr/batch-review",
        json={"accept_all_pending": True, "actions": []},
        headers=headers,
    )
    assert batch_resp.status_code == 403
    assert batch_resp.json()["code"] == "FORBIDDEN"
