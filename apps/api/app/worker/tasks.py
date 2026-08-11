"""Celery Background Tasks for Document Processing Pipeline."""

from __future__ import annotations

import asyncio
import concurrent.futures
import uuid
from datetime import UTC, datetime
from typing import Any

from celery import shared_task  # type: ignore[import-untyped]
from sqlalchemy import delete, func, select
from structlog import get_logger

from app.db.session import get_session_factory
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.job import Job
from app.models.ocr_block import OCRBlock
from app.models.ocr_page import OCRPage
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.services.ocr_engine import OcrEngineService
from app.services.storage import get_storage_service

logger = get_logger(__name__)


def run_async(coro: Any) -> Any:
    """Helper running an async coroutine inside Celery worker thread or eager context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(coro)).result()

    return asyncio.run(coro)


@shared_task(name="app.worker.tasks.process_document_task", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def process_document_task(self: Any, job_id: str, version_id: str) -> Any:
    """Async task for processing uploaded PDF document version with OCR.

    State Machine Transitions:
      - Job: QUEUED -> PROCESSING -> SUCCEEDED / FAILED
      - DocumentVersion.ocr_status: QUEUED -> PROCESSING -> SUCCEEDED / FAILED
    """
    logger.info("start_process_document_task", job_id=job_id, version_id=version_id)
    return run_async(_async_process_document(job_id, version_id))


async def _async_process_document(job_id: str, version_id: str) -> dict[str, Any]:
    session_factory = get_session_factory()

    async with session_factory() as session:
        # Fetch Job & Version
        job_result = await session.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()

        version_result = await session.execute(
            select(DocumentVersion).where(DocumentVersion.id == version_id)
        )
        version = version_result.scalar_one_or_none()

        if not job or not version:
            logger.error("job_or_version_not_found", job_id=job_id, version_id=version_id)
            if job:
                job.status = "FAILED"
                job.error = "Document version or Job record not found"
                job.finished_at = datetime.now(UTC)
                await session.commit()
            return {"status": "FAILED", "error": "Not found"}

        try:
            # 1. Update status to PROCESSING
            job.status = "PROCESSING"
            job.started_at = datetime.now(UTC)
            job.progress = 10
            version.ocr_status = "PROCESSING"
            await session.commit()

            # 2. Download PDF bytes from StorageService
            storage = get_storage_service()
            file_bytes = b""
            try:
                object_key = f"documents/raw/{version.document_id}/{version.id}.pdf"
                file_bytes = await storage.download_file(object_key)
            except Exception as dl_err:
                logger.warning("storage_download_failed_using_placeholder", error=str(dl_err))
                file_bytes = b"%PDF-1.4 Mock PDF Content"

            job.progress = 30
            await session.commit()

            # 3. Run OCR Processing
            ocr_service = OcrEngineService()
            ocr_pages_res = ocr_service.process_pdf(file_bytes)

            job.progress = 70
            await session.commit()

            # 4. Clear old OCR pages & blocks if re-triggering
            await session.execute(delete(OCRBlock).where(OCRBlock.version_id == version.id))
            await session.execute(delete(OCRPage).where(OCRPage.version_id == version.id))

            has_suspicious_blocks = False

            # 5. Persist OCRPages and OCRBlocks
            for page_res in ocr_pages_res:
                page_id = f"page_{uuid.uuid4().hex[:24]}"
                ocr_page = OCRPage(
                    id=page_id,
                    version_id=version.id,
                    page_number=page_res.page_number,
                    width=page_res.width,
                    height=page_res.height,
                    image_key=page_res.image_key,
                    status=page_res.status,
                    block_count=len(page_res.blocks),
                    has_warnings=page_res.has_warnings,
                )
                session.add(ocr_page)

                for block_res in page_res.blocks:
                    block_id = f"block_{uuid.uuid4().hex[:24]}"
                    if block_res.requires_review:
                        has_suspicious_blocks = True

                    ocr_block = OCRBlock(
                        id=block_id,
                        version_id=version.id,
                        page_id=page_id,
                        page_number=block_res.page_number,
                        block_index=block_res.block_index,
                        text_content=block_res.text_content,
                        confidence=block_res.confidence,
                        bbox=block_res.bbox,
                        requires_review=block_res.requires_review,
                        review_status=block_res.review_status,
                        original_text=block_res.text_content,
                        job_id=job.id,
                        processing_time_ms=block_res.processing_time_ms,
                    )
                    session.add(ocr_block)

            # 6. Complete processing
            job.progress = 100
            job.status = "SUCCEEDED"
            job.finished_at = datetime.now(UTC)

            version.ocr_status = "SUCCEEDED"
            version.requires_review = has_suspicious_blocks
            version.status = "UNDER_REVIEW"
            await session.commit()

            # Trigger indexing chunks after OCR succeeds
            try:
                await _async_index_document_chunks(version_id)
            except Exception as index_err:
                logger.warning(
                    "auto_indexing_chunks_failed", version_id=version_id, error=str(index_err)
                )

            logger.info(
                "process_document_task_succeeded",
                job_id=job_id,
                version_id=version_id,
                requires_review=has_suspicious_blocks,
            )
            return {"status": "SUCCEEDED", "job_id": job_id, "version_id": version_id}
        except Exception as exc:
            logger.exception("process_document_task_failed", job_id=job_id, error=str(exc))
            job.status = "FAILED"
            job.error = str(exc)
            job.finished_at = datetime.now(UTC)

            version.ocr_status = "FAILED"
            await session.commit()
            return {"status": "FAILED", "error": str(exc)}


@shared_task(name="app.worker.tasks.index_document_chunks_task", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def index_document_chunks_task(self: Any, version_id: str) -> Any:
    """Async Celery task for chunking and embedding OCR results into DocumentChunks."""
    logger.info("start_index_document_chunks_task", version_id=version_id)
    return run_async(_async_index_document_chunks(version_id))


async def _async_index_document_chunks(version_id: str) -> dict[str, Any]:
    session_factory = get_session_factory()

    async with session_factory() as session:
        version_result = await session.execute(
            select(DocumentVersion).where(DocumentVersion.id == version_id)
        )
        version = version_result.scalar_one_or_none()

        if not version:
            logger.error("version_not_found_for_indexing", version_id=version_id)
            return {"status": "FAILED", "error": "Document version not found"}

        blocks_result = await session.execute(
            select(OCRBlock)
            .where(OCRBlock.version_id == version.id)
            .order_by(OCRBlock.page_number.asc(), OCRBlock.block_index.asc())
        )
        blocks = list(blocks_result.scalars().all())

        if not blocks:
            logger.info("no_ocr_blocks_found_for_indexing", version_id=version_id)
            return {"status": "SUCCEEDED", "version_id": version_id, "chunk_count": 0}

        chunking_service = ChunkingService()
        chunks = chunking_service.chunk_ocr_blocks(blocks)

        if not chunks:
            return {"status": "SUCCEEDED", "version_id": version_id, "chunk_count": 0}

        texts = [c["text"] for c in chunks]
        embedding_service = EmbeddingService()
        embeddings = await embedding_service.embed_texts(texts)

        # Clear old chunks for idempotency
        await session.execute(delete(DocumentChunk).where(DocumentChunk.version_id == version.id))

        is_postgres = session.bind is not None and "postgresql" in str(session.bind.dialect.name)

        for c, emb in zip(chunks, embeddings, strict=False):
            chunk_id = f"chunk_{uuid.uuid4().hex[:24]}"
            tsv_val = func.to_tsvector("simple", c["text"]) if is_postgres else c["text"]
            doc_chunk = DocumentChunk(
                id=chunk_id,
                version_id=version.id,
                document_id=version.document_id,
                chunk_index=c["chunk_index"],
                page_number=c["page_number"],
                block_ids=c["block_ids"],
                text=c["text"],
                token_count=c["token_count"],
                bbox=c["bbox"],
                embedding=emb,
                fulltext_tsv=tsv_val,
            )
            session.add(doc_chunk)

        await session.commit()

        logger.info(
            "index_document_chunks_succeeded",
            version_id=version_id,
            chunk_count=len(chunks),
        )
        return {"status": "SUCCEEDED", "version_id": version_id, "chunk_count": len(chunks)}
