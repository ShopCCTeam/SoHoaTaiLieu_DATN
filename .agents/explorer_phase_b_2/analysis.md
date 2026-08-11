# Báo Cáo Phân Tích DB Models, Alembic Migration & MinIO Storage cho Phase B

> **Dự án**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên (SoHoaTaiLieu_DATN)  
> **Tác giả**: Explorer 2 (Phase B - Database & Storage)  
> **Thư mục làm việc**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_2`  
> **Thời gian**: 2026-08-11  

---

## 1. Tổng Quan & Mục Tiêu Phân Tích

Phase B (Document Management & Storage) tập trung vào việc quản lý lưu trữ văn bản, quản lý các phiên bản tài liệu (versioning), và tích hợp lưu trữ file nhị phân qua dịch vụ MinIO S3. Báo cáo này tiến hành nghiên cứu chi tiết 4 khía cạnh chính:

1. **Khảo sát hiện trạng DB Models & Alembic Migrations**: Phân tích các mô hình ORM và migration đã có (`users`, `document_scopes`, `refresh_sessions`).
2. **Thiết kế SQLAlchemy Async Models**: Xây dựng mô hình cho 2 bảng cốt lõi `documents` và `document_versions` với UUID PK, Foreign Keys, Metadata JSONB, Enum Scope/Status, timestamps và soft delete.
3. **Thiết kế Dịch vụ Tích hợp MinIO S3 (`storage.py`)**: Đóng gói các thao tác bucket, upload, download, presigned URL, delete và xử lý lỗi chuẩn domain.
4. **Chiến lược Test Fixture & Seed Data**: Thiết lập SQLite/Postgres test compatibility, mock S3 client fixture và dữ liệu mẫu cho pytest.

---

## 2. Khảo Sát Hiện Trạng Database & Alembic

### 2.1. Các mô hình hiện có (`apps/api/app/models/`)

- **`User`** (`user.py`):
  - Primary Key `id`: String(36) đại diện cho UUID.
  - Các trường: `email`, `password_hash`, `full_name`, `role` (enum: `admin`, `staff`, `student`), `department`, `is_active`, `created_at`, `updated_at`.
- **`DocumentScope`** (`document_scope.py`):
  - Primary Key `id`: Integer (autoincrement).
  - Trường `code`: Unique String(32) mapping với `DocumentScopeCode` (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`).
  - Seed sẵn 3 dòng quy định phạm vi truy cập tài liệu.
- **`RefreshSession`** (`refresh_session.py`):
  - Đáng chú ý: Định nghĩa TypeDecorator `_UUID` (dùng `CHAR(36)` trên SQLite và `postgresql.UUID` trên Postgres) và `_INet` (dùng `String(45)` trên SQLite và `postgresql.INET` trên Postgres).
  - Mô hình này chứng minh nguyên tắc **Database Portability**: Code chạy tốt cả với PostgreSQL trong production và SQLite in-memory / file trong unit tests.

### 2.2. Tiến trình Alembic Migrations (`apps/api/alembic/versions/`)

- `0001_users_and_scopes.py`: Khởi tạo bảng `users` và `document_scopes`, seed 3 bản ghi scope mặc định.
- `0002_refresh_sessions.py`: Khởi tạo bảng `refresh_sessions` phục vụ JWT Refresh Token Rotation và Family Revocation.

---

## 3. Thiết Kế SQLAlchemy Async Models Cho Phase B

Cần bổ sung 2 mô hình ORM mới vào `apps/api/app/models/`: `document.py` và `document_version.py`.

### 3.1. Mô hình `Document` (`apps/api/app/models/document.py`)

```python
"""Document ORM model — Lưu thông tin tổng quan của văn bản/tài liệu."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator, JSON

from app.core.enums import DocumentScopeCode
from app.db.base import Base
from app.models.refresh_session import _UUID


class _JSONB(TypeDecorator[Any]):
    """Store JSONB on PostgreSQL, JSON on SQLite cho test compatibility."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        _UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Primary key UUID v4/v7",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="QUY_CHE | QUY_DINH | THONG_BAO | QUYET_DINH | HUONG_DAN | KHAC",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="DRAFT",
        index=True,
        comment="DRAFT | UNDER_REVIEW | APPROVED | ARCHIVED",
    )
    scope_code: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("document_scopes.code", onupdate="CASCADE"),
        nullable=False,
        default=DocumentScopeCode.PUBLIC.value,
        index=True,
    )
    code_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    issuing_body: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    latest_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    author_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tags: Mapped[list[str] | None] = mapped_column(_JSONB(), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(_JSONB(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id])
    scope: Mapped["DocumentScope"] = relationship("DocumentScope", foreign_keys=[scope_code])
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number.desc()",
    )
```

### 3.2. Mô hình `DocumentVersion` (`apps/api/app/models/document_version.py`)

```python
"""DocumentVersion ORM model — Lưu chi tiết từng phiên bản file tài liệu."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.document import _JSONB
from app.models.refresh_session import _UUID


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_versions_doc_ver"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        _UUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        _UUID(),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="DRAFT",
        index=True,
        comment="DRAFT | UNDER_REVIEW | APPROVED | ARCHIVED",
    )
    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="S3 object key: documents/{doc_id}/v{version}/{checksum}.pdf",
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Kích thước file tính theo bytes")
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/pdf")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="SHA-256 hex digest")
    
    ocr_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="NOT_STARTED",
        index=True,
        comment="NOT_STARTED | QUEUED | PROCESSING | SUCCEEDED | FAILED",
    )
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    
    supersedes_version_id: Mapped[uuid.UUID | None] = mapped_column(
        _UUID(),
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    superseded_by_version_id: Mapped[uuid.UUID | None] = mapped_column(
        _UUID(),
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(_JSONB(), nullable=True)
    
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
```

---

## 4. Kế Hoạch Alembic Migration (`0003_documents_and_versions.py`)

Viết file migration thứ 3 trong `apps/api/alembic/versions/0003_documents_and_versions.py` với nội dung cấu trúc:

```python
"""add documents and document_versions tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-11
"""
from __future__ import annotations

from typing import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Bảng documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("scope_code", sa.String(length=32), nullable=False, server_default="PUBLIC"),
        sa.Column("code_number", sa.String(length=100), nullable=True),
        sa.Column("issuing_body", sa.String(length=255), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("latest_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("author_id", sa.String(length=36), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scope_code"], ["document_scopes.code"], onupdate="CASCADE"),
    )
    op.create_index("ix_documents_title", "documents", ["title"])
    op.create_index("ix_documents_type", "documents", ["type"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_scope_code", "documents", ["scope_code"])
    op.create_index("ix_documents_code_number", "documents", ["code_number"])
    op.create_index("ix_documents_author_id", "documents", ["author_id"])
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])

    # 2. Bảng document_versions
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False, server_default="application/pdf"),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("ocr_status", sa.String(length=32), nullable=False, server_default="NOT_STARTED"),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("supersedes_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("superseded_by_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_version_id"], ["document_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["superseded_by_version_id"], ["document_versions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_versions_doc_ver"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_status", "document_versions", ["status"])
    op.create_index("ix_document_versions_checksum", "document_versions", ["checksum"])
    op.create_index("ix_document_versions_ocr_status", "document_versions", ["ocr_status"])
    op.create_index("ix_document_versions_requires_review", "document_versions", ["requires_review"])
    op.create_index("ix_document_versions_deleted_at", "document_versions", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("document_versions")
    op.drop_table("documents")
```

---

## 5. Thiết Kế Dịch Vụ MinIO S3 Storage Integration (`storage.py`)

### 5.1. Cấu hình MinIO Settings (Đã khảo sát trong `app/core/config.py`)

Các tham số môi trường:
- `minio_endpoint`: default `"localhost:9000"`
- `minio_access_key`: default `"minioadmin"`
- `minio_secret_key`: default `"minioadmin"`
- `minio_bucket`: default `"ctsv-documents"`
- `minio_secure`: default `False`

### 5.2. Mô hình dịch vụ `StorageService` (`apps/api/app/services/storage.py`)

Dịch vụ này đóng gói SDK `minio.Minio` và chạy bất đồng bộ thông qua `asyncio.to_thread` (hoặc executor) để đảm bảo FastAPI event loop không bị block.

```python
"""MinIO S3 Storage Service cho quản lý lưu trữ file văn bản PDF."""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass
from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error
from structlog import get_logger

from app.core.config import Settings, get_settings

_logger = get_logger(__name__)


@dataclass(frozen=True)
class StorageUploadResult:
    bucket: str
    object_name: str
    size: int
    etag: str


class StorageService:
    """MinIO S3 storage wrapper service."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = Minio(
            endpoint=self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key.get_secret_value(),
            secure=self.settings.minio_secure,
        )
        self.bucket = self.settings.minio_bucket

    async def ensure_bucket_exists(self) -> None:
        """Đảm bảo bucket tồn tại khi khởi động app."""
        def _check() -> None:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                _logger.info("minio_bucket_created", bucket=self.bucket)
        await asyncio.to_thread(_check)

    async def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/pdf",
        metadata: dict[str, str] | None = None,
    ) -> StorageUploadResult:
        """Upload file dưới dạng bytes vào MinIO S3."""
        stream = io.BytesIO(data)
        length = len(data)

        def _upload() -> StorageUploadResult:
            res = self.client.put_object(
                bucket_name=self.bucket,
                object_name=object_name,
                data=stream,
                length=length,
                content_type=content_type,
                metadata=metadata,
            )
            return StorageUploadResult(
                bucket=res.bucket_name,
                object_name=res.object_name,
                size=length,
                etag=res.etag,
            )

        return await asyncio.to_thread(_upload)

    async def download_bytes(self, object_name: str) -> bytes:
        """Tải dữ liệu file từ MinIO S3."""
        def _download() -> bytes:
            response = None
            try:
                response = self.client.get_object(self.bucket, object_name)
                return response.read()
            finally:
                if response:
                    response.close()
                    response.release_conn()

        return await asyncio.to_thread(_download)

    async def get_presigned_url(
        self,
        object_name: str,
        expires: int = 3600,
        filename: str | None = None,
    ) -> str:
        """Tạo URL xem/tải file có thời hạn (Presigned GET URL)."""
        extra_query = {}
        if filename:
            extra_query["response-content-disposition"] = f'inline; filename="{filename}"'

        def _get_url() -> str:
            return self.client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=object_name,
                expires=timedelta(seconds=expires),
                extra_query_params=extra_query if filename else None,
            )

        return await asyncio.to_thread(_get_url)

    async def delete_file(self, object_name: str) -> None:
        """Xoá file khỏi MinIO bucket."""
        def _delete() -> None:
            self.client.remove_object(self.bucket, object_name)

        await asyncio.to_thread(_delete)

    async def file_exists(self, object_name: str) -> bool:
        """Kiểm tra sự tồn tại của object."""
        def _stat() -> bool:
            try:
                self.client.stat_object(self.bucket, object_name)
                return True
            except S3Error as err:
                if err.code == "NoSuchKey":
                    return False
                raise

        return await asyncio.to_thread(_stat)
```

---

## 6. Chiến Lược Seed & Test Fixture Cho Pytest

### 6.1. Mock Storage Service Fixture

Để unit tests và integration test chạy nhanh mà không phụ thuộc vào MinIO service thực tế:

```python
# Fixture mock storage cho unit test
class MockStorageService:
    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    async def ensure_bucket_exists() -> None:
        pass

    async def upload_bytes(self, data: bytes, object_name: str, **kwargs) -> StorageUploadResult:
        self._files[object_name] = data
        return StorageUploadResult(bucket="ctsv-documents", object_name=object_name, size=len(data), etag="mock_etag")

    async def download_bytes(self, object_name: str) -> bytes:
        if object_name not in self._files:
            raise KeyError(f"File {object_name} not found")
        return self._files[object_name]

    async def get_presigned_url(self, object_name: str, **kwargs) -> str:
        return f"http://testserver/storage/{object_name}"

    async def file_exists(self, object_name: str) -> bool:
        return object_name in self._files


@pytest.fixture
def mock_storage() -> MockStorageService:
    return MockStorageService()
```

### 6.2. Document Fixture cho Pytest

Thêm `seeded_document` vào `tests/conftest.py`:

```python
@pytest.fixture
async def seeded_document(db_session_factory, seeded_user) -> Document:
    async with db_session_factory() as session:
        doc = Document(
            id=uuid.uuid4(),
            title="Quy định Học bổng Khuyến khích Học tập 2026",
            type="QUY_DINH",
            status="APPROVED",
            scope_code="PUBLIC",
            code_number="123/QĐ-CTSV",
            issuing_body="Phòng CTSV",
            latest_version=1,
            author_id=seeded_user.id,
            tags=["hoc_bong", "ctsv"],
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        yield doc
```

---

## 7. Đánh Giá Rủi Ro & Đề Xuất Phối hợp

1. **Khả năng tương thích SQLite trong Unit Test**:
   - `Document` và `DocumentVersion` sử dụng `_UUID` và `_JSONB` custom TypeDecorator để tự chuyển sang `CHAR(36)` và `JSON` khi test với SQLite in-memory/file.
2. **Khóa Ngoại Cascade**:
   - Khi xoá `Document`, bảng `document_versions` sẽ bị xoá tự động (`ondelete="CASCADE"`). Tuy nhiên ứng dụng ưu tiên **Soft Delete** (`deleted_at`), nên dữ liệu lịch sử vẫn được bảo toàn.
3. **Phân quyền dữ liệu (RBAC Scope Filter)**:
   - Trong Phase B, các query GET `/documents` phải lọc `scope_code` dựa trên `user.role` (Student chỉ thấy `PUBLIC` & `STUDENT_AFFAIRS`, Staff/Admin thấy toàn bộ).

---
