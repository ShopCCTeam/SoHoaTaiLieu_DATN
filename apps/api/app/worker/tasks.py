"""Celery Background Tasks for Document Processing Pipeline."""

from __future__ import annotations

import asyncio
import concurrent.futures
from datetime import UTC, datetime
from typing import Any

from celery import shared_task  # type: ignore[import-untyped]
from sqlalchemy import select
from structlog import get_logger

from app.db.session import get_session_factory
from app.models.document_version import DocumentVersion
from app.models.job import Job

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
    """Async task for processing uploaded PDF document version.

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

            # 2. Simulate processing / metadata extraction (Step A -> Step D)
            job.progress = 50
            await session.commit()

            # 3. Complete processing
            job.progress = 100
            job.status = "SUCCEEDED"
            job.finished_at = datetime.now(UTC)

            version.ocr_status = "SUCCEEDED"
            version.status = "UNDER_REVIEW"
            await session.commit()

            logger.info("process_document_task_succeeded", job_id=job_id, version_id=version_id)
            return {"status": "SUCCEEDED", "job_id": job_id, "version_id": version_id}
        except Exception as exc:
            logger.exception("process_document_task_failed", job_id=job_id, error=str(exc))
            job.status = "FAILED"
            job.error = str(exc)
            job.finished_at = datetime.now(UTC)

            version.ocr_status = "FAILED"
            await session.commit()
            return {"status": "FAILED", "error": str(exc)}
