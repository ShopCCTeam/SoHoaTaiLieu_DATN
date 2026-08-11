"""Dependencies for Documents module (RBAC scope filtering & permission enforcement)."""

from __future__ import annotations

from fastapi import Depends, Header

from app.core.enums import DocumentScopeCode, UserRole
from app.core.errors import forbidden, not_found, validation_error
from app.models.document import Document
from app.models.user import User
from app.modules.auth.dependencies import get_current_user


def get_allowed_scopes_for_user(user: User) -> list[str]:
    """Calculate allowed document scopes based on user role.

    - admin, staff: PUBLIC, STUDENT_AFFAIRS, INTERNAL
    - student: PUBLIC, STUDENT_AFFAIRS
    """
    if user.role in (UserRole.ADMIN.value, UserRole.STAFF.value):
        return [
            DocumentScopeCode.PUBLIC.value,
            DocumentScopeCode.STUDENT_AFFAIRS.value,
            DocumentScopeCode.INTERNAL.value,
        ]
    return [DocumentScopeCode.PUBLIC.value, DocumentScopeCode.STUDENT_AFFAIRS.value]


def check_document_access(document: Document, user: User, request_id: str = "") -> None:
    """Validate user has permission to view the document.

    If document is soft-deleted -> 404 Not Found.
    If scope not allowed for user role -> 403 Forbidden.
    """
    if document.deleted_at is not None:
        raise not_found(detail="Tài liệu không tồn tại.", request_id=request_id)
    allowed = get_allowed_scopes_for_user(user)
    if document.scope not in allowed:
        raise forbidden(
            detail="Tài khoản của bạn không có quyền truy cập tài liệu này.",
            request_id=request_id,
        )


def require_staff_or_admin(user: User = Depends(get_current_user)) -> User:
    """Require user role to be 'staff' or 'admin'."""
    if user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        raise forbidden(detail="Chỉ cán bộ hoặc quản trị viên mới có quyền thực hiện thao tác này.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require user role to be 'admin'."""
    if user.role != UserRole.ADMIN.value:
        raise forbidden(detail="Chỉ quản trị viên mới có quyền thực hiện thao tác này.")
    return user


def get_idempotency_key(idempotency_key: str = Header(..., alias="Idempotency-Key")) -> str:
    """Extract and validate Idempotency-Key header."""
    if not idempotency_key or not idempotency_key.strip():
        raise validation_error(
            errors=[
                {
                    "field": "Idempotency-Key",
                    "message": "Header Idempotency-Key là bắt buộc.",
                }
            ],
            request_id="",
            detail="Header Idempotency-Key không được để trống.",
        )
    return idempotency_key.strip()
