"""Unit & integration tests for OCR Engine Service, ORM Models, and Celery Tasks."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.job import Job
from app.models.ocr_block import OCRBlock
from app.models.ocr_page import OCRPage
from app.models.user import User
from app.services.ocr_engine import (
    OCR_CONFIDENCE_THRESHOLD,
    OcrBlockResult,
    OcrEngineService,
    OcrEngineStrategy,
    OcrPageResult,
    PaddleOcrStrategy,
    TesseractOcrStrategy,
)
from app.worker.tasks import _async_process_document, process_document_task


class FailingStrategy(OcrEngineStrategy):
    """Strategy that always raises an error to test fallback chain."""

    def process_pdf(self, pdf_bytes: bytes) -> list[OcrPageResult]:
        raise RuntimeError("Simulated OCR engine failure")


def test_ocr_engine_service_strategy_fallback() -> None:
    """Test Strategy pattern fallback chain from primary -> fallback -> mock."""
    service = OcrEngineService(
        primary_engine=FailingStrategy(),
        fallback_engine=FailingStrategy(),
        confidence_threshold=0.80,
    )
    pages = service.process_pdf(b"%PDF-1.4 sample content")

    assert len(pages) > 0
    assert len(pages[0].blocks) > 0
    # Primary & fallback failed, mock strategy returned results
    first_block = pages[0].blocks[0]
    assert first_block.confidence >= 0.80
    assert first_block.requires_review is False
    assert first_block.review_status == "APPROVED"


def test_ocr_confidence_thresholding_rules() -> None:
    """Test confidence thresholding: < 0.80 requires_review=True, >= 0.80 requires_review=False."""

    class CustomMockStrategy(OcrEngineStrategy):
        def process_pdf(self, pdf_bytes: bytes) -> list[OcrPageResult]:
            return [
                OcrPageResult(
                    page_number=1,
                    blocks=[
                        OcrBlockResult(
                            page_number=1,
                            block_index=0,
                            text_content="High confidence block",
                            confidence=0.95,
                            bbox=[10.0, 10.0, 100.0, 20.0],
                        ),
                        OcrBlockResult(
                            page_number=1,
                            block_index=1,
                            text_content="Low confidence block",
                            confidence=0.75,  # Below 0.80!
                            bbox=[10.0, 30.0, 100.0, 40.0],
                        ),
                    ],
                )
            ]

    service = OcrEngineService(
        primary_engine=CustomMockStrategy(),
        confidence_threshold=OCR_CONFIDENCE_THRESHOLD,
    )
    pages = service.process_pdf(b"dummy")

    assert len(pages) == 1
    page = pages[0]
    assert page.has_warnings is True
    assert page.block_count == 2

    high_conf_block = page.blocks[0]
    assert high_conf_block.requires_review is False
    assert high_conf_block.review_status == "APPROVED"

    low_conf_block = page.blocks[1]
    assert low_conf_block.requires_review is True
    assert low_conf_block.review_status == "PENDING"


def test_paddleocr_and_tesseract_error_handling() -> None:
    """Test that PaddleOCR and Tesseract strategies handle missing packages cleanly."""
    paddle = PaddleOcrStrategy()
    tesseract = TesseractOcrStrategy()

    # When native dependencies are missing, they raise RuntimeError cleanly
    with pytest.raises(RuntimeError):
        paddle.process_pdf(b"pdf_bytes")

    with pytest.raises(RuntimeError):
        tesseract.process_pdf(b"pdf_bytes")


@pytest.mark.asyncio
async def test_celery_process_document_task_integration(
    db_session_factory, staff_user: User
) -> None:
    """Test process_document_task persists OCRPage & OCRBlock records into DB."""
    async with db_session_factory() as session:
        doc = Document(
            id="doc_ocr_task_01",
            title="Quyết định OCR Task",
            type="QUYET_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
        )
        ver = DocumentVersion(
            id="ver_ocr_task_01",
            document_id="doc_ocr_task_01",
            version_number=1,
            status="DRAFT",
            file_url="/storage/documents/raw/doc_ocr_task_01/ver_ocr_task_01.pdf",
            file_size=1024,
            checksum="abc123hash",
            ocr_status="QUEUED",
            created_by=staff_user.id,
        )
        job = Job(
            id="job_ocr_task_01",
            type="OCR",
            status="QUEUED",
            target_document_id="doc_ocr_task_01",
            target_version_id="ver_ocr_task_01",
            created_by=staff_user.id,
        )
        session.add_all([doc, ver, job])
        await session.commit()

    # Run async pipeline
    res = await _async_process_document("job_ocr_task_01", "ver_ocr_task_01")
    assert res["status"] == "SUCCEEDED"

    # Verify DB persistence
    async with db_session_factory() as session:
        updated_ver = await session.get(DocumentVersion, "ver_ocr_task_01")
        assert updated_ver is not None
        assert updated_ver.ocr_status == "SUCCEEDED"
        assert updated_ver.status == "UNDER_REVIEW"

        pages_res = await session.execute(
            select(OCRPage).where(OCRPage.version_id == "ver_ocr_task_01")
        )
        pages = pages_res.scalars().all()
        assert len(pages) > 0

        blocks_res = await session.execute(
            select(OCRBlock).where(OCRBlock.version_id == "ver_ocr_task_01")
        )
        blocks = blocks_res.scalars().all()
        assert len(blocks) > 0
        for b in blocks:
            assert isinstance(b.bbox, list)
            assert len(b.bbox) == 4
            assert b.original_text is not None


@pytest.mark.asyncio
async def test_celery_task_wrapper(staff_user: User, db_session_factory) -> None:
    """Test process_document_task celery wrapper entrypoint."""
    async with db_session_factory() as session:
        doc = Document(
            id="doc_ocr_wrap_01",
            title="Tài liệu test task wrapper",
            type="KHAC",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
        )
        ver = DocumentVersion(
            id="ver_ocr_wrap_01",
            document_id="doc_ocr_wrap_01",
            version_number=1,
            status="DRAFT",
            file_url="/storage/wrap.pdf",
            file_size=500,
            checksum="hash123",
            ocr_status="QUEUED",
            created_by=staff_user.id,
        )
        job = Job(
            id="job_ocr_wrap_01",
            type="OCR",
            status="QUEUED",
            target_document_id="doc_ocr_wrap_01",
            target_version_id="ver_ocr_wrap_01",
            created_by=staff_user.id,
        )
        session.add_all([doc, ver, job])
        await session.commit()

    # Call task
    result = process_document_task("job_ocr_wrap_01", "ver_ocr_wrap_01")
    assert result["status"] == "SUCCEEDED"
