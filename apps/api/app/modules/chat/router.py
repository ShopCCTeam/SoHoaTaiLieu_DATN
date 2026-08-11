"""FastAPI Router for RAG Chatbot endpoints."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.chat import service
from app.modules.chat.schemas import (
    ChatMessageEnvelope,
    ChatMessageListEnvelope,
    ChatMessageResponse,
    ChatQueryEnvelope,
    ChatQueryRequest,
    ChatSessionEnvelope,
    ChatSessionListEnvelope,
    ChatSessionResponse,
    CreateSessionRequest,
    SendMessageRequest,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionEnvelope, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    body: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatSessionEnvelope:
    """Create a new chat session for current user."""
    chat_session = await service.create_session(
        session=session,
        user_id=current_user.id,
        title=body.title,
    )
    return ChatSessionEnvelope(data=ChatSessionResponse.model_validate(chat_session))


@router.get("/sessions", response_model=ChatSessionListEnvelope)
async def list_chat_sessions(
    page: int = Query(1, ge=1, description="Trang kết quả (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Kích thước trang"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatSessionListEnvelope:
    """List chat sessions of the current user."""
    sessions, total = await service.list_sessions(
        session=session,
        user_id=current_user.id,
        page=page,
        size=size,
    )
    res_items = [ChatSessionResponse.model_validate(s) for s in sessions]
    return ChatSessionListEnvelope(
        data=res_items,
        total=total,
        page=page,
        size=size,
    )


@router.get("/sessions/{id}", response_model=ChatSessionEnvelope)
async def get_chat_session(
    id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatSessionEnvelope:
    """Get chat session detail by session ID."""
    chat_session = await service.get_session_by_id(
        session=session,
        session_id=id,
        user_id=current_user.id,
    )
    return ChatSessionEnvelope(data=ChatSessionResponse.model_validate(chat_session))


@router.delete("/sessions/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Delete a chat session by session ID."""
    await service.delete_session(
        session=session,
        session_id=id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sessions/{id}/messages", response_model=ChatMessageListEnvelope)
async def list_chat_messages(
    id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatMessageListEnvelope:
    """List messages for a chat session."""
    messages = await service.list_messages(
        session=session,
        session_id=id,
        user_id=current_user.id,
    )
    return ChatMessageListEnvelope(data=[ChatMessageResponse.model_validate(m) for m in messages])


@router.post("/sessions/{id}/messages", response_model=ChatMessageEnvelope)
async def send_chat_message(
    id: str,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatMessageEnvelope:
    """Send a message synchronously and get complete RAG response with citations."""
    assistant_msg = await service.process_send_message(
        session=session,
        user=current_user,
        session_id=id,
        content=body.content,
    )
    return ChatMessageEnvelope(data=ChatMessageResponse.model_validate(assistant_msg))


@router.post("/sessions/{id}/messages/stream")
async def send_chat_message_stream(
    id: str,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Send a message with SSE streaming response (citation, token, done, error)."""

    async def sse_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in service.process_send_message_stream(
                session=session,
                user=current_user,
                session_id=id,
                content=body.content,
            ):
                yield chunk
        except Exception as exc:
            err_payload = {"error": str(exc)}
            yield f"event: error\ndata: {json.dumps(err_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/query", response_model=ChatQueryEnvelope)
async def chat_query(
    body: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatQueryEnvelope:
    """Stateless chat query endpoint without session creation."""
    res = await service.process_stateless_query(
        session=session,
        user=current_user,
        question=body.question,
        scope=body.scope,
        doc_type=body.doc_type,
        top_k=body.top_k,
    )
    return ChatQueryEnvelope(data=res)
