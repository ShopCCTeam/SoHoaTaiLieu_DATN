"""Pydantic schemas for Chat module and RAG Chatbot with Citations."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CitationSchema(BaseModel):
    """Citation metadata matching docs/domain/citation-spec.md."""

    model_config = ConfigDict(from_attributes=True)

    document_id: str = Field(..., description="UUID của tài liệu gốc")
    document_version_id: str = Field(..., description="UUID của phiên bản tài liệu")
    title: str = Field(..., description="Tiêu đề hiện tại của tài liệu")
    page_number: int = Field(..., ge=1, description="Trang PDF 1-based")
    chunk_id: str = Field(..., description="UUID của chunk embedding")
    quote: str = Field(..., description="Đoạn trích dẫn nguyên văn (tối đa 300 ký tự)")
    score: float = Field(..., ge=0.0, le=1.0, description="Điểm tương đồng (0..1)")
    bbox: list[float] | None = Field(
        None, description="Tọa độ [x0, y0, x1, y1] nếu từ OCR block, null nếu text-extracted"
    )


class CreateSessionRequest(BaseModel):
    """Payload to create a new chat session."""

    title: str | None = Field(None, max_length=255, description="Tiêu đề hội thoại tùy chọn")


class ChatSessionResponse(BaseModel):
    """Chat session representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages_count: int | None = 0


class ChatMessageResponse(BaseModel):
    """Chat message representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    citations: list[CitationSchema] | None = None
    has_sufficient_evidence: bool = True
    tokens_used: int = 0
    created_at: datetime


class SendMessageRequest(BaseModel):
    """Payload to send a message to a session."""

    content: str = Field(..., min_length=1, description="Nội dung tin nhắn")


class ChatQueryRequest(BaseModel):
    """Stateless chat query payload."""

    question: str = Field(..., min_length=1, description="Câu hỏi người dùng")
    scope: str | None = Field(None, description="Lọc theo phạm vi tài liệu")
    doc_type: str | None = Field(None, description="Lọc theo loại tài liệu")
    top_k: int = Field(5, ge=1, le=20, description="Số lượng trích dẫn tối đa")


class ChatQueryResponse(BaseModel):
    """Stateless chat query response."""

    answer: str
    citations: list[CitationSchema]
    has_sufficient_evidence: bool
    tokens_used: int


class ChatSessionEnvelope(BaseModel):
    success: Literal[True] = True
    data: ChatSessionResponse


class ChatSessionListEnvelope(BaseModel):
    success: Literal[True] = True
    data: list[ChatSessionResponse]
    total: int
    page: int
    size: int


class ChatMessageEnvelope(BaseModel):
    success: Literal[True] = True
    data: ChatMessageResponse


class ChatMessageListEnvelope(BaseModel):
    success: Literal[True] = True
    data: list[ChatMessageResponse]


class ChatQueryEnvelope(BaseModel):
    success: Literal[True] = True
    data: ChatQueryResponse
