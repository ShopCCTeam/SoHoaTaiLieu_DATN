# Báo Cáo Phân Tích & Đề Xuất Triển Khai Phase B — Document Management & Storage APIs

> **Tác giả**: Explorer 1 (Phase B Document Management)  
> **Dự án**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên (`SoHoaTaiLieu_DATN`)  
> **Ngày thực hiện**: 11/08/2026  
> **Trạng thái**: Khảo sát & Phân tích (Read-Only) — Sẵn sàng cho Implementer  

---

## 1. Tổng Quan Kế Hoạch & Phạm Vi Khảo Sát

Phase B tập trung xây dựng toàn bộ hệ thống API Quản lý & Lưu trữ Tài liệu (`/documents`, `/documents/{id}`, `/documents/{id}/versions`, `/jobs/{id}`) cùng cơ chế lưu trữ file (MinIO/S3), kiểm tra an toàn file PDF, quản lý vòng đời tài liệu/phiên bản, phân quyền chi tiết theo vai trò (RBAC Scope Filtering: `PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`), xử lý bất đồng bộ qua Job và Idempotency.

### 1.1. Kết Quả Khảo Sát Nguồn Tương Thích (Baseline Verification)
- **FastAPI Foundation**: Hiện tại `apps/api/app/` đã hoàn thành Phase 0 & Phase 1.1 với Auth (Login, Refresh Rotation, Logout, Me), Pydantic v2, Async SQLAlchemy 2.x, Alembic, structlog, middleware `RequestIdMiddleware` và chuẩn error RFC 7807 (`ApiError`, `ProblemDetail`).
- **OpenAPI Contract**: Spec tại `docs/api/openapi.yaml` định nghĩa chuẩn response envelope (`{ success: true, data: ... }`), RFC 7807 errors, các enum domain (`DocumentScope`, `DocumentStatus`, `JobStatus`, `UserRole`) và các endpoint chính (`/documents` GET & POST). Các endpoint chi tiết (`/documents/{id}`, `/documents/{id}/versions`, `/jobs/{id}`) được quy định trong `docs/api/README.md` §2.2–§2.3 và `docs/domain/document-lifecycle.md`.
- **Test Suite**: Thư mục `apps/api/tests/` đã có 84 tests unit/integration trên SQLite in-memory (aiosqlite) và Postgres fixture (`pg_engine`), hỗ trợ `db_session_factory`, `seeded_user`, `api_client` sẵn sàng cho việc mở rộng test suite Phase B.

---

## 2. Thiết Kế Cơ Sở Dữ Liệu & ORM Models (SQLAlchemy 2.x Async)

Để đáp ứng đầy đủ yêu cầu của Phase B và duy trì tính toàn vẹn dữ liệu (Domain Invariants), cần bổ sung 3 ORM models chính trong `apps/api/app/models/`:

### 2.1. Model `Document` (`app/models/document.py`, table `documents`)
Quản lý thông tin tài liệu ở cấp độ tổng thể.

```python
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True) # UUID v7
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True) # QUY_CHE, QUY_DINH, THONG_BAO, QUYET_DINH, HUONG_DAN, KHAC
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True) # DRAFT, UNDER_REVIEW, APPROVED, ARCHIVED
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="PUBLIC", index=True) # PUBLIC, STUDENT_AFFAIRS, INTERNAL
    code_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    issuing_body: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    latest_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True) # Soft delete flag

    # Relationships
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id])
    versions: Mapped[list["DocumentVersion"]] = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
```

### 2.2. Model `DocumentVersion` (`app/models/document_version.py`, table `document_versions`)
Quản lý chi tiết từng phiên bản của tài liệu.

```python
class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True) # UUID v7
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT") # DRAFT, UNDER_REVIEW, APPROVED, ARCHIVED
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False) # SHA-256 hex
    ocr_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_STARTED") # NOT_STARTED, QUEUED, PROCESSING, SUCCEEDED, FAILED
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supersedes_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True)
    superseded_by_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
```

### 2.3. Model `Job` (`app/models/job.py`, table `jobs`)
Quản lý trạng thái các tiến trình xử lý bất đồng bộ (202 Accepted polling pattern).

```python
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True) # UUID v7
    type: Mapped[str] = mapped_column(String(32), nullable=False) # OCR, EMBEDDING, INDEXING, REINDEX
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED", index=True) # QUEUED, PROCESSING, SUCCEEDED, FAILED, CANCELLED
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    target_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    target_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
```

---

## 3. Ma Trận Quyền Hạn RBAC & Logic Lọc Phạm Vi (Scope Filtering)

Tuân thủ đúng ma trận tại `docs/domain/rbac-matrix.md`:

| Vai Trò (`UserRole`) | Quyền Truy Cập Scope Tài Liệu | Thao Tác Được Phép |
|---|---|---|
| `admin` | `PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL` | Tất cả thao tác (bao gồm Soft Delete, Approve, Upload version) |
| `staff` | `PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL` | Upload, Patch metadata, Upload version mới, Trigger OCR, Approve. **KHÔNG có quyền Delete** (403 Forbidden). |
| `student` | `PUBLIC`, `STUDENT_AFFAIRS` ONLY | Chỉ xem danh sách và xem chi tiết các tài liệu thuộc 2 scope này. **Hoàn toàn KHÔNG được thấy tài liệu `INTERNAL`** (nếu truy cập trực tiếp ID → 403 Forbidden). KHÔNG được upload/sửa/xoá (403 Forbidden). |

### 3.1. Implementation Helper cho Scope Checker
```python
# app/modules/documents/dependencies.py
from app.core.enums import DocumentScopeCode, UserRole
from app.core.errors import forbidden, not_found
from app.models.user import User

def get_allowed_scopes_for_user(user: User) -> list[str]:
    if user.role in (UserRole.ADMIN, UserRole.STAFF):
        return [DocumentScopeCode.PUBLIC.value, DocumentScopeCode.STUDENT_AFFAIRS.value, DocumentScopeCode.INTERNAL.value]
    return [DocumentScopeCode.PUBLIC.value, DocumentScopeCode.STUDENT_AFFAIRS.value]

def check_document_access(document: Document, user: User) -> None:
    if document.deleted_at is not None:
        raise not_found(detail="Tài liệu không tồn tại.", code="NOT_FOUND")
    allowed = get_allowed_scopes_for_user(user)
    if document.scope not in allowed:
        raise forbidden(detail="Bạn không có quyền truy cập tài liệu này.", code="FORBIDDEN")
```

---

## 4. Chi Tiết Danh Sách API Endpoints Phase B

### 4.1. `GET /api/v1/documents`
- **Mục đích**: Lấy danh sách tài liệu phân trang + lọc scope theo role + lọc theo status, type, q.
- **Parameters**: `status` (DocumentStatus), `type` (str), `q` (full-text search), `page` (int, default=1), `limit` (int, default=20).
- **Logic**:
  - Filter `deleted_at IS NULL`.
  - Filter `scope IN (allowed_scopes)`.
  - Nếu `q` có giá trị: search trên `title`, `code_number`, `tags` (dùng `ilike` hoặc PostgreSQL full-text search).
  - Trả về envelope `{ success: true, data: [...], total, page, limit }`.

### 4.2. `POST /api/v1/documents`
- **Mục đích**: Upload PDF tài liệu mới, tạo phiên bản đầu tiên v1, tạo Job OCR và trả 202 Accepted.
- **Quyền**: `staff`, `admin`. (`student` → 403 Forbidden).
- **Header bắt buộc**: `Idempotency-Key: <uuid>`.
- **Request multipart/form-data**: `file`, `title`, `type`, `scope`, `issuing_body`, `effective_from`, `tags`, `change_summary`.
- **Validation**:
  - Kiểm tra file size ≤ 50MB (52,428,800 bytes). Nếu vượt → 413 Payload Too Large (`PAYLOAD_TOO_LARGE`).
  - Kiểm tra MIME type = `application/pdf` và Magic Bytes `%PDF-` (4 bytes đầu). Nếu sai → 415 / RFC 7807 `INVALID_FILE_TYPE`.
- **Xử lý Idempotency**:
  - Tìm `Job` với `idempotency_key`. Nếu tồn tại → trả lại kết quả Job cũ (Idempotent replay). Nếu payload khác → 409 `IDEMPOTENCY_KEY_MISMATCH`.
- **Response**: HTTP 202 Accepted:
  ```json
  {
    "success": true,
    "data": {
      "document_id": "doc_01HXYZ...",
      "job_id": "job_01HXYZ...",
      "status": "QUEUED"
    }
  }
  ```

### 4.3. `GET /api/v1/documents/{id}`
- **Mục đích**: Chi tiết 1 tài liệu + thông tin phiên bản mới nhất (`latest_version`).
- **Quyền**: Authenticated user. Kiểm tra scope access! (Nếu doc scope `INTERNAL` và user `student` → 403 Forbidden; nếu soft-deleted → 404 Not Found).

### 4.4. `PATCH /api/v1/documents/{id}`
- **Mục đích**: Cập nhật metadata tài liệu (title, type, scope, code_number, issuing_body, effective_from, effective_to, tags).
- **Quyền**: `staff`, `admin`. (`student` → 403 Forbidden).

### 4.5. `DELETE /api/v1/documents/{id}`
- **Mục đích**: Soft delete tài liệu (set `deleted_at = now()`).
- **Quyền**: **`admin` ONLY**. (`staff` và `student` → 403 Forbidden).
- **Invariants**: Tài liệu bị soft delete không bao giờ được xuất hiện trong `GET /documents`, search hoặc RAG.
- **Response**: HTTP 204 No Content.

### 4.6. `GET /api/v1/documents/{id}/versions`
- **Mục đích**: Lấy danh sách tất cả phiên bản của tài liệu.
- **Quyền**: Authenticated user (kiểm tra scope tài liệu).

### 4.7. `POST /api/v1/documents/{id}/versions`
- **Mục đích**: Upload file PDF cho phiên bản mới (tăng `version_number` + 1).
- **Quyền**: `staff`, `admin`.
- **Header bắt buộc**: `Idempotency-Key: <uuid>`.

### 4.8. `GET /api/v1/documents/{id}/versions/{vid}`
- **Mục đích**: Xem chi tiết 1 phiên bản cụ thể.

### 4.9. `PATCH /api/v1/documents/{id}/versions/{vid}/metadata`
- **Mục đích**: Sửa metadata của version.
- **Quyền**: `staff`, `admin`.
- **Lưu ý**: Nếu version đã ở trạng thái `APPROVED`, không cho phép sửa metadata → trả về 409 Conflict (`code="CONFLICT"`, detail="Phiên bản đã duyệt không được sửa").

### 4.10. `POST /api/v1/documents/{id}/versions/{vid}/ocr`
- **Mục đích**: Kích hoạt lại tiến trình OCR cho version.
- **Header bắt buộc**: `Idempotency-Key: <uuid>`.
- **Response**: HTTP 202 Accepted + `job_id`.

### 4.11. `POST /api/v1/documents/{id}/versions/{vid}/approve`
- **Mục đích**: Phê duyệt phiên bản tài liệu.
- **Quyền**: `staff`, `admin`.
- **Ràng buộc bất biến (Lifecycle Invariants)**:
  - Chỉ cho phép duyệt khi `ocr_status == "SUCCEEDED"`.
  - Chỉ cho phép duyệt khi `requires_review == False` HOẶC tất cả các OCR blocks nghi vấn đều có `review_status IN ("APPROVED", "CORRECTED")`.
  - Khi approve: set version status → `APPROVED`, cập nhật `Document.latest_version` và `Document.status` → `APPROVED`, tự động kích hoạt job Embedding / Indexing.

### 4.12. `GET /api/v1/jobs/{id}` & `POST /api/v1/jobs/{id}/cancel`
- **Mục đích**: Polling tiến độ xử lý async (mỗi 2 giây từ FE) và hủy Job nếu cần.
- **Quyền**: Owner (`created_by == user.id`) hoặc `admin`.

---

## 5. Dịch Vụ Storage & Protocol Kiểm Tra An Toàn File PDF

### 5.1. Storage Abstraction (`app/services/storage.py`)
Hỗ trợ MinIO (S3 compatible) trong môi trường live/docker và Local File Storage / Temporary Storage trong môi trường unit test:

```python
from abc import ABC, abstractmethod
from pathlib import Path

class StorageService(ABC):
    @abstractmethod
    async def upload_file(self, file_bytes: bytes, object_key: str, content_type: str) -> str:
        """Upload file và trả về file_url hoặc object_key."""
        pass

    @abstractmethod
    async def delete_file(self, object_key: str) -> None:
        pass
```

### 5.2. Protocol Kiểm Tra Magic Bytes PDF (`app/modules/documents/security.py`)
Đảm bảo ngăn chặn việc đổi đuôi file độc hại (vd: file `.exe` sửa thành `.pdf`):

```python
from app.core.errors import ApiError, status

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def validate_pdf_file(file_bytes: bytes, content_type: str, request_id: str) -> None:
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ApiError(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            code="PAYLOAD_TOO_LARGE",
            title="File vượt quá kích thước cho phép",
            detail="Kích thước tệp vượt quá 50MB.",
            request_id=request_id,
        )
    if content_type != "application/pdf":
        raise ApiError(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="INVALID_FILE_TYPE",
            title="Định dạng tệp không hợp lệ",
            detail="Chỉ hỗ trợ tệp định dạng PDF (application/pdf).",
            request_id=request_id,
        )
    # Magic bytes check
    if not file_bytes.startswith(b"%PDF-"):
        raise ApiError(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="INVALID_FILE_TYPE",
            title="Nội dung tệp không hợp lệ",
            detail="Tệp không phải là định dạng PDF hợp lệ (Magic bytes %PDF- mismatch).",
            request_id=request_id,
        )
```

---

## 6. Chiến Lược Kiểm Thử (Unit & Integration Test Suite)

Cần viết bổ sung các test file trong `apps/api/tests/` bao phủ tối thiểu 80% test coverage:

1. `test_documents_router.py`:
   - `test_list_documents_pagination_and_filters`: Kiểm tra GET `/documents` với page, limit, status, type, q.
   - `test_get_document_detail_success_and_not_found`: Kiểm tra GET `/documents/{id}` thành công & 404 cho doc không tồn tại.
   - `test_patch_document_metadata`: Kiểm tra PATCH `/documents/{id}` bởi staff.
   - `test_delete_document_soft_delete`: Kiểm tra DELETE `/documents/{id}` bởi admin thành công và bị ẩn ở list.
2. `test_documents_rbac.py`:
   - `test_student_cannot_see_internal_documents`: Sinh viên chỉ xem được `PUBLIC` và `STUDENT_AFFAIRS`.
   - `test_student_get_internal_document_returns_403`: Sinh viên GET trực tiếp doc `INTERNAL` bị 403 Forbidden.
   - `test_student_cannot_upload_or_delete`: Sinh viên POST/DELETE bị 403.
   - `test_staff_cannot_delete_document`: Staff DELETE bị 403.
3. `test_documents_upload.py`:
   - `test_upload_valid_pdf_returns_202_accepted`: Upload đúng PDF trả 202 Accepted + Job QUEUED.
   - `test_upload_missing_idempotency_key`: Thiếu header `Idempotency-Key` trả 422.
   - `test_upload_invalid_magic_bytes`: File đổi đuôi trả 415 `INVALID_FILE_TYPE`.
   - `test_upload_file_too_large`: File > 50MB trả 413.
   - `test_idempotency_replay`: Request thứ 2 cùng idempotency key trả kết quả cũ.
4. `test_documents_versions.py`:
   - `test_approve_version_invariants_check`: Phê duyệt version kiểm tra điều kiện `ocr_status == SUCCEEDED`.
5. `test_jobs_router.py`:
   - `test_get_job_status_polling`: Polling `/jobs/{id}` thành công.

---

## 7. Đánh Giá Rủi Ro & Khuyến Nghị Trình Tự Triển Khai (Roadmap cho Implementer)

### Trình Tự Triển Khai Khuyến Nghị:
1. **Bước 1 — Models & Alembic Migration**:
   Tạo `app/models/document.py`, `app/models/document_version.py`, `app/models/job.py`, import vào `app/models/__init__.py` và tạo Alembic migration `0002_documents_and_jobs.py`.
2. **Bước 2 — Schemas & Security Helpers**:
   Tạo `app/modules/documents/schemas.py`, `app/modules/jobs/schemas.py`, `app/modules/documents/security.py` (magic bytes & file validation).
3. **Bước 3 — Service & Storage Layer**:
   Tạo `app/services/storage.py` và `app/modules/documents/service.py` thực thi các hàm DB query, RBAC scope filter, soft delete và version increment.
4. **Bước 4 — Router & Dependencies**:
   Tạo `app/modules/documents/router.py` & `app/modules/jobs/router.py`, kết nối router vào `app/main.py`.
5. **Bước 5 — Pytest Suite & Coverage Check**:
   Viết 5 test files và chạy `uv run pytest` đảm bảo 100% test pass và coverage ≥ 80%.

---

*Báo cáo phân tích hoàn tất. Chuyển giao thông tin chi tiết qua Handoff Report.*
