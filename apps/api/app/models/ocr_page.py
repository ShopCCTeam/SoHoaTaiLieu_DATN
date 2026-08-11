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
        comment="MinIO/S3 object key ảnh preview trang",
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
