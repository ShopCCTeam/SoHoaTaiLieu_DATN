# Phân Tích Thiết Kế Database Models, Alembic Migration & Storage cho OCR Pipeline (Phase C)

**Tác giả**: Explorer 2 (Phase C - OCR Pipeline)  
**Dự án**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên (`SoHoaTaiLieu_DATN`)  
**Ngày thực hiện**: 2026-08-11  
**Trạng thái**: Đã hoàn thành (Read-Only Exploration & Architectural Design)  

---

## 1. Tổng Quan & Bối Cảnh Hệ Thống (Executive Summary)

Trong kiến trúc tổng thể của hệ thống `SoHoaTaiLieu_DATN`, Phase C đóng vai trò xử lý tự động OCR (dùng PaddleOCR / Tesseract) cho các phiên bản tài liệu PDF (`document_versions`). 

Kết quả đầu ra của OCR không chỉ phục vụ việc trích xuất văn bản thô (raw text) để đánh chỉ mục RAG (BGE-M3 + pgvector), mà còn cung cấp thông tin chi tiết đến cấp độ **trang (`ocr_pages`)** và **khối văn bản (`ocr_blocks`)** kèm tọa độ Bounding Box (`bbox`), độ tin cậy (`confidence`), cùng với quy trình xem xét/hiệu chỉnh thủ công (Human-in-the-Loop OCR Review) tại Frontend (Phase F3).

Báo cáo này phân tích chi tiết thiết kế ORM Models (SQLAlchemy 2.x Async), Alembic Migrations, chiến lược đánh chỉ mục (Database Indexing), cũng như định dạng lưu trữ JSONB cho kết quả OCR.

---

## 2. Thiết Kế Cấu Trúc Bảng DB (`ocr_pages` & `ocr_blocks`)

Để tối ưu khả năng truy vấn theo từng trang cho trình xem tài liệu (split-view viewer tại FE) và truy vấn toàn bộ khối văn bản của một phiên bản tài liệu, hệ thống thiết kế 2 bảng quan hệ thuộc Phase C:

1. **`ocr_pages`**: Lưu thông tin tổng quan của từng trang trong một `document_version` (số trang, kích thước WxH, tổng số block, trạng thái xử lý trang, đường dẫn ảnh preview trang trên MinIO/S3).
2. **`ocr_blocks`**: Lưu thông tin chi tiết từng khối văn bản do OCR nhận dạng được (tọa độ `bbox`, nội dung nhận dạng, độ tin cậy `confidence`, trạng thái cờ `requires_review`, trạng thái review `review_status`, văn bản đã qua hiệu chỉnh `edited_text`, người review `reviewed_by`).

### 2.1. Sơ Đồ Quan Hệ Sơ Bộ (Entity-Relationship Diagram)

```
[documents] (1) <--- (N) [document_versions] (1) <--- (N) [ocr_pages]
                                |                              | (1)
                                |                              |
                                +---------------------(N) <----+ (N) [ocr_blocks]
                                                                  |
                                [users] (1) <--- (N) (reviewed_by)+
                                [jobs]  (1) <--- (N) (job_id)     +
```

---

## 3. Chi Tiết Trường Dữ Liệu & Mã ORM Models (SQLAlchemy 2.x Async)

### 3.1. Bổ Sung Enum Trong `app/core/enums.py`

Cần bổ sung enum `OCRReviewStatus` và `OCRPageStatus` vào `apps/api/app/core/enums.py` để dùng chung giữa ORM Models và Pydantic Schemas:

```python
# app/core/enums.py
from enum import StrEnum

class OCRReviewStatus(StrEnum):
    """Trạng thái review cho từng block có requires_review=True."""
    PENDING = "PENDING"      # Chờ staff/admin xem xét
    APPROVED = "APPROVED"    # Đã duyệt - văn bản OCR nhận dạng đúng
    REJECTED = "REJECTED"    # Đã loại bỏ - block rác / nhiễu không thuộc nội dung
    CORRECTED = "CORRECTED"  # Đã sửa - văn bản đã được nhân viên hiệu chỉnh lại

class OCRPageStatus(StrEnum):
    """Trạng thái xử lý OCR cho từng trang độc lập."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
```

---

### 3.2. Model `OCRPage` (`apps/api/app/models/ocr_page.py`)

Bảng `ocr_pages` quản lý metadata cấp độ trang tài liệu:

```python
"""OCRPage ORM model.

Table: ocr_pages
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OCRPageStatus
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document_version import DocumentVersion
    from app.models.ocr_block import OCRBlock


class OCRPage(Base):
    __tablename__ = "ocr_pages"
    __table_args__ = (
        UniqueConstraint("version_id", "page_number", name="uq_ocr_pages_version_page"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="OCR Page ID (UUID v4)",
    )
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Phiên bản tài liệu sở hữu trang này",
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Số trang (1-indexed: 1, 2, 3...)",
    )
    width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Chiều rộng trang (PDF points hoặc px)",
    )
    height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Chiều cao trang (PDF points hoặc px)",
    )
    image_key: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="MinIO/S3 object key ảnh preview trang (vd: docs/doc_1/v1/pages/1.png)",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=OCRPageStatus.COMPLETED.value,
    )
    block_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Tổng số block trong trang",
    )
    has_warnings: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True nếu có ít nhất 1 block cần review trong trang này",
    )
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

    # Relationships
    version: Mapped[DocumentVersion] = relationship("DocumentVersion", back_populates="ocr_pages")
    blocks: Mapped[list[OCRBlock]] = relationship(
        "OCRBlock",
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="OCRBlock.block_index.asc()",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OCRPage id={self.id} version_id={self.version_id} page={self.page_number}>"
```

---

### 3.3. Model `OCRBlock` (`apps/api/app/models/ocr_block.py`)

Bảng `ocr_blocks` lưu trữ toàn bộ các đoạn/khối văn bản nhận dạng được:

```python
"""OCRBlock ORM model.

Table: ocr_blocks
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OCRReviewStatus
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document_version import DocumentVersion
    from app.models.job import Job
    from app.models.ocr_page import OCRPage
    from app.models.user import User


class OCRBlock(Base):
    __tablename__ = "ocr_blocks"
    __table_args__ = (
        # Composite Index cho truy vấn lấy toàn bộ blocks của 1 trang cụ thể (Yêu cầu cốt lõi #4)
        Index("ix_ocr_blocks_version_page", "version_id", "page_number"),
        # Composite Index hỗ trợ lấy danh sách block theo thứ tự hiển thị
        Index("ix_ocr_blocks_version_page_index", "version_id", "page_number", "block_index"),
        # Composite Index hỗ trợ bù tải màn hình Review tại FE (F3) cho các block chưa duyệt
        Index("ix_ocr_blocks_review_status", "version_id", "requires_review", "review_status"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="OCR Block ID (UUID v4)",
    )
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID phiên bản tài liệu chứa block này",
    )
    page_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ocr_pages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="ID trang OCR tương ứng (optional lookup link)",
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Số trang chứa block (1-indexed)",
    )
    block_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Thứ tự xuất hiện của block trong trang (0-indexed)",
    )
    text_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Văn bản OCR nhận dạng được (hiện tại)",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Độ tin cậy của thuật toán OCR (0.0 đến 1.0)",
    )
    bbox: Mapped[list[float]] = mapped_column(
        JSON,
        nullable=False,
        comment="Bounding Box JSONB dạng [x0, y0, x1, y1] theo hệ tọa độ PDF",
    )
    requires_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True nếu confidence < threshold (vd: 0.90)",
    )
    review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=OCRReviewStatus.PENDING.value,
        index=True,
        comment="PENDING, APPROVED, REJECTED, CORRECTED",
    )
    edited_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Văn bản đã qua sửa đổi bởi người dùng (nếu có)",
    )
    original_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Văn bản gốc ban đầu do OCR bóc tách (trước khi sửa)",
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Job ID tạo ra OCR block này",
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID của cán bộ thực hiện review/edit",
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Thời điểm hoàn tất review",
    )
    processing_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Thời gian OCR xử lý riêng cho block (ms)",
    )
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

    # Relationships
    version: Mapped[DocumentVersion] = relationship("DocumentVersion", back_populates="ocr_blocks")
    page: Mapped[OCRPage | None] = relationship("OCRPage", back_populates="blocks")
    job: Mapped[Job | None] = relationship("Job", foreign_keys=[job_id])
    reviewer: Mapped[User | None] = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OCRBlock id={self.id} page={self.page_number} conf={self.confidence:.2f}>"
```

---

### 3.4. Cập Nhật Quan Hệ Trong `DocumentVersion` (`apps/api/app/models/document_version.py`)

Cần bổ sung các relationship phương hướng 2 chiều trong `DocumentVersion`:

```python
# Sửa đổi trong app/models/document_version.py
if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.ocr_block import OCRBlock
    from app.models.ocr_page import OCRPage
    from app.models.user import User

class DocumentVersion(Base):
    # ... các cột hiện tại ...

    # Bổ sung Relationships cho OCR Pipeline Phase C
    ocr_pages: Mapped[list[OCRPage]] = relationship(
        "OCRPage",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="OCRPage.page_number.asc()",
    )
    ocr_blocks: Mapped[list[OCRBlock]] = relationship(
        "OCRBlock",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="(OCRBlock.page_number.asc(), OCRBlock.block_index.asc())",
    )
```

---

## 4. Alembic Migration Script Thiết Kế Cho Phase C (`0004_ocr_pages_and_blocks.py`)

Dưới đây là mã nguồn thiết kế migration script hoàn chỉnh cho Alembic (`apps/api/alembic/versions/0004_ocr_pages_and_blocks.py`):

```python
"""ocr_pages and ocr_blocks tables for Phase C OCR Pipeline.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-11
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Tạo bảng ocr_pages
    op.create_table(
        "ocr_pages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("image_key", sa.String(length=512), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="COMPLETED"
        ),
        sa.Column("block_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "has_warnings", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["version_id"], ["document_versions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("version_id", "page_number", name="uq_ocr_pages_version_page"),
    )
    op.create_index("ix_ocr_pages_version_id", "ocr_pages", ["version_id"])
    op.create_index(
        "ix_ocr_pages_version_page", "ocr_pages", ["version_id", "page_number"]
    )

    # 2. Tạo bảng ocr_blocks
    op.create_table(
        "ocr_blocks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("page_id", sa.String(length=36), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column(
            "requires_review",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("edited_text", sa.Text(), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "processing_time_ms",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["version_id"], ["document_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["page_id"], ["ocr_pages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"], ondelete="SET NULL"
        ),
    )
    # Đánh chỉ mục (Indexes)
    op.create_index("ix_ocr_blocks_version_id", "ocr_blocks", ["version_id"])
    op.create_index("ix_ocr_blocks_page_id", "ocr_blocks", ["page_id"])
    op.create_index("ix_ocr_blocks_page_number", "ocr_blocks", ["page_number"])
    op.create_index("ix_ocr_blocks_requires_review", "ocr_blocks", ["requires_review"])
    op.create_index("ix_ocr_blocks_review_status_single", "ocr_blocks", ["review_status"])
    op.create_index("ix_ocr_blocks_job_id", "ocr_blocks", ["job_id"])

    # Composite indexes chuyên biệt
    op.create_index(
        "ix_ocr_blocks_version_page", "ocr_blocks", ["version_id", "page_number"]
    )
    op.create_index(
        "ix_ocr_blocks_version_page_index",
        "ocr_blocks",
        ["version_id", "page_number", "block_index"],
    )
    op.create_index(
        "ix_ocr_blocks_review_status",
        "ocr_blocks",
        ["version_id", "requires_review", "review_status"],
    )


def downgrade() -> None:
    # Xóa bảng ocr_blocks & indexes
    op.drop_index("ix_ocr_blocks_review_status", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_version_page_index", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_version_page", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_job_id", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_review_status_single", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_requires_review", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_page_number", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_page_id", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_version_id", table_name="ocr_blocks")
    op.drop_table("ocr_blocks")

    # Xóa bảng ocr_pages & indexes
    op.drop_index("ix_ocr_pages_version_page", table_name="ocr_pages")
    op.drop_index("ix_ocr_pages_version_id", table_name="ocr_pages")
    op.drop_table("ocr_pages")
```

---

## 5. Phân Tích Chiến Lược Đánh Chỉ Mục (Indexing Strategy)

1. **Composite Index `(version_id, page_number)` trên `ocr_blocks`**:
   - **Tác dụng**: Giúp FE truy vấn tức thì toàn bộ OCR block thuộc trang $N$ của phiên bản $V$ trong màn hình review split-view (FE F3 component `ocr-review-pane.tsx`).
   - **Query Pattern**: `SELECT * FROM ocr_blocks WHERE version_id = :v AND page_number = :p ORDER BY block_index ASC`.
   - **Hiệu năng**: B-Tree composite index loại bỏ toàn bộ việc Full Table Scan.

2. **Composite Index `(version_id, page_number, block_index)`**:
   - **Tác dụng**: Phục vụ sắp xếp tự nhiên theo dòng/khối văn bản trên trang PDF mà không cần Sort stage trong PostgreSQL execution plan.

3. **Composite Index `(version_id, requires_review, review_status)`**:
   - **Tác dụng**: Phục vụ API tổng hợp tiến độ review: kiểm tra xem phiên bản tài liệu còn block nào `requires_review = true` và `review_status = 'PENDING'` hay không trước khi chuyển trạng thái phiên bản sang `APPROVED`.

---

## 6. Phân Tích Định Dạng Lưu Trữ JSONB `bbox` & Đồng Bộ Contract

### 6.1. Định Dạng `bbox`
- **Mảng JSON 4 phần tử**: `[x0, y0, x1, y1]` đại diện cho `[x_min, y_min, x_max, y_max]`.
- **Hệ tọa độ (Coordinate System)**: Tọa độ chuẩn của file PDF (PDF User Unit points, thông thường 72 points/inch).
- **Đồng bộ Frontend**: 
  Tại Frontend Next.js (`apps/web/lib/api/mappers.ts`), hàm `apiOCRBlockToDomain` sẽ nhận `bbox` mảng 4 số này và map vào component canvas rendering thông qua helper chuyển đổi sang pixel hiển thị.

### 6.2. Đối Chiếu OpenAPI Contract 3.1 (`docs/api/openapi.yaml`)
Định dạng DTO được trả về từ API backend sẽ có cấu trúc 1:1 với OpenAPI schema `OCRBlock`:

```json
{
  "id": "block_01HXYZ...",
  "ocr_job_id": "job_01HABC...",
  "version_id": "ver_01HDEF...",
  "page_number": 1,
  "block_index": 0,
  "bbox": [54.0, 720.5, 540.0, 745.0],
  "text": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
  "confidence": 0.985,
  "requires_review": false,
  "review_status": "APPROVED",
  "edited_text": null,
  "original_text": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
  "reviewed_by": null,
  "reviewed_at": null,
  "processing_time_ms": 142
}
```

---

## 7. Đánh Giá Khả Năng Tương Thích & Tính Khả Thi

- **Khả năng tương thích ngược**: Thiết kế hoàn toàn khớp với mock data fixtures `MOCK_OCR_BLOCKS` tại `apps/web/lib/mocks/fixtures.ts` và OpenAPI spec `docs/api/openapi.yaml`.
- **Hỗ trợ TDD & Async SQLAlchemy**: Thiết kế dùng type annotations `Mapped[...]` chuẩn SQLAlchemy 2.x, hoàn toàn tương thích với `asyncpg` và `aiosqlite` (dùng cho pytest in-memory).

---

## 8. Kết Luận & Đề Xuất Bước Tiếp Theo

1. Kiến trúc bảng `ocr_pages` và `ocr_blocks` đã sẵn sàng để chuyển giao sang bước Implementation (Phase C Backend Implementer).
2. Khi tiến hành tạo file trong `apps/api/app/models/`, cần đăng ký `OCRPage` và `OCRBlock` vào `apps/api/app/models/__init__.py` để Alembic autodiscovery nhận diện chính xác.
