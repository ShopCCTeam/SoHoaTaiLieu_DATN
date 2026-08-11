"""Tests for ChatSession and ChatMessage ORM models."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.user import User


@pytest.mark.asyncio
async def test_chat_session_and_message_crud(
    db_session: AsyncSession,
    seeded_user: User,
):
    # 1. Create session
    session_obj = ChatSession(
        user_id=seeded_user.id,
        title="Phiên thảo luận quy chế",
    )
    db_session.add(session_obj)
    await db_session.flush()

    assert session_obj.id is not None
    assert session_obj.user_id == seeded_user.id
    assert session_obj.title == "Phiên thảo luận quy chế"

    # 2. Add messages
    user_msg = ChatMessage(
        session_id=session_obj.id,
        role="user",
        content="Học bổng KKHT được xét thế nào?",
        has_sufficient_evidence=True,
        tokens_used=10,
    )
    assistant_msg = ChatMessage(
        session_id=session_obj.id,
        role="assistant",
        content="Học bổng được xét theo điểm rèn luyện và điểm học tập...",
        citations=[
            {
                "document_id": "doc_01",
                "document_version_id": "ver_01",
                "title": "Quy chế Học bổng",
                "page_number": 3,
                "chunk_id": "chk_01",
                "quote": "Trích đoạn quy chế...",
                "score": 0.95,
                "bbox": [10.0, 20.0, 100.0, 50.0],
            }
        ],
        has_sufficient_evidence=True,
        tokens_used=25,
    )
    db_session.add_all([user_msg, assistant_msg])
    await db_session.commit()

    # 3. Query back session & messages
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_obj.id)
    )
    res = await db_session.execute(stmt)
    refreshed_session = res.scalar_one_or_none()
    assert refreshed_session is not None
    assert len(refreshed_session.messages) == 2
    assert refreshed_session.messages[0].role == "user"
    assert refreshed_session.messages[1].role == "assistant"
    assert refreshed_session.messages[1].citations is not None
    assert len(refreshed_session.messages[1].citations) == 1
    assert refreshed_session.messages[1].citations[0]["title"] == "Quy chế Học bổng"


@pytest.mark.asyncio
async def test_chat_session_cascade_delete(
    db_session: AsyncSession,
    seeded_user: User,
):
    session_obj = ChatSession(user_id=seeded_user.id, title="Test Cascade")
    db_session.add(session_obj)
    await db_session.flush()

    msg = ChatMessage(
        session_id=session_obj.id,
        role="user",
        content="Test message content",
    )
    db_session.add(msg)
    await db_session.commit()

    msg_id = msg.id

    # Delete session
    await db_session.delete(session_obj)
    await db_session.commit()

    # Verify message is also deleted
    deleted_msg = await db_session.get(ChatMessage, msg_id)
    assert deleted_msg is None
