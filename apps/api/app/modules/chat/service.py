"""Chat module service logic for RAG Chatbot with Citations."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import forbidden, not_found
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.user import User
from app.modules.chat.schemas import (
    ChatQueryResponse,
    CitationSchema,
)
from app.modules.documents.dependencies import get_allowed_scopes_for_user
from app.modules.search.schemas import SearchResultItem
from app.modules.search.service import search_documents
from app.services.llm import AbstractLLMProvider, get_llm_provider


def truncate_quote(text: str, max_length: int = 300) -> str:
    """Truncate text to max_length at word boundary, appending '...' if truncated."""
    cleaned = text.strip()
    if len(cleaned) <= max_length:
        return cleaned
    truncated = cleaned[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."


def evaluate_grounding_and_citations(
    search_items: list[SearchResultItem],
    score_threshold: float = 0.005,
) -> tuple[bool, list[CitationSchema]]:
    """Evaluate if retrieved search results provide sufficient grounding evidence
    and construct valid citation schemas matching citation-spec.md.
    """
    if not search_items:
        return False, []

    valid_items = [item for item in search_items if item.score >= score_threshold]
    if not valid_items:
        return False, []

    citations: list[CitationSchema] = []
    for item in valid_items:
        bbox_val = item.bbox if item.bbox and item.bbox != [0.0, 0.0, 0.0, 0.0] else None
        citation = CitationSchema(
            document_id=item.document_id,
            document_version_id=item.version_id,
            title=item.document_title,
            page_number=item.page_number,
            chunk_id=item.chunk_id,
            quote=truncate_quote(item.text, 300),
            score=round(item.score, 4),
            bbox=bbox_val,
        )
        citations.append(citation)

    return True, citations


def build_rag_prompt(
    question: str,
    citations: list[CitationSchema],
) -> tuple[str, str]:
    """Construct system prompt and user prompt with grounded retrieval context."""
    system_prompt = (
        "Bạn là Trợ lý AI Quản lý & Số hóa Tài liệu Công tác Sinh viên. "
        "Hãy trả lời câu hỏi của người dùng DỰA TRÊN các đoạn văn bản trích dẫn dưới đây. "
        "Trả lời chính xác, ngắn gọn, trích dẫn rõ điều khoản nếu có."
    )

    context_lines = []
    for idx, c in enumerate(citations, 1):
        context_lines.append(
            f"[{idx}] Tài liệu: {c.title} (Trang {c.page_number})\nNội dung: {c.quote}"
        )

    context_str = "\n\n".join(context_lines)

    user_prompt = (
        f"THÔNG TIN TRÍCH DẪN THAM KHẢO:\n{context_str}\n\n" f"CÂU HỎI NGUỜI DÙNG:\n{question}"
    )

    return system_prompt, user_prompt


async def create_session(
    session: AsyncSession,
    user_id: str,
    title: str | None = None,
) -> ChatSession:
    """Create a new chat session for a user."""
    chat_session = ChatSession(
        user_id=user_id,
        title=title.strip() if (title and title.strip()) else "Hội thoại mới",
    )
    session.add(chat_session)
    await session.commit()
    await session.refresh(chat_session)
    return chat_session


async def list_sessions(
    session: AsyncSession,
    user_id: str,
    page: int = 1,
    size: int = 20,
) -> tuple[list[ChatSession], int]:
    """List sessions for a specific user ordered by update time descending."""
    count_stmt = select(func.count()).select_from(ChatSession).where(ChatSession.user_id == user_id)
    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * size
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .offset(offset)
        .limit(size)
    )
    res = await session.execute(stmt)
    sessions = list(res.scalars().all())
    return sessions, total


async def get_session_by_id(
    session: AsyncSession,
    session_id: str,
    user_id: str,
) -> ChatSession:
    """Retrieve session by ID, validating user ownership."""
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id,
    )
    res = await session.execute(stmt)
    chat_session = res.scalar_one_or_none()
    if not chat_session:
        raise not_found(f"Không tìm thấy phiên hội thoại với ID '{session_id}'.")
    return chat_session


async def delete_session(
    session: AsyncSession,
    session_id: str,
    user_id: str,
) -> None:
    """Delete a session by ID for a user."""
    chat_session = await get_session_by_id(session, session_id, user_id)
    await session.delete(chat_session)
    await session.commit()


async def list_messages(
    session: AsyncSession,
    session_id: str,
    user_id: str,
) -> list[ChatMessage]:
    """List all messages in a session after verifying ownership."""
    await get_session_by_id(session, session_id, user_id)
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def process_send_message(
    session: AsyncSession,
    user: User,
    session_id: str,
    content: str,
    llm_provider: AbstractLLMProvider | None = None,
) -> ChatMessage:
    """Process synchronous chat message with RAG grounding and citation metadata."""
    chat_session = await get_session_by_id(session, session_id, user.id)

    # 1. Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=content,
        has_sufficient_evidence=True,
        tokens_used=len(content.split()),
    )
    session.add(user_msg)
    await session.flush()

    # 2. Perform RBAC-scoped vector & text retrieval
    allowed_scopes = get_allowed_scopes_for_user(user)
    search_res = await search_documents(
        session=session,
        query=content,
        allowed_scopes=allowed_scopes,
        top_k=5,
    )

    # 3. Evaluate grounding evidence and citations
    has_evidence, citations = evaluate_grounding_and_citations(search_res.items)

    # 4. Generate response via LLM
    if not has_evidence:
        answer = "Không tìm thấy thông tin phù hợp trong các tài liệu hiện có."
        citations = []
    else:
        llm = llm_provider or get_llm_provider()
        sys_prompt, user_prompt = build_rag_prompt(content, citations)
        answer = await llm.generate(prompt=user_prompt, system_prompt=sys_prompt)

    tokens_used = len(content.split()) + len(answer.split())

    # 5. Save assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer,
        citations=[c.model_dump() for c in citations] if citations else None,
        has_sufficient_evidence=has_evidence,
        tokens_used=tokens_used,
    )
    session.add(assistant_msg)

    # Update session updated_at
    chat_session.updated_at = func.now()
    await session.commit()
    await session.refresh(assistant_msg)

    return assistant_msg


async def process_send_message_stream(
    session: AsyncSession,
    user: User,
    session_id: str,
    content: str,
    llm_provider: AbstractLLMProvider | None = None,
) -> AsyncGenerator[str, None]:
    """Process chat message with Server-Sent Events (SSE) streaming output."""
    chat_session = await get_session_by_id(session, session_id, user.id)

    # 1. Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=content,
        has_sufficient_evidence=True,
        tokens_used=len(content.split()),
    )
    session.add(user_msg)
    await session.flush()

    # 2. RAG Retrieval
    allowed_scopes = get_allowed_scopes_for_user(user)
    search_res = await search_documents(
        session=session,
        query=content,
        allowed_scopes=allowed_scopes,
        top_k=5,
    )

    # 3. Grounding evaluation
    has_evidence, citations = evaluate_grounding_and_citations(search_res.items)

    # 4. Yield citation event first
    citation_payload = {
        "citations": [c.model_dump() for c in citations],
        "has_sufficient_evidence": has_evidence,
    }
    yield f"event: citation\ndata: {json.dumps(citation_payload, ensure_ascii=False)}\n\n"

    full_answer_tokens: list[str] = []

    if not has_evidence:
        fallback_msg = "Không tìm thấy thông tin phù hợp trong các tài liệu hiện có."
        full_answer_tokens.append(fallback_msg)
        token_payload = {"token": fallback_msg}
        yield f"event: token\ndata: {json.dumps(token_payload, ensure_ascii=False)}\n\n"
    else:
        llm = llm_provider or get_llm_provider()
        sys_prompt, user_prompt = build_rag_prompt(content, citations)
        async for token in llm.stream_generate(prompt=user_prompt, system_prompt=sys_prompt):
            full_answer_tokens.append(token)
            token_payload = {"token": token}
            yield f"event: token\ndata: {json.dumps(token_payload, ensure_ascii=False)}\n\n"

    full_answer = "".join(full_answer_tokens)
    tokens_used = len(content.split()) + len(full_answer.split())

    # 5. Save assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=full_answer,
        citations=[c.model_dump() for c in citations] if citations else None,
        has_sufficient_evidence=has_evidence,
        tokens_used=tokens_used,
    )
    session.add(assistant_msg)
    chat_session.updated_at = func.now()
    await session.commit()
    await session.refresh(assistant_msg)

    # 6. Yield done event
    done_payload = {
        "message_id": assistant_msg.id,
        "tokens_used": tokens_used,
    }
    yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"


async def process_stateless_query(
    session: AsyncSession,
    user: User,
    question: str,
    scope: str | None = None,
    doc_type: str | None = None,
    top_k: int = 5,
    llm_provider: AbstractLLMProvider | None = None,
) -> ChatQueryResponse:
    """Process stateless chat query without persisting session history."""
    allowed_scopes = get_allowed_scopes_for_user(user)
    if scope and scope not in allowed_scopes:
        raise forbidden(f"Tài khoản của bạn không có quyền truy cập phạm vi '{scope}'.")

    search_res = await search_documents(
        session=session,
        query=question,
        allowed_scopes=allowed_scopes,
        requested_scope=scope,
        doc_type=doc_type,
        top_k=top_k,
    )

    has_evidence, citations = evaluate_grounding_and_citations(search_res.items)

    if not has_evidence:
        answer = "Không tìm thấy thông tin phù hợp trong các tài liệu hiện có."
        citations = []
    else:
        llm = llm_provider or get_llm_provider()
        sys_prompt, user_prompt = build_rag_prompt(question, citations)
        answer = await llm.generate(prompt=user_prompt, system_prompt=sys_prompt)

    tokens_used = len(question.split()) + len(answer.split())

    return ChatQueryResponse(
        answer=answer,
        citations=citations,
        has_sufficient_evidence=has_evidence,
        tokens_used=tokens_used,
    )
