"""DocumentScope lookup table.

Reference data — seed sẵn 3 rows: PUBLIC, STUDENT_AFFAIRS, INTERNAL.
"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import DocumentScopeCode
from app.db.base import Base


class DocumentScope(Base):
    __tablename__ = "document_scopes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        comment="Enum: PUBLIC / STUDENT_AFFAIRS / INTERNAL",
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    @property
    def code_enum(self) -> DocumentScopeCode:
        return DocumentScopeCode(self.code)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentScope code={self.code}>"
