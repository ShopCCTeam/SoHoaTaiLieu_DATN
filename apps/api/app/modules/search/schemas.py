"""Pydantic schemas for Search API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.enums import DocumentScopeCode


class SearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Nội dung tìm kiếm")
    scope: DocumentScopeCode | None = Field(None, description="Lọc theo phạm vi tài liệu")
    doc_type: str | None = Field(None, description="Lọc theo loại tài liệu")
    keyword: str | None = Field(None, description="Lọc metadata bổ sung")
    tags: list[str] | None = Field(None, description="Các tag exact-match bắt buộc")
    alpha: float = Field(
        0.5, ge=0.0, le=1.0, description="Trọng số RRF (0.0: fulltext -> 1.0: vector)"
    )
    top_k: int = Field(10, ge=1, le=100, description="Số lượng kết quả tối đa")
    page: int = Field(1, ge=1, description="Trang kết quả (1-indexed)")
    size: int = Field(10, ge=1, le=100, description="Kích thước trang")


class SearchResultItem(BaseModel):
    chunk_id: str = Field(..., description="ID của chunk")
    document_id: str = Field(..., description="ID của tài liệu")
    version_id: str = Field(..., description="ID phiên bản tài liệu")
    document_title: str = Field(..., description="Tên tài liệu")
    document_scope: str = Field(..., description="Phạm vi tài liệu")
    document_type: str = Field(..., description="Loại tài liệu")
    page_number: int = Field(..., description="Số trang chứa chunk")
    chunk_index: int = Field(..., description="Thứ tự chunk trong phiên bản")
    text: str = Field(..., description="Nội dung đoạn văn bản")
    bbox: list[float] = Field(..., description="Bounding box envelope [x0, y0, x1, y1]")
    score: float = Field(..., description="Điểm RRF hybrid")
    vector_score: float | None = Field(None, description="Điểm tương đồng vector")
    fulltext_score: float | None = Field(None, description="Điểm khớp full-text")


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    total: int
    page: int
    size: int
    query: str


class SearchEnvelope(BaseModel):
    success: Literal[True] = True
    data: SearchResponse
