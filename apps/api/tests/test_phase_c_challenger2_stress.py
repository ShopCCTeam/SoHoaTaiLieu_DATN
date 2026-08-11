"""Phase C Invariant & State Transition Stress Tests by Challenger 2.

Empirical verification suite for:
1. OCR Engine Strategy Pattern & Fallback Chain (Primary -> Fallback -> Mock)
2. Thresholding invariants (boundary values at 0.80, custom threshold)
3. Celery document processing task (`process_document_task` & `_async_process_document`)
4. DB persistence, idempotency / cleanup of re-triggered processing
5. Error state transitions for invalid IDs or OCR failure
6. Migration 0004_ocr_pages_and_blocks schema structural invariants
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from alembic.script import ScriptDirectory
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.job import Job
from app.models.ocr_block import OCRBlock
from app.models.ocr_page import OCRPage
from app.models.user import User
from app.services.ocr_engine import (
    OcrBlockResult,
    OcrEngineService,
    OcrEngineStrategy,
    OcrPageResult,
)
from app.worker.tasks import _async_process_document


class SpyStrategy(OcrEngineStrategy):
    """Strategy that records calls and can fail or succeed on demand."""

    def __init__(
        self,
        should_fail: bool = False,
        return_pages: list[OcrPageResult] | None = None,
    ) -> None:
        self.called = False
        self.should_fail = should_fail
        self.return_pages = return_pages or []

    def process_pdf(self, pdf_bytes: bytes) -> list[OcrPageResult]:
        self.called = True
        if self.should_fail:
            raise RuntimeError("SpyStrategy deliberate failure")
        return self.return_pages


# ---------------------------------------------------------------------------
# 1. OCR ENGINE STRATEGY PATTERN & FALLBACK CHAIN TESTS
# ---------------------------------------------------------------------------


def test_ocr_strategy_primary_success_bypasses_fallback() -> None:
    """Verify that when primary engine succeeds, fallback engine is NOT invoked."""
    primary = SpyStrategy(
        should_fail=False,
        return_pages=[
            OcrPageResult(
                page_number=1,
                blocks=[
                    OcrBlockResult(
                        page_number=1,
                        block_index=0,
                        text_content="Primary Text",
                        confidence=0.90,
                        bbox=[0.0, 0.0, 10.0, 10.0],
                    )
                ],
            )
        ],
    )
    fallback = SpyStrategy(should_fail=False)
    service = OcrEngineService(primary_engine=primary, fallback_engine=fallback)

    pages = service.process_pdf(b"dummy pdf bytes")

    assert primary.called is True
    assert fallback.called is False
    assert len(pages) == 1
    assert pages[0].blocks[0].text_content == "Primary Text"


def test_ocr_strategy_primary_fails_fallback_succeeds() -> None:
    """Verify that when primary engine fails, fallback engine is called and used."""
    primary = SpyStrategy(should_fail=True)
    fallback = SpyStrategy(
        should_fail=False,
        return_pages=[
            OcrPageResult(
                page_number=1,
                blocks=[
                    OcrBlockResult(
                        page_number=1,
                        block_index=0,
                        text_content="Fallback Text",
                        confidence=0.85,
                        bbox=[5.0, 5.0, 15.0, 15.0],
                    )
                ],
            )
        ],
    )
    service = OcrEngineService(primary_engine=primary, fallback_engine=fallback)

    pages = service.process_pdf(b"dummy pdf bytes")

    assert primary.called is True
    assert fallback.called is True
    assert len(pages) == 1
    assert pages[0].blocks[0].text_content == "Fallback Text"


def test_ocr_strategy_all_fail_triggers_mock_fallback() -> None:
    """Verify that when both primary and fallback engines fail, mock strategy handles request."""
    primary = SpyStrategy(should_fail=True)
    fallback = SpyStrategy(should_fail=True)
    service = OcrEngineService(primary_engine=primary, fallback_engine=fallback)

    pages = service.process_pdf(b"dummy pdf bytes")

    assert primary.called is True
    assert fallback.called is True
    assert len(pages) > 0
    assert len(pages[0].blocks) > 0


@pytest.mark.parametrize(
    "confidence, expected_requires_review, expected_status",
    [
        (0.799, True, "PENDING"),
        (0.800, False, "APPROVED"),
        (0.801, False, "APPROVED"),
        (0.000, True, "PENDING"),
        (1.000, False, "APPROVED"),
    ],
)
def test_ocr_confidence_threshold_boundary_invariants(
    confidence: float, expected_requires_review: bool, expected_status: str
) -> None:
    """Test exact boundary condition behavior for OCR_CONFIDENCE_THRESHOLD (0.80)."""
    custom_strategy = SpyStrategy(
        should_fail=False,
        return_pages=[
            OcrPageResult(
                page_number=1,
                blocks=[
                    OcrBlockResult(
                        page_number=1,
                        block_index=0,
                        text_content="Boundary Test Text",
                        confidence=confidence,
                        bbox=[0.0, 0.0, 100.0, 100.0],
                    )
                ],
            )
        ],
    )
    service = OcrEngineService(primary_engine=custom_strategy, confidence_threshold=0.80)
    pages = service.process_pdf(b"test pdf")

    block = pages[0].blocks[0]
    assert block.requires_review is expected_requires_review
    assert block.review_status == expected_status
    assert pages[0].has_warnings is expected_requires_review


def test_ocr_custom_confidence_threshold_override() -> None:
    """Verify custom confidence threshold parameter is respected."""
    custom_strategy = SpyStrategy(
        should_fail=False,
        return_pages=[
            OcrPageResult(
                page_number=1,
                blocks=[
                    OcrBlockResult(
                        page_number=1,
                        block_index=0,
                        text_content="High Threshold Test",
                        confidence=0.85,  # Above 0.80, but below custom 0.90!
                        bbox=[0.0, 0.0, 50.0, 50.0],
                    )
                ],
            )
        ],
    )
    service = OcrEngineService(primary_engine=custom_strategy, confidence_threshold=0.90)
    pages = service.process_pdf(b"test pdf")

    block = pages[0].blocks[0]
    assert block.requires_review is True
    assert block.review_status == "PENDING"
    assert pages[0].has_warnings is True


# ---------------------------------------------------------------------------
# 2. CELERY DOCUMENT OCR TASK STRESS & INVARIANT TESTS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_document_task_nonexistent_job_or_version(
    db_session_factory,
) -> None:
    """Verify task gracefully fails when job_id or version_id is invalid/missing."""
    res = await _async_process_document("nonexistent_job_id", "nonexistent_version_id")
    assert res["status"] == "FAILED"
    assert res["error"] == "Not found"


@pytest.mark.asyncio
async def test_process_document_task_nonexistent_version_updates_job_failed(
    db_session_factory, staff_user: User
) -> None:
    """Verify job record is marked FAILED when version_id does not exist."""
    async with db_session_factory() as session:
        job = Job(
            id="job_missing_ver_01",
            type="OCR",
            status="QUEUED",
            target_document_id="doc_dummy",
            target_version_id="ver_dummy_missing",
            created_by=staff_user.id,
        )
        session.add(job)
        await session.commit()

    res = await _async_process_document("job_missing_ver_01", "ver_dummy_missing")
    assert res["status"] == "FAILED"

    async with db_session_factory() as session:
        updated_job = await session.get(Job, "job_missing_ver_01")
        assert updated_job is not None
        assert updated_job.status == "FAILED"
        assert updated_job.error is not None


@pytest.mark.asyncio
async def test_process_document_task_idempotency_clears_old_pages_and_blocks(
    db_session_factory, staff_user: User
) -> None:
    """Verify re-running process_document_task cleans up existing OCRPage & OCRBlock records."""
    async with db_session_factory() as session:
        doc = Document(
            id="doc_idempotent_01",
            title="Idempotency Document",
            type="QUYET_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
        )
        ver = DocumentVersion(
            id="ver_idempotent_01",
            document_id="doc_idempotent_01",
            version_number=1,
            status="DRAFT",
            file_url="/storage/idempotent.pdf",
            file_size=1024,
            checksum="hash_idempotent",
            ocr_status="QUEUED",
            created_by=staff_user.id,
        )
        job = Job(
            id="job_idempotent_01",
            type="OCR",
            status="QUEUED",
            target_document_id="doc_idempotent_01",
            target_version_id="ver_idempotent_01",
            created_by=staff_user.id,
        )
        session.add_all([doc, ver, job])
        await session.commit()

    # Run 1st execution
    res1 = await _async_process_document("job_idempotent_01", "ver_idempotent_01")
    assert res1["status"] == "SUCCEEDED"

    async with db_session_factory() as session:
        pages1 = (
            (
                await session.execute(
                    select(OCRPage).where(OCRPage.version_id == "ver_idempotent_01")
                )
            )
            .scalars()
            .all()
        )
        blocks1 = (
            (
                await session.execute(
                    select(OCRBlock).where(OCRBlock.version_id == "ver_idempotent_01")
                )
            )
            .scalars()
            .all()
        )
        page_ids_run1 = [p.id for p in pages1]
        block_ids_run1 = [b.id for b in blocks1]

    # Reset job state and Run 2nd execution
    async with db_session_factory() as session:
        job_db = await session.get(Job, "job_idempotent_01")
        assert job_db is not None
        job_db.status = "QUEUED"
        await session.commit()

    res2 = await _async_process_document("job_idempotent_01", "ver_idempotent_01")
    assert res2["status"] == "SUCCEEDED"

    async with db_session_factory() as session:
        pages2 = (
            (
                await session.execute(
                    select(OCRPage).where(OCRPage.version_id == "ver_idempotent_01")
                )
            )
            .scalars()
            .all()
        )
        blocks2 = (
            (
                await session.execute(
                    select(OCRBlock).where(OCRBlock.version_id == "ver_idempotent_01")
                )
            )
            .scalars()
            .all()
        )
        page_ids_run2 = [p.id for p in pages2]
        block_ids_run2 = [b.id for b in blocks2]

        # Verify old IDs were completely deleted and replaced with new ones (no accumulation!)
        assert len(pages2) == len(pages1)
        assert len(blocks2) == len(blocks1)
        for old_p_id in page_ids_run1:
            assert old_p_id not in page_ids_run2
        for old_b_id in block_ids_run1:
            assert old_b_id not in block_ids_run2


# ---------------------------------------------------------------------------
# 3. DB MIGRATION 0004 REVISION AND INVARIANT CHECKS
# ---------------------------------------------------------------------------


def test_migration_0004_revision_chain_invariants() -> None:
    """Verify 0004 revision metadata and dependency chain."""
    here = Path(__file__).parent
    alembic_path = here.parent / "alembic"
    script_dir = ScriptDirectory(str(alembic_path))

    revisions = {r.revision: r for r in script_dir.walk_revisions()}
    assert "0004" in revisions
    rev_0004 = revisions["0004"]
    assert rev_0004.down_revision == "0003"
    assert script_dir.get_current_head() in ("0005", "0006")


def test_ocr_models_table_structure_and_foreign_keys() -> None:
    """Verify ORM models match migration 0004 specification."""
    assert OCRPage.__tablename__ == "ocr_pages"
    assert OCRBlock.__tablename__ == "ocr_blocks"

    # Verify relationships and fields on OCRPage
    assert hasattr(OCRPage, "version_id")
    assert hasattr(OCRPage, "page_number")
    assert hasattr(OCRPage, "has_warnings")
    assert hasattr(OCRPage, "block_count")

    # Verify relationships and fields on OCRBlock
    assert hasattr(OCRBlock, "version_id")
    assert hasattr(OCRBlock, "page_id")
    assert hasattr(OCRBlock, "page_number")
    assert hasattr(OCRBlock, "block_index")
    assert hasattr(OCRBlock, "text_content")
    assert hasattr(OCRBlock, "confidence")
    assert hasattr(OCRBlock, "bbox")
    assert hasattr(OCRBlock, "requires_review")
    assert hasattr(OCRBlock, "review_status")
    assert hasattr(OCRBlock, "original_text")
    assert hasattr(OCRBlock, "job_id")
    assert hasattr(OCRBlock, "reviewed_by")
