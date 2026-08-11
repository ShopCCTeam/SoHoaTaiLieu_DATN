"""DocumentVersion ORM model.

Table: document_versions
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.ocr_block import OCRBlock
    from app.models.ocr_page import OCRPage
    from app.models.user import User


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Document version ID (UUID v4)",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT"
    )  # DRAFT, UNDER_REVIEW, APPROVED, ARCHIVED
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hex
    ocr_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="NOT_STARTED"
    )  # NOT_STARTED, QUEUED, PROCESSING, SUCCEEDED, FAILED
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supersedes_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("document_versions.id"), nullable=True
    )
    superseded_by_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("document_versions.id"), nullable=True
    )
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    document: Mapped[Document] = relationship("Document", back_populates="versions")
    creator: Mapped[User] = relationship("User", foreign_keys=[created_by])
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

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentVersion id={self.id} doc={self.document_id} v={self.version_number}>"
