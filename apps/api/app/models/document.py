"""Document ORM model.

Table: documents
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DocumentScopeCode
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document_version import DocumentVersion
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Document ID (UUID v4 or doc_01...)",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # QUY_CHE, QUY_DINH, THONG_BAO, QUYET_DINH, HUONG_DAN, KHAC
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT", index=True
    )  # DRAFT, UNDER_REVIEW, APPROVED, ARCHIVED
    scope: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DocumentScopeCode.PUBLIC.value,
        index=True,
    )  # PUBLIC, STUDENT_AFFAIRS, INTERNAL
    code_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    issuing_body: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    latest_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
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
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationships
    author: Mapped[User] = relationship("User", foreign_keys=[author_id])
    versions: Mapped[list[DocumentVersion]] = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number.desc()",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Document id={self.id} title={self.title} scope={self.scope}>"
