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
        Index("ix_ocr_blocks_version_page", "version_id", "page_number"),
        Index("ix_ocr_blocks_version_page_index", "version_id", "page_number", "block_index"),
        Index(
            "ix_ocr_blocks_review_status_composite",
            "version_id",
            "requires_review",
            "review_status",
        ),
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
        comment="ID trang OCR tương ứng",
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
        comment="Văn bản OCR nhận dạng được",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Độ tin cậy của OCR (0.0 đến 1.0)",
    )
    bbox: Mapped[Any] = mapped_column(
        JSON,
        nullable=False,
        comment="Bounding Box JSONB dạng [x0, y0, x1, y1]",
    )
    requires_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True nếu confidence < threshold (vd: 0.80)",
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
        comment="Văn bản đã qua sửa đổi (nếu có)",
    )
    original_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Văn bản gốc ban đầu do OCR bóc tách",
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
        comment="ID cán bộ thực hiện review",
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
