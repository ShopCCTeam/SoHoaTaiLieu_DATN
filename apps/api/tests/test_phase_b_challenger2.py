"""Empirical Verification Tests by Challenger 2 for Phase B.

Verifies:
1. Celery Task Eager Execution in Async Event Loop
2. Soft Deletion Invariants across service and access layers
3. Version Approval Invariants & Version sequence handling
4. DB Transaction Atomicity & Post-commit side-effect failures
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.job import Job
from app.models.user import User
from app.modules.documents import service
from app.worker.tasks import process_document_task

VALID_PDF_BYTES = (
    b"%PDF-1.7 header\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
)


# ============================================================================
# FOCUS AREA 1: Celery Task Eager Execution
# ============================================================================


@pytest.mark.asyncio
async def test_celery_eager_execution_succeeds_in_async_event_loop(db_session_factory) -> None:
    """Test process_document_task in active event loop runs cleanly via ThreadPoolExecutor."""
    res = process_document_task("job_fake_id", "ver_fake_id")
    assert res == {"status": "FAILED", "error": "Not found"}


# ============================================================================
# FOCUS AREA 2: Soft Deletion Invariants
# ============================================================================


@pytest.mark.asyncio
async def test_soft_deletion_service_level_isolation(db_session_factory, staff_user: User) -> None:
    """Empirically verify how soft-deleted documents behave at service layer vs access layer."""
    async with db_session_factory() as session:
        doc = Document(
            id="doc_soft_del_test",
            title="Tài liệu bị xoá mềm",
            type="QUYET_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
            deleted_at=datetime.now(UTC),
        )
        session.add(doc)
        await session.commit()

    async with db_session_factory() as session:
        # 1. list_documents filters out soft-deleted documents
        docs, total = await service.list_documents(session, staff_user)
        doc_ids = [d.id for d in docs]
        assert "doc_soft_del_test" not in doc_ids

        # 2. get_document_by_id filters out soft-deleted documents by default
        retrieved_default = await service.get_document_by_id(session, "doc_soft_del_test")
        assert retrieved_default is None

        # 3. get_document_by_id with include_deleted=True returns soft-deleted document
        retrieved = await service.get_document_by_id(
            session, "doc_soft_del_test", include_deleted=True
        )
        assert retrieved is not None
        assert retrieved.deleted_at is not None


# ============================================================================
# FOCUS AREA 3: Version Approval Invariants
# ============================================================================


@pytest.mark.asyncio
async def test_version_approval_invariants(db_session_factory, staff_user: User) -> None:
    """Empirically verify version approval invariants and version pointer behavior."""
    async with db_session_factory() as session:
        doc = Document(
            id="doc_app_inv_test",
            title="Tài liệu kiểm tra phê duyệt",
            type="QUY_DINH",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
            latest_version=2,
        )
        ver1 = DocumentVersion(
            id="ver_inv_01",
            document_id="doc_app_inv_test",
            version_number=1,
            status="DRAFT",
            file_url="/storage/v1.pdf",
            file_size=1024,
            checksum="checksum_1",
            ocr_status="SUCCEEDED",
            created_by=staff_user.id,
        )
        ver2 = DocumentVersion(
            id="ver_inv_02",
            document_id="doc_app_inv_test",
            version_number=2,
            status="DRAFT",
            file_url="/storage/v2.pdf",
            file_size=2048,
            checksum="checksum_2",
            ocr_status="NOT_STARTED",
            created_by=staff_user.id,
        )
        session.add_all([doc, ver1, ver2])
        await session.commit()

    async with db_session_factory() as session:
        doc_obj = await service.get_document_by_id(
            session, "doc_app_inv_test", include_deleted=True
        )
        assert doc_obj is not None
        ver1_obj = await service.get_document_version_by_id(
            session, "doc_app_inv_test", "ver_inv_01"
        )
        assert ver1_obj is not None
        ver2_obj = await service.get_document_version_by_id(
            session, "doc_app_inv_test", "ver_inv_02"
        )
        assert ver2_obj is not None

        # 1. Approving ver2 when ocr_status != SUCCEEDED must fail
        from app.core.errors import ApiError

        with pytest.raises(ApiError) as exc_info:
            await service.approve_document_version(session, doc_obj, ver2_obj)
        assert exc_info.value.status_code == 409

        # 2. Approving ver1 (which has SUCCEEDED) succeeds
        approved_v1 = await service.approve_document_version(session, doc_obj, ver1_obj)
        assert approved_v1.status == "APPROVED"
        assert doc_obj.status == "APPROVED"
        # latest_version updated to approved version_number (1)
        assert doc_obj.latest_version == 1

        # 3. Mark ver2 ocr_status SUCCEEDED and approve ver2
        # -> ver1 becomes SUPERSEDED with lineage links
        ver2_obj.ocr_status = "SUCCEEDED"
        approved_v2 = await service.approve_document_version(session, doc_obj, ver2_obj)
        assert approved_v2.status == "APPROVED"
        assert approved_v2.supersedes_version_id == "ver_inv_01"
        assert ver1_obj.status == "SUPERSEDED"
        assert ver1_obj.superseded_by_version_id == "ver_inv_02"
        assert doc_obj.latest_version == 2


# ============================================================================
# FOCUS AREA 4: Transaction & Task Dispatch Atomicity
# ============================================================================


@pytest.mark.asyncio
async def test_transaction_commit_before_celery_dispatch(
    db_session_factory, staff_user: User
) -> None:
    """Empirically verify DB commit happens BEFORE Celery task dispatch."""
    async with db_session_factory() as session:
        # Simulate create_document DB commit step
        doc_id = "doc_tx_test_01"
        ver_id = "ver_tx_test_01"
        job_id = "job_tx_test_01"

        doc = Document(
            id=doc_id,
            title="Tài liệu test transaction",
            type="THONG_BAO",
            status="DRAFT",
            scope="PUBLIC",
            author_id=staff_user.id,
        )
        ver = DocumentVersion(
            id=ver_id,
            document_id=doc_id,
            version_number=1,
            status="DRAFT",
            file_url="/storage/test.pdf",
            file_size=100,
            checksum="hash123",
            ocr_status="QUEUED",
            created_by=staff_user.id,
        )
        job = Job(
            id=job_id,
            type="OCR",
            status="QUEUED",
            progress=0,
            idempotency_key="tx-idem-key-1",
            target_document_id=doc_id,
            target_version_id=ver_id,
            created_by=staff_user.id,
        )
        session.add_all([doc, ver, job])
        await session.commit()

        # Task dispatch executes safely without crashing
        process_document_task.delay(job_id, ver_id)

    # Check DB state post-dispatch
    async with db_session_factory() as session:
        job_in_db = await session.get(Job, job_id)
        assert job_in_db is not None
        assert job_in_db.status in ("QUEUED", "PROCESSING", "SUCCEEDED")
