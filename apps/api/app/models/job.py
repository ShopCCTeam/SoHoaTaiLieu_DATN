"""Job ORM model.

Table: jobs
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.document_version import DocumentVersion
    from app.models.user import User


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Job ID (UUID v4)",
    )
    type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # OCR, EMBEDDING, INDEXING, REINDEX
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="QUEUED", index=True
    )  # QUEUED, PROCESSING, SUCCEEDED, FAILED, CANCELLED
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    target_document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    target_version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    target_document: Mapped[Document | None] = relationship(
        "Document", foreign_keys=[target_document_id]
    )
    target_version: Mapped[DocumentVersion | None] = relationship(
        "DocumentVersion", foreign_keys=[target_version_id]
    )
    creator: Mapped[User] = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Job id={self.id} type={self.type} status={self.status}>"
