"""DocumentChunk ORM model.

Table: document_chunks
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.document_version import DocumentVersion


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_version_index", "version_id", "chunk_index"),
        Index("ix_document_chunks_document_page", "document_id", "page_number"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Document Chunk ID (UUID v4)",
    )
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Phiên bản tài liệu chứa chunk này",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID tài liệu gốc",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Thứ tự xuất hiện của chunk trong phiên bản (0-indexed)",
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Số trang chính chứa chunk (1-indexed)",
    )
    block_ids: Mapped[Any] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Danh sách ID các OCRBlock thuộc chunk này",
    )
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Nội dung văn bản bóc tách của chunk",
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Số lượng từ/token trong chunk",
    )
    bbox: Mapped[Any] = mapped_column(
        JSON,
        nullable=False,
        comment="Min-Max Envelope Bounding Box dạng [x0, y0, x1, y1]",
    )
    embedding: Mapped[Any] = mapped_column(
        Vector(1024).with_variant(JSON, "sqlite"),
        nullable=False,
        comment="Vector embedding 1024 chiều (BGE-M3)",
    )
    fulltext_tsv: Mapped[Any | None] = mapped_column(
        TSVECTOR().with_variant(Text, "sqlite"),
        nullable=True,
        comment="Full-text search tsvector",
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
    document: Mapped[Document] = relationship("Document", foreign_keys=[document_id])
    version: Mapped[DocumentVersion] = relationship("DocumentVersion", foreign_keys=[version_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentChunk id={self.id} doc={self.document_id}>"
