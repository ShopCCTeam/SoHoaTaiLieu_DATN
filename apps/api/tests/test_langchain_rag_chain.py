"""Tests for the LangChain RAG orchestration boundary."""

from __future__ import annotations

import pytest

from app.modules.search.schemas import SearchResultItem
from app.services.llm.base import AbstractLLMProvider
from app.services.rag_chain import LangChainRagChain, RAGRetriever


class StaticRetriever(RAGRetriever):
    """In-memory retriever double used to verify chain orchestration."""

    def __init__(self, items: list[SearchResultItem]) -> None:
        self.items = items
        self.queries: list[str] = []

    async def retrieve(self, query: str) -> list[SearchResultItem]:
        self.queries.append(query)
        return self.items


class RecordingProvider(AbstractLLMProvider):
    """Provider double that records only prompt invocation count for tests."""

    def __init__(self) -> None:
        self.calls = 0

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        self.calls += 1
        assert "CÂU HỎI NGƯỜI DÙNG" in prompt
        assert "Tài liệu kiểm chứng" in prompt
        return "Câu trả lời chỉ dựa trên trích dẫn."

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        yield await self.generate(prompt, system_prompt, temperature, max_tokens)


def _item(vector_score: float | None = 0.61) -> SearchResultItem:
    return SearchResultItem(
        chunk_id="chunk_langchain_01",
        document_id="doc_langchain_01",
        version_id="ver_langchain_01",
        document_title="Tài liệu kiểm chứng",
        document_scope="PUBLIC",
        document_type="QUY_DINH",
        page_number=2,
        chunk_index=0,
        text="Nội dung bằng chứng đã được truy xuất hợp lệ.",
        bbox=[10.0, 20.0, 30.0, 40.0],
        score=0.014,
        vector_score=vector_score,
        fulltext_score=0.8,
    )


@pytest.mark.asyncio
async def test_langchain_chain_returns_grounded_answer_with_citation() -> None:
    retriever = StaticRetriever([_item()])
    provider = RecordingProvider()
    chain = LangChainRagChain(retriever=retriever, llm_provider=provider)

    result = await chain.ainvoke("Điều kiện áp dụng là gì?")

    assert retriever.queries == ["Điều kiện áp dụng là gì?"]
    assert provider.calls == 1
    assert result.has_sufficient_evidence is True
    assert result.answer == "Câu trả lời chỉ dựa trên trích dẫn."
    assert result.citations[0].chunk_id == "chunk_langchain_01"
    assert result.trace.stages == ["retrieval_guardrail_complete", "generation_complete"]
    assert result.trace.evidence_count == 1
    trace_dump = repr(result.trace)
    assert "Điều kiện áp dụng" not in trace_dump
    assert "Nội dung bằng chứng" not in trace_dump
    assert "Câu trả lời chỉ dựa" not in trace_dump


@pytest.mark.asyncio
async def test_langchain_chain_returns_no_answer_without_invoking_llm() -> None:
    retriever = StaticRetriever([_item(vector_score=0.59)])
    provider = RecordingProvider()
    chain = LangChainRagChain(retriever=retriever, llm_provider=provider)

    result = await chain.ainvoke("Thông tin không đủ bằng chứng?")

    assert provider.calls == 0
    assert result.has_sufficient_evidence is False
    assert result.citations == []
    assert "Không tìm thấy thông tin phù hợp" in result.answer
    assert result.trace.stages == ["retrieval_guardrail_complete"]
    assert result.trace.evidence_count == 0
