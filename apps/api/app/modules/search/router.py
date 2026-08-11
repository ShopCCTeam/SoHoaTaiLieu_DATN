"""FastAPI Router for Search API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DocumentScopeCode
from app.core.errors import forbidden
from app.db.session import get_session
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.documents.dependencies import get_allowed_scopes_for_user
from app.modules.search import service
from app.modules.search.schemas import (
    SearchEnvelope,
    SearchQueryRequest,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchEnvelope)
async def search_documents_get(
    request: Request,
    q: str = Query(..., min_length=1, max_length=1000, description="Từ khóa/câu hỏi tìm kiếm"),
    scope: DocumentScopeCode | None = Query(
        None, description="Lọc theo phạm vi (PUBLIC, STUDENT_AFFAIRS, INTERNAL)"
    ),
    type: str | None = Query(None, description="Lọc theo loại tài liệu"),
    alpha: float = Query(
        0.5, ge=0.0, le=1.0, description="Trọng số RRF (0.0: fulltext -> 1.0: vector)"
    ),
    top_k: int = Query(10, ge=1, le=100, description="Số lượng kết quả tối đa"),
    page: int = Query(1, ge=1, description="Trang kết quả (1-indexed)"),
    size: int = Query(10, ge=1, le=100, description="Kích thước trang"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SearchEnvelope:
    """GET Search documents with RRF hybrid search & RBAC scope filtering."""
    request_id = getattr(request.state, "request_id", "")
    allowed_scopes = get_allowed_scopes_for_user(current_user)

    if scope and scope.value not in allowed_scopes:
        raise forbidden(
            detail=f"Tài khoản của bạn không có quyền tìm kiếm phạm vi '{scope.value}'.",
            request_id=request_id,
        )

    res = await service.search_documents(
        session=session,
        query=q,
        allowed_scopes=allowed_scopes,
        requested_scope=scope.value if scope else None,
        doc_type=type,
        alpha=alpha,
        top_k=top_k,
        page=page,
        size=size,
    )
    return SearchEnvelope(data=res)


@router.post("", response_model=SearchEnvelope)
async def search_documents_post(
    request: Request,
    body: SearchQueryRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SearchEnvelope:
    """POST Search documents with RRF hybrid search & RBAC scope filtering."""
    request_id = getattr(request.state, "request_id", "")
    allowed_scopes = get_allowed_scopes_for_user(current_user)

    if body.scope and body.scope.value not in allowed_scopes:
        raise forbidden(
            detail=f"Tài khoản của bạn không có quyền tìm kiếm phạm vi '{body.scope.value}'.",
            request_id=request_id,
        )

    res = await service.search_documents(
        session=session,
        query=body.query,
        allowed_scopes=allowed_scopes,
        requested_scope=body.scope.value if body.scope else None,
        doc_type=body.doc_type,
        alpha=body.alpha,
        top_k=body.top_k,
        page=body.page,
        size=body.size,
    )
    return SearchEnvelope(data=res)
