"""FastAPI Router for Document Management endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.db.session import get_session
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.documents import service
from app.modules.documents.dependencies import (
    check_document_access,
    require_admin,
    require_staff_or_admin,
)
from app.modules.documents.schemas import (
    DocumentDetailEnvelope,
    DocumentDetailResponse,
    DocumentListEnvelope,
    DocumentResponse,
    DocumentSingleEnvelope,
    DocumentUpdateSchema,
    DocumentVersionListEnvelope,
    DocumentVersionResponse,
    DocumentVersionSingleEnvelope,
    JobCreatedEnvelope,
    UploadResponseEnvelope,
    VersionUpdateSchema,
)
from app.services.pdf_validator import validate_upload_file

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListEnvelope)
async def list_documents(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    status: str | None = Query(None),
    type: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> DocumentListEnvelope:
    """List documents with pagination and RBAC scope filtering."""
    docs, total = await service.list_documents(
        session=session,
        user=current_user,
        status=status,
        doc_type=type,
        q=q,
        page=page,
        limit=limit,
    )
    return DocumentListEnvelope(
        data=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("", response_model=UploadResponseEnvelope, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    type: str = Form(...),
    scope: str = Form("PUBLIC"),
    issuing_body: str | None = Form(None),
    effective_from: date | str | None = Form(None),
    effective_to: date | str | None = Form(None),
    tags: str | None = Form(None),
    change_summary: str | None = Form(None),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(require_staff_or_admin),
    session: AsyncSession = Depends(get_session),
) -> UploadResponseEnvelope:
    """Upload a new PDF document (returns 202 Accepted + job_id)."""
    request_id = getattr(request.state, "request_id", "")

    file_bytes, checksum, total_bytes = await validate_upload_file(
        upload_file=file, request_id=request_id
    )

    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    doc_id, job_id, job_status = await service.create_document(
        session=session,
        user=current_user,
        file_bytes=file_bytes,
        checksum=checksum,
        total_bytes=total_bytes,
        idempotency_key=idempotency_key,
        title=title,
        doc_type=type,
        scope=scope,
        issuing_body=issuing_body,
        effective_from=str(effective_from) if effective_from else None,
        effective_to=str(effective_to) if effective_to else None,
        tags=parsed_tags,
        change_summary=change_summary,
        request_id=request_id,
    )

    return UploadResponseEnvelope(
        data={
            "document_id": doc_id,
            "job_id": job_id,
            "status": job_status,
        }
    )


@router.get("/{id}", response_model=DocumentDetailEnvelope)
async def get_document_detail(
    id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentDetailEnvelope:
    """Get document details with versions."""
    request_id = getattr(request.state, "request_id", "")
    doc = await service.get_document_by_id(session, id)
    if not doc:
        raise not_found(detail=f"Tài liệu với ID '{id}' không tồn tại.", request_id=request_id)

    check_document_access(doc, current_user, request_id=request_id)
    return DocumentDetailEnvelope(data=DocumentDetailResponse.model_validate(doc))


@router.patch("/{id}", response_model=DocumentSingleEnvelope)
async def update_document(
    id: str,
    body: DocumentUpdateSchema,
    request: Request,
    current_user: User = Depends(require_staff_or_admin),
    session: AsyncSession = Depends(get_session),
) -> DocumentSingleEnvelope:
    """Update document metadata."""
    request_id = getattr(request.state, "request_id", "")
    doc = await service.get_document_by_id(session, id)
    if not doc:
        raise not_found(detail=f"Tài liệu với ID '{id}' không tồn tại.", request_id=request_id)

    check_document_access(doc, current_user, request_id=request_id)
    updated_doc = await service.update_document(session, doc, body)
    return DocumentSingleEnvelope(data=DocumentResponse.model_validate(updated_doc))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Soft delete document (Admin only)."""
    request_id = getattr(request.state, "request_id", "")
    doc = await service.get_document_by_id(session, id)
    if not doc or doc.deleted_at is not None:
        raise not_found(detail=f"Tài liệu với ID '{id}' không tồn tại.", request_id=request_id)

    await service.soft_delete_document(session, doc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{id}/versions", response_model=DocumentVersionListEnvelope)
async def list_document_versions(
    id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentVersionListEnvelope:
    """List all versions of a document."""
    request_id = getattr(request.state, "request_id", "")
    doc = await service.get_document_by_id(session, id)
    if not doc:
        raise not_found(detail=f"Tài liệu với ID '{id}' không tồn tại.", request_id=request_id)

    check_document_access(doc, current_user, request_id=request_id)
    versions = await service.list_document_versions(session, id)
    return DocumentVersionListEnvelope(
        data=[DocumentVersionResponse.model_validate(v) for v in versions]
    )


@router.post(
    "/{id}/versions",
    response_model=UploadResponseEnvelope,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_document_version(
    id: str,
    request: Request,
    file: UploadFile = File(...),
    change_summary: str | None = Form(None),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(require_staff_or_admin),
    session: AsyncSession = Depends(get_session),
) -> UploadResponseEnvelope:
    """Upload a new version of a document."""
    request_id = getattr(request.state, "request_id", "")
    doc = await service.get_document_by_id(session, id)
    if not doc:
        raise not_found(detail=f"Tài liệu với ID '{id}' không tồn tại.", request_id=request_id)

    check_document_access(doc, current_user, request_id=request_id)

    file_bytes, checksum, total_bytes = await validate_upload_file(
        upload_file=file, request_id=request_id
    )

    doc_id, job_id, job_status = await service.create_document_version(
        session=session,
        document=doc,
        user=current_user,
        file_bytes=file_bytes,
        checksum=checksum,
        total_bytes=total_bytes,
        idempotency_key=idempotency_key,
        change_summary=change_summary,
        request_id=request_id,
    )

    return UploadResponseEnvelope(
        data={
            "document_id": doc_id,
            "job_id": job_id,
            "status": job_status,
        }
    )


@router.get("/{id}/versions/{vid}", response_model=DocumentVersionSingleEnvelope)
async def get_document_version_detail(
    id: str,
    vid: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentVersionSingleEnvelope:
    """Get detail of a specific document version."""
    request_id = getattr(request.state, "request_id", "")
    doc = await service.get_document_by_id(session, id)
    if not doc:
        raise not_found(detail=f"Tài liệu với ID '{id}' không tồn tại.", request_id=request_id)

    check_document_access(doc, current_user, request_id=request_id)
    version = await service.get_document_version_by_id(session, id, vid)
    if not version:
        raise not_found(detail=f"Phiên bản với ID '{vid}' không tồn tại.", request_id=request_id)

    return DocumentVersionSingleEnvelope(data=DocumentVersionResponse.model_validate(version))


@router.patch("/{id}/versions/{vid}/metadata", response_model=DocumentVersionSingleEnvelope)
async def update_version_metadata(
    id: str,
    vid: str,
    body: VersionUpdateSchema,
    request: Request,
    current_user: User = Depends(require_staff_or_admin),
    session: AsyncSession = Depends(get_session),
) -> DocumentVersionSingleEnvelope:
    """Update metadata of a document version."""
    request_id = getattr(request.state, "request_id", "")
    doc = await service.get_document_by_id(session, id)
    if not doc:
        raise not_found(detail=f"Tài liệu với ID '{id}' không tồn tại.", request_id=request_id)

    check_document_access(doc, current_user, request_id=request_id)
    version = await service.get_document_version_by_id(session, id, vid)
    if not version:
        raise not_found(detail=f"Phiên bản với ID '{vid}' không tồn tại.", request_id=request_id)

    updated_ver = await service.update_document_version_metadata(
        session, version, body.change_summary, request_id=request_id
    )
    return DocumentVersionSingleEnvelope(data=DocumentVersionResponse.model_validate(updated_ver))


@router.post(
    "/{id}/versions/{vid}/ocr",
    response_model=JobCreatedEnvelope,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_version_ocr(
    id: str,
    vid: str,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(require_staff_or_admin),
    session: AsyncSession = Depends(get_session),
) -> JobCreatedEnvelope:
    """Trigger or re-trigger OCR process for a version."""
    request_id = getattr(request.state, "request_id", "")
    doc = await service.get_document_by_id(session, id)
    if not doc:
        raise not_found(detail=f"Tài liệu với ID '{id}' không tồn tại.", request_id=request_id)

    check_document_access(doc, current_user, request_id=request_id)
    version = await service.get_document_version_by_id(session, id, vid)
    if not version:
        raise not_found(detail=f"Phiên bản với ID '{vid}' không tồn tại.", request_id=request_id)

    job_id = await service.trigger_version_ocr(
        session, id, version, current_user, idempotency_key, request_id=request_id
    )
    return JobCreatedEnvelope(data={"job_id": job_id, "status": "QUEUED"})


@router.post("/{id}/versions/{vid}/approve", response_model=DocumentVersionSingleEnvelope)
async def approve_version(
    id: str,
    vid: str,
    request: Request,
    current_user: User = Depends(require_staff_or_admin),
    session: AsyncSession = Depends(get_session),
) -> DocumentVersionSingleEnvelope:
    """Approve a document version."""
    request_id = getattr(request.state, "request_id", "")
    doc = await service.get_document_by_id(session, id)
    if not doc:
        raise not_found(detail=f"Tài liệu với ID '{id}' không tồn tại.", request_id=request_id)

    check_document_access(doc, current_user, request_id=request_id)
    version = await service.get_document_version_by_id(session, id, vid)
    if not version:
        raise not_found(detail=f"Phiên bản với ID '{vid}' không tồn tại.", request_id=request_id)

    approved_ver = await service.approve_document_version(
        session, doc, version, request_id=request_id
    )
    return DocumentVersionSingleEnvelope(data=DocumentVersionResponse.model_validate(approved_ver))
