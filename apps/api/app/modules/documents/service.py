"""Service layer for Document Management."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog import get_logger

from app.core.errors import conflict, idempotency_mismatch
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.job import Job
from app.models.user import User
from app.modules.documents.dependencies import get_allowed_scopes_for_user
from app.modules.documents.schemas import DocumentUpdateSchema
from app.services.storage import get_storage_service
from app.worker.tasks import process_document_task

logger = get_logger(__name__)


async def list_documents(
    session: AsyncSession,
    user: User,
    status: str | None = None,
    doc_type: str | None = None,
    q: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[Sequence[Document], int]:
    """List documents with pagination, filters, and RBAC scope restriction."""
    allowed_scopes = get_allowed_scopes_for_user(user)

    stmt = select(Document).where(
        Document.deleted_at.is_(None),
        Document.scope.in_(allowed_scopes),
    )

    if status:
        stmt = stmt.where(Document.status == status)
    if doc_type:
        stmt = stmt.where(Document.type == doc_type)
    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            (Document.title.ilike(search_pattern)) | (Document.code_number.ilike(search_pattern))
        )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Pagination & Order
    stmt = stmt.order_by(Document.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await session.execute(stmt)
    documents = result.scalars().all()

    return documents, total


async def get_document_by_id(
    session: AsyncSession, document_id: str, include_deleted: bool = False
) -> Document | None:
    """Fetch Document by ID with preloaded versions."""
    stmt = (
        select(Document).options(selectinload(Document.versions)).where(Document.id == document_id)
    )
    if not include_deleted:
        stmt = stmt.where(Document.deleted_at.is_(None))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_document(
    session: AsyncSession,
    user: User,
    file_bytes: bytes,
    checksum: str,
    total_bytes: int,
    idempotency_key: str,
    title: str,
    doc_type: str,
    scope: str,
    code_number: str | None = None,
    issuing_body: str | None = None,
    effective_from: str | None = None,
    effective_to: str | None = None,
    tags: list[str] | None = None,
    change_summary: str | None = None,
    request_id: str = "",
) -> tuple[str, str, str]:
    """Upload new document and start async OCR job."""
    # 1. Check Idempotency Key
    if idempotency_key:
        job_stmt = select(Job).where(Job.idempotency_key == idempotency_key)
        existing_job_res = await session.execute(job_stmt)
        existing_job = existing_job_res.scalar_one_or_none()

        if existing_job:
            if existing_job.target_document_id and existing_job.target_version_id:
                ver_stmt = select(DocumentVersion).where(
                    DocumentVersion.id == existing_job.target_version_id
                )
                ver_res = await session.execute(ver_stmt)
                existing_ver = ver_res.scalar_one_or_none()
                if existing_ver and existing_ver.checksum == checksum:
                    doc_stmt = select(Document).where(
                        Document.id == existing_job.target_document_id
                    )
                    doc_res = await session.execute(doc_stmt)
                    existing_doc = doc_res.scalar_one_or_none()
                    if existing_doc and existing_doc.title == title:
                        return (
                            existing_job.target_document_id,
                            existing_job.id,
                            existing_job.status,
                        )
            raise idempotency_mismatch(request_id=request_id)

    doc_id = f"doc_{uuid.uuid4().hex[:24]}"
    version_id = f"ver_{uuid.uuid4().hex[:24]}"
    job_id = f"job_{uuid.uuid4().hex[:24]}"

    object_key = f"documents/raw/{doc_id}/{version_id}.pdf"
    storage = get_storage_service()
    file_url = await storage.upload_file(file_bytes, object_key, content_type="application/pdf")

    # Insert Document
    doc = Document(
        id=doc_id,
        title=title,
        type=doc_type,
        status="DRAFT",
        scope=scope,
        code_number=code_number,
        issuing_body=issuing_body,
        effective_from=effective_from,
        effective_to=effective_to,
        latest_version=1,
        author_id=user.id,
        tags=tags or [],
    )
    session.add(doc)

    # Insert DocumentVersion
    ver = DocumentVersion(
        id=version_id,
        document_id=doc_id,
        version_number=1,
        status="DRAFT",
        file_url=file_url,
        file_size=total_bytes,
        checksum=checksum,
        ocr_status="QUEUED",
        requires_review=False,
        change_summary=change_summary,
        created_by=user.id,
    )
    session.add(ver)

    # Insert Job
    job = Job(
        id=job_id,
        type="OCR",
        status="QUEUED",
        progress=0,
        idempotency_key=idempotency_key,
        target_document_id=doc_id,
        target_version_id=version_id,
        created_by=user.id,
    )
    session.add(job)

    await session.commit()

    # Trigger async Celery task
    try:
        process_document_task.delay(job_id, version_id)
    except Exception as exc:
        logger.exception(
            "failed_to_enqueue_process_document_task",
            job_id=job_id,
            version_id=version_id,
            error=str(exc),
        )

    return doc_id, job_id, "QUEUED"


async def update_document(
    session: AsyncSession,
    document: Document,
    update_data: DocumentUpdateSchema,
) -> Document:
    """Update document metadata."""
    if update_data.title is not None:
        document.title = update_data.title
    if update_data.type is not None:
        document.type = update_data.type
    if update_data.scope is not None:
        document.scope = update_data.scope.value
    if update_data.code_number is not None:
        document.code_number = update_data.code_number
    if update_data.issuing_body is not None:
        document.issuing_body = update_data.issuing_body
    if update_data.effective_from is not None:
        document.effective_from = update_data.effective_from
    if update_data.effective_to is not None:
        document.effective_to = update_data.effective_to
    if update_data.tags is not None:
        document.tags = update_data.tags

    document.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(document)
    return document


async def soft_delete_document(session: AsyncSession, document: Document) -> None:
    """Soft delete document."""
    document.deleted_at = datetime.now(UTC)
    await session.commit()


async def list_document_versions(
    session: AsyncSession, document_id: str
) -> Sequence[DocumentVersion]:
    """Get all versions of a document."""
    stmt = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_document_version_by_id(
    session: AsyncSession, document_id: str, version_id: str
) -> DocumentVersion | None:
    """Get specific version of a document."""
    stmt = select(DocumentVersion).where(
        DocumentVersion.document_id == document_id,
        DocumentVersion.id == version_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_document_version(
    session: AsyncSession,
    document: Document,
    user: User,
    file_bytes: bytes,
    checksum: str,
    total_bytes: int,
    idempotency_key: str,
    change_summary: str | None = None,
    request_id: str = "",
) -> tuple[str, str, str]:
    """Upload new version for an existing document."""
    if idempotency_key:
        job_stmt = select(Job).where(Job.idempotency_key == idempotency_key)
        existing_job_res = await session.execute(job_stmt)
        existing_job = existing_job_res.scalar_one_or_none()

        if existing_job:
            if existing_job.target_version_id:
                ver_stmt = select(DocumentVersion).where(
                    DocumentVersion.id == existing_job.target_version_id
                )
                ver_res = await session.execute(ver_stmt)
                existing_ver = ver_res.scalar_one_or_none()
                if existing_ver and existing_ver.checksum == checksum:
                    return document.id, existing_job.id, existing_job.status
            raise idempotency_mismatch(request_id=request_id)

    new_version_num = document.latest_version + 1
    version_id = f"ver_{uuid.uuid4().hex[:24]}"
    job_id = f"job_{uuid.uuid4().hex[:24]}"

    object_key = f"documents/raw/{document.id}/{version_id}.pdf"
    storage = get_storage_service()
    file_url = await storage.upload_file(file_bytes, object_key, content_type="application/pdf")

    ver = DocumentVersion(
        id=version_id,
        document_id=document.id,
        version_number=new_version_num,
        status="DRAFT",
        file_url=file_url,
        file_size=total_bytes,
        checksum=checksum,
        ocr_status="QUEUED",
        requires_review=False,
        change_summary=change_summary,
        created_by=user.id,
    )
    session.add(ver)

    document.latest_version = new_version_num
    document.updated_at = datetime.now(UTC)

    job = Job(
        id=job_id,
        type="OCR",
        status="QUEUED",
        progress=0,
        idempotency_key=idempotency_key,
        target_document_id=document.id,
        target_version_id=version_id,
        created_by=user.id,
    )
    session.add(job)

    await session.commit()

    try:
        process_document_task.delay(job_id, version_id)
    except Exception as exc:
        logger.exception(
            "failed_to_enqueue_process_document_task",
            job_id=job_id,
            version_id=version_id,
            error=str(exc),
        )

    return document.id, job_id, "QUEUED"


async def update_document_version_metadata(
    session: AsyncSession,
    version: DocumentVersion,
    change_summary: str | None,
    request_id: str = "",
) -> DocumentVersion:
    """Update version change summary."""
    if version.status == "APPROVED":
        raise conflict(
            detail="Phiên bản đã duyệt không được phép sửa metadata.",
            request_id=request_id,
        )
    if change_summary is not None:
        version.change_summary = change_summary
    await session.commit()
    await session.refresh(version)
    return version


async def trigger_version_ocr(
    session: AsyncSession,
    document_id: str,
    version: DocumentVersion,
    user: User,
    idempotency_key: str,
    request_id: str = "",
) -> str:
    """Re-trigger OCR process for a document version."""
    if idempotency_key:
        job_stmt = select(Job).where(Job.idempotency_key == idempotency_key)
        existing_job_res = await session.execute(job_stmt)
        existing_job = existing_job_res.scalar_one_or_none()

        if existing_job:
            if existing_job.target_version_id == version.id:
                return existing_job.id
            raise idempotency_mismatch(request_id=request_id)

    job_id = f"job_{uuid.uuid4().hex[:24]}"
    version.ocr_status = "QUEUED"

    job = Job(
        id=job_id,
        type="OCR",
        status="QUEUED",
        progress=0,
        idempotency_key=idempotency_key,
        target_document_id=document_id,
        target_version_id=version.id,
        created_by=user.id,
    )
    session.add(job)
    await session.commit()

    try:
        process_document_task.delay(job_id, version.id)
    except Exception as exc:
        logger.exception(
            "failed_to_enqueue_process_document_task",
            job_id=job_id,
            version_id=version.id,
            error=str(exc),
        )
    return job_id


async def approve_document_version(
    session: AsyncSession,
    document: Document,
    version: DocumentVersion,
    request_id: str = "",
) -> DocumentVersion:
    """Approve a document version (Lifecycle Invariant Check)."""
    if version.ocr_status != "SUCCEEDED":
        raise conflict(
            detail="Chỉ có thể phê duyệt phiên bản khi OCR thành công (ocr_status == 'SUCCEEDED').",
            request_id=request_id,
        )
    if version.requires_review:
        raise conflict(
            detail="Phiên bản yêu cầu kiểm tra OCR trước khi phê duyệt.",
            request_id=request_id,
        )

    prev_approved_stmt = select(DocumentVersion).where(
        DocumentVersion.document_id == document.id,
        DocumentVersion.status == "APPROVED",
        DocumentVersion.id != version.id,
    )
    prev_approved_res = await session.execute(prev_approved_stmt)
    prev_approved_versions = prev_approved_res.scalars().all()

    if prev_approved_versions:
        latest_prev_approved = max(prev_approved_versions, key=lambda v: v.version_number)
        version.supersedes_version_id = latest_prev_approved.id

        for prev_ver in prev_approved_versions:
            prev_ver.status = "SUPERSEDED"
            prev_ver.superseded_by_version_id = version.id

    version.status = "APPROVED"
    document.status = "APPROVED"
    document.latest_version = version.version_number
    document.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(version)
    return version
