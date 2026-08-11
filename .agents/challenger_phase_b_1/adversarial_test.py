"""Adversarial Empirical Test Harness for Phase B (Document Management & Storage).

Executed by Challenger Phase B 1.
"""

from __future__ import annotations

import asyncio
import io
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add apps/api to sys.path so app imports work
api_dir = Path("E:/SoHoaTaiLieu_DATN/apps/api").resolve()
sys.path.insert(0, str(api_dir))

from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.main import create_app
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.job import Job
from app.models.user import User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.documents.security import validate_pdf_bytes, validate_upload_file
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Output report list
test_results: list[dict[str, str]] = []


def record_result(name: str, status: str, details: str) -> None:
    print(f"[{status}] {name}: {details}")
    test_results.append({"name": name, "status": status, "details": details})


async def run_adversarial_tests():
    print("=== STARTING ADVERSARIAL EMPIRICAL TESTS ===")

    # 1. Setup file-backed SQLite DB in agent folder
    db_file = Path("E:/SoHoaTaiLieu_DATN/.agents/challenger_phase_b_1/test_adv.db")
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    # Seed users
    async with session_factory() as session:
        admin_user = User(
            id="usr_admin_adv",
            email="admin_adv@example.com",
            password_hash=hash_password("Demo@2026"),
            full_name="Admin Challenger",
            role="admin",
            department="Phòng CTSV",
            is_active=True,
        )
        staff_user = User(
            id="usr_staff_adv",
            email="staff_adv@example.com",
            password_hash=hash_password("Demo@2026"),
            full_name="Staff Challenger",
            role="staff",
            department="Phòng CTSV",
            is_active=True,
        )
        student_user = User(
            id="usr_student_adv",
            email="student_adv@example.com",
            password_hash=hash_password("Demo@2026"),
            full_name="Student Challenger",
            role="student",
            department="Khoa CNTT",
            is_active=True,
        )
        session.add_all([admin_user, staff_user, student_user])
        await session.commit()

    admin_token = create_access_token(subject="usr_admin_adv", role="admin")
    staff_token = create_access_token(subject="usr_staff_adv", role="staff")
    student_token = create_access_token(subject="usr_student_adv", role="student")

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Setup FastAPI test client
    app = create_app()

    async def _override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # -------------------------------------------------------------------
        # Category A: PDF Validation & Security (Magic bytes, Content-Type, Size)
        # -------------------------------------------------------------------

        # A1: Invalid Magic Bytes (b"NOT-A-PDF")
        try:
            validate_pdf_bytes(b"NOT-A-PDF-CONTENT", content_type="application/pdf")
            record_result("A1_magic_bytes_invalid", "FAIL", "Did not raise exception for invalid magic bytes")
        except Exception as e:
            record_result("A1_magic_bytes_invalid", "PASS", f"Successfully caught: {e}")

        # A2: Empty file
        try:
            validate_pdf_bytes(b"", content_type="application/pdf")
            record_result("A2_empty_file", "FAIL", "Did not raise exception for empty file")
        except Exception as e:
            record_result("A2_empty_file", "PASS", f"Successfully caught: {e}")

        # A3: Truncated header
        try:
            validate_pdf_bytes(b"%PD", content_type="application/pdf")
            record_result("A3_truncated_header", "FAIL", "Did not raise exception for truncated header")
        except Exception as e:
            record_result("A3_truncated_header", "PASS", f"Successfully caught: {e}")

        # A4: Wrong MIME Type
        try:
            validate_pdf_bytes(b"%PDF-1.4 Test PDF", content_type="image/png")
            record_result("A4_wrong_mime_type", "FAIL", "Did not raise exception for wrong MIME type")
        except Exception as e:
            record_result("A4_wrong_mime_type", "PASS", f"Successfully caught: {e}")

        # A5: Oversized PDF Stream (> 50MB)
        large_bytes = b"%PDF-1.4" + b"X" * (50 * 1024 * 1024 + 10)
        try:
            validate_pdf_bytes(large_bytes, content_type="application/pdf")
            record_result("A5_oversized_pdf", "FAIL", "Did not raise exception for file size > 50MB")
        except Exception as e:
            record_result("A5_oversized_pdf", "PASS", f"Successfully caught payload_too_large: {e}")

        # -------------------------------------------------------------------
        # Category B: RBAC & Document Access Restrictions
        # -------------------------------------------------------------------

        # Seed internal document and public document
        async with session_factory() as session:
            internal_doc = Document(
                id="doc_internal_01",
                title="Tài liệu Nội bộ Mật",
                type="QUYET_DINH",
                status="APPROVED",
                scope="INTERNAL",
                latest_version=1,
                author_id="usr_admin_adv",
                tags=[],
            )
            public_doc = Document(
                id="doc_public_01",
                title="Tài liệu Công khai",
                type="THONG_BAO",
                status="APPROVED",
                scope="PUBLIC",
                latest_version=1,
                author_id="usr_staff_adv",
                tags=[],
            )
            session.add_all([internal_doc, public_doc])
            await session.commit()

        # B1: Student attempts GET internal document detail
        r = await client.get("/api/v1/documents/doc_internal_01", headers=student_headers)
        if r.status_code == 403:
            record_result("B1_student_access_internal_doc", "PASS", f"Received HTTP 403 as expected: {r.json()}")
        else:
            record_result("B1_student_access_internal_doc", "FAIL", f"Expected HTTP 403, got HTTP {r.status_code} ({r.text})")

        # B2: Student listing documents should not contain internal document
        r = await client.get("/api/v1/documents", headers=student_headers)
        if r.status_code == 200:
            docs = r.json().get("data", [])
            doc_ids = [d["id"] for d in docs]
            if "doc_internal_01" not in doc_ids and "doc_public_01" in doc_ids:
                record_result("B2_student_list_documents_filter", "PASS", "Internal doc correctly filtered out for student")
            else:
                record_result("B2_student_list_documents_filter", "FAIL", f"Internal doc leaked or list improper: {doc_ids}")
        else:
            record_result("B2_student_list_documents_filter", "FAIL", f"HTTP status {r.status_code}")

        # B3: Staff user attempts soft delete document (Admin only)
        r = await client.delete("/api/v1/documents/doc_public_01", headers=staff_headers)
        if r.status_code == 403:
            record_result("B3_staff_soft_delete_doc", "PASS", f"Received HTTP 403 for non-admin delete")
        else:
            record_result("B3_staff_soft_delete_doc", "FAIL", f"Expected HTTP 403, got {r.status_code}")

        # B4: Admin soft delete document
        r = await client.delete("/api/v1/documents/doc_public_01", headers=admin_headers)
        if r.status_code == 204:
            record_result("B4_admin_soft_delete_doc", "PASS", "Admin successfully soft deleted document")
        else:
            record_result("B4_admin_soft_delete_doc", "FAIL", f"Expected HTTP 204, got {r.status_code}")

        # B5: Deleted document is hidden from listing
        r = await client.get("/api/v1/documents", headers=admin_headers)
        if r.status_code == 200:
            docs = r.json().get("data", [])
            doc_ids = [d["id"] for d in docs]
            if "doc_public_01" not in doc_ids:
                record_result("B5_deleted_doc_hidden", "PASS", "Soft deleted document hidden from document list")
            else:
                record_result("B5_deleted_doc_hidden", "FAIL", f"Soft deleted document found in list: {doc_ids}")
        else:
            record_result("B5_deleted_doc_hidden", "FAIL", f"HTTP status {r.status_code}")

        # -------------------------------------------------------------------
        # Category C: Document Lifecycle & Version Mutability Rules
        # -------------------------------------------------------------------

        # Seed document and versions
        async with session_factory() as session:
            doc_ver = Document(
                id="doc_ver_test",
                title="Tài liệu Test Lifecycle",
                type="QUYET_DINH",
                status="DRAFT",
                scope="PUBLIC",
                latest_version=1,
                author_id="usr_staff_adv",
                tags=[],
            )
            v1_draft = DocumentVersion(
                id="ver_01_draft",
                document_id="doc_ver_test",
                version_number=1,
                status="DRAFT",
                file_url="http://storage/ver1.pdf",
                file_size=1000,
                checksum="abc123sha",
                ocr_status="QUEUED",
                requires_review=False,
                created_by="usr_staff_adv",
            )
            v2_approved = DocumentVersion(
                id="ver_02_approved",
                document_id="doc_ver_test",
                version_number=2,
                status="APPROVED",
                file_url="http://storage/ver2.pdf",
                file_size=1000,
                checksum="def456sha",
                ocr_status="SUCCEEDED",
                requires_review=False,
                created_by="usr_staff_adv",
            )
            session.add_all([doc_ver, v1_draft, v2_approved])
            await session.commit()

        # C1: Update version metadata on APPROVED version should be BLOCKED (HTTP 409 Conflict)
        r = await client.patch(
            "/api/v1/documents/doc_ver_test/versions/ver_02_approved/metadata",
            json={"change_summary": "Attempting to edit approved version"},
            headers=staff_headers,
        )
        if r.status_code == 409:
            record_result("C1_patch_approved_version_metadata", "PASS", f"Blocked with 409 Conflict: {r.json()}")
        else:
            record_result("C1_patch_approved_version_metadata", "FAIL", f"Expected HTTP 409, got {r.status_code} ({r.text})")

        # C2: Approve version when OCR is QUEUED should be BLOCKED (HTTP 409 Conflict)
        r = await client.post(
            "/api/v1/documents/doc_ver_test/versions/ver_01_draft/approve",
            headers=staff_headers,
        )
        if r.status_code == 409:
            record_result("C2_approve_unprocessed_version", "PASS", f"Blocked with 409 Conflict: {r.json()}")
        else:
            record_result("C2_approve_unprocessed_version", "FAIL", f"Expected HTTP 409, got {r.status_code} ({r.text})")

        # -------------------------------------------------------------------
        # Category D: Jobs & Idempotency Key Handling
        # -------------------------------------------------------------------

        async with session_factory() as session:
            job_succeeded = Job(
                id="job_succ_01",
                type="OCR",
                status="SUCCEEDED",
                progress=100,
                idempotency_key="key_existing_01",
                target_document_id="doc_internal_01",
                target_version_id="ver_02_approved",
                created_by="usr_staff_adv",
            )
            session.add(job_succeeded)
            await session.commit()

        # D1: Cancel job that is already SUCCEEDED (HTTP 409 Conflict)
        r = await client.post("/api/v1/jobs/job_succ_01/cancel", headers=staff_headers)
        if r.status_code == 409:
            record_result("D1_cancel_succeeded_job", "PASS", f"Blocked with 409 Conflict: {r.json()}")
        else:
            record_result("D1_cancel_succeeded_job", "FAIL", f"Expected HTTP 409, got {r.status_code} ({r.text})")

        # D2: Student accessing job created by staff (HTTP 403 Forbidden)
        r = await client.get("/api/v1/jobs/job_succ_01", headers=student_headers)
        if r.status_code == 403:
            record_result("D2_student_access_staff_job", "PASS", f"Blocked with 403 Forbidden: {r.json()}")
        else:
            record_result("D2_student_access_staff_job", "FAIL", f"Expected HTTP 403, got {r.status_code} ({r.text})")

        # D3: Query non-existent document (HTTP 404 Not Found)
        r = await client.get("/api/v1/documents/doc_non_existent", headers=admin_headers)
        if r.status_code == 404:
            record_result("D3_get_non_existent_document", "PASS", "Returned 404 Not Found")
        else:
            record_result("D3_get_non_existent_document", "FAIL", f"Expected HTTP 404, got {r.status_code} ({r.text})")

    await engine.dispose()
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass

    print("\n=== SUMMARY OF ADVERSARIAL TEST HARNESS RESULTS ===")
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = sum(1 for r in test_results if r["status"] == "FAIL")
    print(f"Total: {len(test_results)} | Passed: {passed} | Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(run_adversarial_tests())
