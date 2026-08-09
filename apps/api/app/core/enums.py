"""Enum types chia sẻ giữa ORM models và Pydantic schemas.

Giữ DTO (FE-facing) snake_case và DB enum uppercase cho khớp PostgreSQL convention.
"""
from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    """User role — đồng bộ với OpenAPI `User.role` enum."""

    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"


class DocumentScopeCode(StrEnum):
    """Document visibility scope — đồng bộ với OpenAPI `DocumentScope` enum."""

    PUBLIC = "PUBLIC"
    STUDENT_AFFAIRS = "STUDENT_AFFAIRS"
    INTERNAL = "INTERNAL"
