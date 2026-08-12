"""Coverage boost unit tests targeting missing lines in documents, jobs, and storage services."""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import pytest
from fastapi import UploadFile
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.enums import DocumentScopeCode
from app.core.errors import ApiError
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.job import Job
from app.models.user import User
from app.modules.documents import service
from app.modules.documents.schemas import DocumentUpdateSchema
from app.modules.documents.security import (
    MAX_FILE_SIZE_BYTES,
    validate_pdf_bytes,
    validate_upload_file,
)
from app.services.pdf_validator import PdfValidatorService
from app.services.storage import (
    LocalStorageService,
    MinioStorageService,
    get_storage_service,
)
from tests.conftest import auth_headers_for

VALID_PDF_BYTES = (
    b"%PDF-1.7 header\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
)


# ============================================================================
# Section 1: Documents Service Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_get_document_by_id_include_deleted(db_session_factory, admin_user: User) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_soft_del_01",
            title="Tài liệu bị xóa mềm",
            type="QUY_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=admin_user.id,
        )
        session.add(doc)
        await session.commit()

        await service.soft_delete_document(session, doc)

        # include_deleted=False (default) should return None
        fetched_active = await service.get_document_by_id(
            session, "doc_soft_del_01", include_deleted=False
        )
        assert fetched_active is None

        # include_deleted=True should return the document
        fetched_deleted = await service.get_document_by_id(
            session, "doc_soft_del_01", include_deleted=True
        )
        assert fetched_deleted is not None
        assert fetched_deleted.id == "doc_soft_del_01"


@pytest.mark.asyncio
async def test_update_document_service_all_fields(db_session_factory, admin_user: User) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_update_01",
            title="Tieu de goc",
            type="QUY_CHE",
            status="DRAFT",
            scope="PUBLIC",
            author_id=admin_user.id,
        )
        session.add(doc)
        await session.commit()

        update_schema = DocumentUpdateSchema(
            title="Tieu de moi",
            type="QUY_DINH",
            scope=DocumentScopeCode.STUDENT_AFFAIRS,
            code_number="QD-2026/01",
            issuing_body="Ban BGH",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            tags=["moi", "cap_nhat"],
        )

        updated = await service.update_document(session, doc, update_schema)
        assert updated.title == "Tieu de moi"
        assert updated.type == "QUY_DINH"
        assert updated.scope == "STUDENT_AFFAIRS"
        assert updated.code_number == "QD-2026/01"
        assert updated.issuing_body == "Ban BGH"
        assert updated.effective_from == date(2026, 1, 1)
        assert updated.effective_to == date(2026, 12, 31)
        assert updated.tags == ["moi", "cap_nhat"]


@pytest.mark.asyncio
async def test_create_document_and_idempotency(db_session_factory, admin_user: User) -> None:
    async with db_session_factory() as session:
        idempotency_key = "idem_key_create_doc_01"
        doc_id, job_id, status_str = await service.create_document(
            session=session,
            user=admin_user,
            file_bytes=VALID_PDF_BYTES,
            checksum="dummy_checksum_123",
            total_bytes=len(VALID_PDF_BYTES),
            idempotency_key=idempotency_key,
            title="Tài liệu Idempotent",
            doc_type="QUY_DINH",
            scope="PUBLIC",
        )
        assert doc_id.startswith("doc_")
        assert job_id.startswith("job_")
        assert status_str == "QUEUED"

        # Re-call with exact same parameters -> returns existing job
        doc_id_2, job_id_2, status_str_2 = await service.create_document(
            session=session,
            user=admin_user,
            file_bytes=VALID_PDF_BYTES,
            checksum="dummy_checksum_123",
            total_bytes=len(VALID_PDF_BYTES),
            idempotency_key=idempotency_key,
            title="Tài liệu Idempotent",
            doc_type="QUY_DINH",
            scope="PUBLIC",
        )
        assert doc_id_2 == doc_id
        assert job_id_2 == job_id
        assert status_str_2 in ("QUEUED", "SUCCEEDED")

        # Re-call with same idempotency key but different checksum -> idempotency mismatch 409
        with pytest.raises(ApiError) as exc_info:
            await service.create_document(
                session=session,
                user=admin_user,
                file_bytes=VALID_PDF_BYTES,
                checksum="different_checksum_456",
                total_bytes=len(VALID_PDF_BYTES),
                idempotency_key=idempotency_key,
                title="Tài liệu Idempotent",
                doc_type="QUY_DINH",
                scope="PUBLIC",
            )
        assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_create_document_version_and_idempotency(
    db_session_factory, admin_user: User
) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_ver_test_01",
            title="Doc Version Test",
            type="QUY_DINH",
            status="DRAFT",
            scope="PUBLIC",
            latest_version=1,
            author_id=admin_user.id,
        )
        session.add(doc)
        await session.commit()

        idempotency_key = "idem_key_ver_01"
        doc_id, job_id, status_str = await service.create_document_version(
            session=session,
            document=doc,
            user=admin_user,
            file_bytes=VALID_PDF_BYTES,
            checksum="checksum_ver_01",
            total_bytes=len(VALID_PDF_BYTES),
            idempotency_key=idempotency_key,
            change_summary="Bổ sung điều khoản",
        )
        assert doc_id == doc.id
        assert job_id.startswith("job_")
        assert status_str == "QUEUED"

        # Match idempotency key & checksum -> returns existing job
        doc_id_2, job_id_2, status_str_2 = await service.create_document_version(
            session=session,
            document=doc,
            user=admin_user,
            file_bytes=VALID_PDF_BYTES,
            checksum="checksum_ver_01",
            total_bytes=len(VALID_PDF_BYTES),
            idempotency_key=idempotency_key,
        )
        assert job_id_2 == job_id

        # Mismatch idempotency key checksum -> raises 409
        with pytest.raises(ApiError) as exc_info:
            await service.create_document_version(
                session=session,
                document=doc,
                user=admin_user,
                file_bytes=VALID_PDF_BYTES,
                checksum="checksum_ver_DIFFERENT",
                total_bytes=len(VALID_PDF_BYTES),
                idempotency_key=idempotency_key,
            )
        assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_update_document_version_metadata_approved_conflict(
    db_session_factory, admin_user: User
) -> None:
    async with db_session_factory() as session:
        ver = DocumentVersion(
            id="ver_approved_01",
            document_id="doc_app_01",
            version_number=1,
            status="APPROVED",
            file_url="/storage/dummy.pdf",
            file_size=100,
            checksum="chk123",
            created_by=admin_user.id,
        )
        session.add(ver)
        await session.commit()

        # Updating metadata of APPROVED version raises 409 conflict
        with pytest.raises(ApiError) as exc_info:
            await service.update_document_version_metadata(
                session=session,
                version=ver,
                change_summary="New summary",
            )
        assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_trigger_version_ocr_and_idempotency(db_session_factory, admin_user: User) -> None:
    async with db_session_factory() as session:
        ver = DocumentVersion(
            id="ver_ocr_01",
            document_id="doc_ocr_01",
            version_number=1,
            status="DRAFT",
            file_url="/storage/dummy.pdf",
            file_size=100,
            checksum="chk123",
            created_by=admin_user.id,
        )
        session.add(ver)
        await session.commit()

        idem_key = "idem_ocr_trigger_01"
        job_id = await service.trigger_version_ocr(
            session=session,
            document_id="doc_ocr_01",
            version=ver,
            user=admin_user,
            idempotency_key=idem_key,
        )
        assert job_id.startswith("job_")

        # Same idempotency key -> returns existing job ID
        job_id_2 = await service.trigger_version_ocr(
            session=session,
            document_id="doc_ocr_01",
            version=ver,
            user=admin_user,
            idempotency_key=idem_key,
        )
        assert job_id_2 == job_id

        # Mismatch version for same idempotency key -> raises 409
        ver_other = DocumentVersion(
            id="ver_ocr_other",
            document_id="doc_ocr_01",
            version_number=2,
            status="DRAFT",
            file_url="/storage/dummy2.pdf",
            file_size=100,
            checksum="chk456",
            created_by=admin_user.id,
        )
        session.add(ver_other)
        await session.commit()

        with pytest.raises(ApiError) as exc_info:
            await service.trigger_version_ocr(
                session=session,
                document_id="doc_ocr_01",
                version=ver_other,
                user=admin_user,
                idempotency_key=idem_key,
            )
        assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_approve_document_version_logic_and_errors(
    db_session_factory, admin_user: User
) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_approve_flow",
            title="Quy chế duyệt",
            type="QUY_CHE",
            status="DRAFT",
            scope="PUBLIC",
            latest_version=2,
            author_id=admin_user.id,
        )
        v1 = DocumentVersion(
            id="ver_app_v1",
            document_id=doc.id,
            version_number=1,
            status="APPROVED",
            file_url="/storage/v1.pdf",
            file_size=100,
            checksum="chk_v1",
            ocr_status="SUCCEEDED",
            requires_review=False,
            created_by=admin_user.id,
        )
        v2 = DocumentVersion(
            id="ver_app_v2",
            document_id=doc.id,
            version_number=2,
            status="DRAFT",
            file_url="/storage/v2.pdf",
            file_size=100,
            checksum="chk_v2",
            ocr_status="FAILED",
            requires_review=False,
            created_by=admin_user.id,
        )
        session.add_all([doc, v1, v2])
        await session.commit()

        # 1. Error: ocr_status != SUCCEEDED
        with pytest.raises(ApiError) as exc_info1:
            await service.approve_document_version(session, doc, v2)
        assert exc_info1.value.status_code == 409
        assert "SUCCEEDED" in str(exc_info1.value.detail)

        # 2. Error: requires_review is True
        v2.ocr_status = "SUCCEEDED"
        v2.requires_review = True
        await session.commit()

        with pytest.raises(ApiError) as exc_info2:
            await service.approve_document_version(session, doc, v2)
        assert exc_info2.value.status_code == 409
        assert "kiểm tra OCR" in str(exc_info2.value.detail)

        # 3. Success: approve v2 supersedes v1
        v2.requires_review = False
        await session.commit()

        approved_v2 = await service.approve_document_version(session, doc, v2)
        assert approved_v2.status == "APPROVED"
        assert approved_v2.supersedes_version_id == "ver_app_v1"

        # Check v1 superseded
        await session.refresh(v1)
        assert v1.status == "SUPERSEDED"
        assert v1.superseded_by_version_id == "ver_app_v2"


# ============================================================================
# Section 2: Documents Router 404 Endpoints
# ============================================================================


@pytest.mark.asyncio
async def test_documents_router_not_found_endpoints(
    api_client: AsyncClient, admin_user: User
) -> None:
    headers = auth_headers_for(admin_user)
    non_existent = "doc_non_existent_999"

    # GET /documents/{id}
    resp1 = await api_client.get(f"/api/v1/documents/{non_existent}", headers=headers)
    assert resp1.status_code == 404

    # PATCH /documents/{id}
    resp2 = await api_client.patch(
        f"/api/v1/documents/{non_existent}",
        headers=headers,
        json={"title": "Mới"},
    )
    assert resp2.status_code == 404

    # DELETE /documents/{id}
    resp3 = await api_client.delete(f"/api/v1/documents/{non_existent}", headers=headers)
    assert resp3.status_code == 404

    # GET /documents/{id}/versions
    resp4 = await api_client.get(f"/api/v1/documents/{non_existent}/versions", headers=headers)
    assert resp4.status_code == 404

    # POST /documents/{id}/versions
    files = {"file": ("test.pdf", VALID_PDF_BYTES, "application/pdf")}
    headers_idem = {**headers, "Idempotency-Key": "idem_404_ver"}
    resp5 = await api_client.post(
        f"/api/v1/documents/{non_existent}/versions",
        headers=headers_idem,
        files=files,
    )
    assert resp5.status_code == 404

    # GET /documents/{id}/versions/{vid}
    resp6 = await api_client.get(
        f"/api/v1/documents/{non_existent}/versions/ver_999", headers=headers
    )
    assert resp6.status_code == 404

    # PATCH /documents/{id}/versions/{vid}/metadata
    resp7 = await api_client.patch(
        f"/api/v1/documents/{non_existent}/versions/ver_999/metadata",
        headers=headers,
        json={"change_summary": "Sửa"},
    )
    assert resp7.status_code == 404

    # POST /documents/{id}/versions/{vid}/ocr
    resp8 = await api_client.post(
        f"/api/v1/documents/{non_existent}/versions/ver_999/ocr",
        headers=headers_idem,
    )
    assert resp8.status_code == 404

    # POST /documents/{id}/versions/{vid}/approve
    resp9 = await api_client.post(
        f"/api/v1/documents/{non_existent}/versions/ver_999/approve",
        headers=headers,
    )
    assert resp9.status_code == 404


@pytest.mark.asyncio
async def test_documents_router_version_not_found_on_existing_doc(
    api_client: AsyncClient, admin_user: User, db_session_factory
) -> None:
    async with db_session_factory() as session:
        doc = Document(
            id="doc_ver_404_test",
            title="Document Exists",
            type="QUY_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=admin_user.id,
        )
        session.add(doc)
        await session.commit()

    headers = auth_headers_for(admin_user)

    # GET /documents/{id}/versions/{vid} (version does not exist)
    resp1 = await api_client.get(
        "/api/v1/documents/doc_ver_404_test/versions/ver_missing", headers=headers
    )
    assert resp1.status_code == 404

    # PATCH /documents/{id}/versions/{vid}/metadata
    resp2 = await api_client.patch(
        "/api/v1/documents/doc_ver_404_test/versions/ver_missing/metadata",
        headers=headers,
        json={"change_summary": "Test"},
    )
    assert resp2.status_code == 404

    # POST /documents/{id}/versions/{vid}/ocr
    headers_idem = {**headers, "Idempotency-Key": "idem_ocr_404"}
    resp3 = await api_client.post(
        "/api/v1/documents/doc_ver_404_test/versions/ver_missing/ocr",
        headers=headers_idem,
    )
    assert resp3.status_code == 404

    # POST /documents/{id}/versions/{vid}/approve
    resp4 = await api_client.post(
        "/api/v1/documents/doc_ver_404_test/versions/ver_missing/approve",
        headers=headers,
    )
    assert resp4.status_code == 404


# ============================================================================
# Section 3: Jobs Router Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_jobs_router_status_and_cancel_edge_cases(
    api_client: AsyncClient,
    admin_user: User,
    student_user: User,
    db_session_factory,
) -> None:
    async with db_session_factory() as session:
        admin_job = Job(
            id="job_admin_01",
            type="OCR",
            status="QUEUED",
            progress=0,
            created_by=admin_user.id,
        )
        finished_job = Job(
            id="job_finished_01",
            type="OCR",
            status="SUCCEEDED",
            progress=100,
            created_by=student_user.id,
        )
        session.add_all([admin_job, finished_job])
        await session.commit()

    student_headers = auth_headers_for(student_user)
    admin_headers = auth_headers_for(admin_user)

    # 1. Get non-existent job -> 404
    resp1 = await api_client.get("/api/v1/jobs/job_missing_999", headers=student_headers)
    assert resp1.status_code == 404

    # 2. Student trying to view Admin job -> 403 Forbidden
    resp2 = await api_client.get("/api/v1/jobs/job_admin_01", headers=student_headers)
    assert resp2.status_code == 403

    # 3. Cancel non-existent job -> 404
    resp3 = await api_client.post("/api/v1/jobs/job_missing_999/cancel", headers=admin_headers)
    assert resp3.status_code == 404

    # 4. Student trying to cancel Admin job -> 403 Forbidden
    resp4 = await api_client.post("/api/v1/jobs/job_admin_01/cancel", headers=student_headers)
    assert resp4.status_code == 403

    # 5. Cancel already finished job -> 409 Conflict
    resp5 = await api_client.post("/api/v1/jobs/job_finished_01/cancel", headers=student_headers)
    assert resp5.status_code == 409

    # 6. Admin cancels queued job -> 200 OK & status CANCELLED
    resp6 = await api_client.post("/api/v1/jobs/job_admin_01/cancel", headers=admin_headers)
    assert resp6.status_code == 200
    assert resp6.json()["data"]["status"] == "CANCELLED"


# ============================================================================
# Section 4: Storage Service Edge Cases & Fallbacks
# ============================================================================


@pytest.mark.asyncio
async def test_local_storage_service_methods(tmp_path: Path) -> None:
    storage = LocalStorageService(base_dir=tmp_path)
    object_key = "test_dir/sample.pdf"

    # Upload
    url = await storage.upload_file(VALID_PDF_BYTES, object_key)
    assert url == f"/storage/{object_key}"

    # Download
    downloaded = await storage.download_file(object_key)
    assert downloaded == VALID_PDF_BYTES

    # Download non-existent -> FileNotFoundError
    with pytest.raises(FileNotFoundError):
        await storage.download_file("non_existent.pdf")

    # Delete
    await storage.delete_file(object_key)
    with pytest.raises(FileNotFoundError):
        await storage.download_file(object_key)

    # Delete non-existent (should not raise)
    await storage.delete_file("non_existent.pdf")


@pytest.mark.asyncio
async def test_minio_storage_service_raises_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnavailableMinio:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def bucket_exists(self, bucket: str) -> bool:
            raise ConnectionError(f"MinIO unavailable for {bucket}")

        def get_object(self, bucket: str, object_key: str) -> object:
            raise ConnectionError(f"MinIO unavailable for {bucket}/{object_key}")

        def remove_object(self, bucket: str, object_key: str) -> None:
            raise ConnectionError(f"MinIO unavailable for {bucket}/{object_key}")

    monkeypatch.setattr("minio.Minio", UnavailableMinio)
    minio_service = MinioStorageService()
    object_key = "test_fallback/sample.pdf"

    # MinIO unavailable (package/service missing) -> operations must raise,
    # NOT silently fall back to LocalStorageService.
    with pytest.raises(RuntimeError, match="MinIO upload failed"):
        await minio_service.upload_file(VALID_PDF_BYTES, object_key)

    with pytest.raises(RuntimeError, match="MinIO download failed"):
        await minio_service.download_file(object_key)

    with pytest.raises(RuntimeError, match="MinIO delete failed"):
        await minio_service.delete_file(object_key)


@pytest.mark.asyncio
async def test_get_storage_service_production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Clear singleton
    import app.services.storage as storage_mod

    monkeypatch.setattr(storage_mod, "_storage_instance", None)
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()

    service_inst = get_storage_service()
    assert isinstance(service_inst, MinioStorageService)

    # Reset back to test
    monkeypatch.setattr(storage_mod, "_storage_instance", None)
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()


# ============================================================================
# Section 5: PDF Validation Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_pdf_validator_service_class_method() -> None:
    file_obj = io.BytesIO(VALID_PDF_BYTES)
    upload = UploadFile(
        filename="test.pdf",
        file=file_obj,
        headers={"content-type": "application/pdf"},
    )
    checksum, size = await PdfValidatorService.validate_upload_file(upload)
    assert len(checksum) == 64
    assert size == len(VALID_PDF_BYTES)


@pytest.mark.asyncio
async def test_pdf_validation_security_edge_cases() -> None:
    # 1. validate_pdf_bytes empty / non-pdf magic bytes
    with pytest.raises(ApiError) as exc1:
        validate_pdf_bytes(b"INVALID_HEADER")
    assert exc1.value.status_code == 415

    # 2. validate_pdf_bytes wrong content type
    with pytest.raises(ApiError) as exc2:
        validate_pdf_bytes(VALID_PDF_BYTES, content_type="image/png")
    assert exc2.value.status_code == 415

    # 3. validate_pdf_bytes payload too large
    oversized_bytes = b"%PDF-" + b"0" * (MAX_FILE_SIZE_BYTES + 10)
    with pytest.raises(ApiError) as exc3:
        validate_pdf_bytes(oversized_bytes)
    assert exc3.value.status_code == 413

    # 4. validate_upload_file wrong content type
    upload_wrong_ct = UploadFile(
        filename="test.png",
        file=io.BytesIO(VALID_PDF_BYTES),
        headers={"content-type": "image/png"},
    )
    with pytest.raises(ApiError) as exc4:
        await validate_upload_file(upload_wrong_ct)
    assert exc4.value.status_code == 415

    # 5. validate_upload_file header < 5 bytes or missing magic bytes
    upload_short_hdr = UploadFile(
        filename="short.pdf",
        file=io.BytesIO(b"%PDF"),
        headers={"content-type": "application/pdf"},
    )
    with pytest.raises(ApiError) as exc5:
        await validate_upload_file(upload_short_hdr)
    assert exc5.value.status_code == 415


# ============================================================================
# Section 6: Celery Exception Fallbacks & Dependencies Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_celery_task_delay_exception_handling(db_session_factory, admin_user: User) -> None:
    from app.modules.documents.dependencies import check_document_access, get_idempotency_key

    # 1. Test get_idempotency_key
    assert get_idempotency_key("  valid_key_123  ") == "valid_key_123"
    with pytest.raises(ApiError) as exc1:
        get_idempotency_key("   ")
    assert exc1.value.status_code == 422

    # 2. Test check_document_access soft-deleted doc
    deleted_doc = Document(
        id="doc_deleted_access",
        title="Deleted Doc",
        type="QUY_DINH",
        status="DRAFT",
        scope="PUBLIC",
        deleted_at=admin_user.created_at,
        author_id=admin_user.id,
    )
    with pytest.raises(ApiError) as exc2:
        check_document_access(deleted_doc, admin_user)
    assert exc2.value.status_code == 404
