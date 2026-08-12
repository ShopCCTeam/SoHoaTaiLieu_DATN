"""LangChain orchestration for grounded, RBAC-scoped document answers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_ollama import ChatOllama
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import forbidden
from app.models.user import User
from app.modules.documents.dependencies import get_allowed_scopes_for_user
from app.modules.search.schemas import SearchResponse, SearchResultItem
from app.modules.search.service import search_documents
from app.services.llm import AbstractLLMProvider, get_llm_provider

if TYPE_CHECKING:
    from app.modules.chat.schemas import CitationSchema


NO_ANSWER_MESSAGE = "Không tìm thấy thông tin phù hợp trong các tài liệu hiện có."
SYSTEM_PROMPT = (
    "Bạn là Trợ lý AI Quản lý & Số hóa Tài liệu Công tác Sinh viên. "
    "Chỉ trả lời dựa trên thông tin trích dẫn được cung cấp. "
    "Nếu trích dẫn không đủ để trả lời, hãy nói không đủ thông tin; "
    "không suy đoán và không tạo trích dẫn mới. "
    "Trả lời chính xác, ngắn gọn bằng tiếng Việt."
)


SearchFunction: TypeAlias = Callable[..., Awaitable[SearchResponse]]


@dataclass
class SafeRagTraceCallback(BaseCallbackHandler):
    """In-memory trace that intentionally excludes prompts, chunks, answers and PII."""

    stages: list[str]
    evidence_count: int = 0
    has_sufficient_evidence: bool = False

    def record_retrieval(self, *, evidence_count: int, has_sufficient_evidence: bool) -> None:
        self.stages.append("retrieval_guardrail_complete")
        self.evidence_count = evidence_count
        self.has_sufficient_evidence = has_sufficient_evidence

    def record_generation(self) -> None:
        self.stages.append("generation_complete")


class RAGRetriever(Protocol):
    """Retrieval boundary that returns only already-authorized search evidence."""

    async def retrieve(self, query: str) -> list[SearchResultItem]:
        """Return RBAC-filtered evidence for one user query."""


@dataclass(frozen=True)
class RagChainResult:
    """Typed output from the grounded LangChain chain."""

    answer: str
    citations: list[CitationSchema]
    has_sufficient_evidence: bool
    trace: SafeRagTraceCallback


@dataclass
class SearchDocumentsRetriever:
    """Adapter that applies scope authorization before existing hybrid retrieval."""

    session: AsyncSession
    user: User
    requested_scope: str | None = None
    doc_type: str | None = None
    top_k: int = 5
    search_function: SearchFunction = search_documents

    async def retrieve(self, query: str) -> list[SearchResultItem]:
        allowed_scopes = get_allowed_scopes_for_user(self.user)
        if self.requested_scope and self.requested_scope not in allowed_scopes:
            raise forbidden(
                f"Tài khoản của bạn không có quyền truy cập phạm vi '{self.requested_scope}'."
            )

        search_response = await self.search_function(
            session=self.session,
            query=query,
            allowed_scopes=allowed_scopes,
            requested_scope=self.requested_scope,
            doc_type=self.doc_type,
            top_k=self.top_k,
        )
        return search_response.items


def truncate_quote(text: str, max_length: int = 300) -> str:
    """Limit a citation quote at a word boundary without exposing unrelated text."""
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
    vector_score_threshold: float | None = None,
) -> tuple[bool, list[CitationSchema]]:
    """Accept evidence only at the configured cosine threshold; RRF never overrides it."""
    if not search_items:
        return False, []

    threshold = (
        vector_score_threshold
        if vector_score_threshold is not None
        else get_settings().rag_vector_score_threshold
    )
    valid_items = [
        item
        for item in search_items
        if item.vector_score is not None and item.vector_score >= threshold
    ]
    if not valid_items:
        return False, []

    from app.modules.chat.schemas import CitationSchema

    citations: list[CitationSchema] = []
    for item in valid_items:
        bbox = item.bbox if item.bbox and item.bbox != [0.0, 0.0, 0.0, 0.0] else None
        citations.append(
            CitationSchema(
                document_id=item.document_id,
                document_version_id=item.version_id,
                title=item.document_title,
                page_number=item.page_number,
                chunk_id=item.chunk_id,
                quote=truncate_quote(item.text),
                score=round(item.score, 4),
                bbox=bbox,
            )
        )
    return True, citations


def _citation_context(citations: list[CitationSchema]) -> str:
    """Render citations into the chain prompt while preserving citation identifiers externally."""
    return "\n\n".join(
        f"[{index}] Tài liệu: {citation.title} (Trang {citation.page_number})\n"
        f"Nội dung: {citation.quote}"
        for index, citation in enumerate(citations, start=1)
    )


class ProviderLangChainAdapter:
    """Make the existing provider interface usable as an async LangChain runnable."""

    def __init__(self, provider: AbstractLLMProvider) -> None:
        self.provider = provider

    async def ainvoke(self, prompt_value: PromptValue) -> str:
        system_prompt: str | None = None
        user_prompt_parts: list[str] = []
        for message in prompt_value.to_messages():
            content = str(message.content)
            if message.type == "system":
                system_prompt = content
            else:
                user_prompt_parts.append(content)
        return await self.provider.generate(
            prompt="\n".join(user_prompt_parts),
            system_prompt=system_prompt,
        )


class LangChainOllamaAdapter:
    """Adapter for the internal Ollama service using langchain-ollama."""

    def __init__(self) -> None:
        settings = get_settings()
        self.chat_model = ChatOllama(
            base_url=settings.llm_ollama_base_url,
            model=settings.llm_ollama_model_name,
            temperature=settings.llm_temperature,
            num_predict=settings.llm_max_tokens,
        )

    async def ainvoke(self, prompt_value: PromptValue) -> str:
        response = await self.chat_model.ainvoke(prompt_value)
        content = response.content
        if isinstance(content, str):
            return content
        return str(content)


def _default_llm_adapter() -> ProviderLangChainAdapter | LangChainOllamaAdapter:
    """Select the internal LangChain Ollama adapter in live mode and mock adapter in tests."""
    if get_settings().llm_provider == "ollama":
        return LangChainOllamaAdapter()
    return ProviderLangChainAdapter(get_llm_provider())


class LangChainRagChain:
    """Retriever → grounding guardrail → prompt → LLM adapter → string parser."""

    def __init__(
        self,
        retriever: RAGRetriever,
        llm_provider: AbstractLLMProvider | None = None,
    ) -> None:
        self.retriever = retriever
        llm_adapter = (
            ProviderLangChainAdapter(llm_provider)
            if llm_provider
            else _default_llm_adapter()
        )
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "human",
                    "THÔNG TIN TRÍCH DẪN THAM KHẢO:\n{context}\n\n"
                    "CÂU HỎI NGƯỜI DÙNG:\n{question}",
                ),
            ]
        )
        # LangChain's RunnableLambda stubs cannot express an arbitrary async
        # prompt-value callback. Keep that dynamic boundary isolated here.
        llm_runnable: Any = RunnableLambda(llm_adapter.ainvoke)
        self.generation_chain: Any = self.prompt | llm_runnable | StrOutputParser()

    async def retrieve_grounded(
        self, question: str
    ) -> tuple[bool, list[CitationSchema]]:
        """Run the RBAC retriever and cosine guardrail without invoking an LLM."""
        search_items = await self.retriever.retrieve(question)
        return evaluate_grounding_and_citations(search_items)

    def build_provider_prompts(
        self, question: str, citations: list[CitationSchema]
    ) -> tuple[str, str]:
        """Render the LangChain prompt template for providers that stream tokens directly."""
        messages = self.prompt.format_messages(
            question=question,
            context=_citation_context(citations),
        )
        system_prompt = "\n".join(
            str(message.content) for message in messages if message.type == "system"
        )
        user_prompt = "\n".join(
            str(message.content) for message in messages if message.type != "system"
        )
        return system_prompt, user_prompt

    async def ainvoke(self, question: str) -> RagChainResult:
        """Execute the full retriever → prompt → LLM → parser chain."""
        trace = SafeRagTraceCallback(stages=[])
        has_evidence, citations = await self.retrieve_grounded(question)
        trace.record_retrieval(
            evidence_count=len(citations),
            has_sufficient_evidence=has_evidence,
        )
        if not has_evidence:
            return RagChainResult(
                answer=NO_ANSWER_MESSAGE,
                citations=[],
                has_sufficient_evidence=False,
                trace=trace,
            )

        answer = await self.generation_chain.ainvoke(
            {"question": question, "context": _citation_context(citations)},
            config={"callbacks": [trace]},
        )
        trace.record_generation()
        return RagChainResult(
            answer=answer,
            citations=citations,
            has_sufficient_evidence=True,
            trace=trace,
        )


__all__ = [
    "LangChainRagChain",
    "NO_ANSWER_MESSAGE",
    "RAGRetriever",
    "SafeRagTraceCallback",
    "RagChainResult",
    "SearchDocumentsRetriever",
    "evaluate_grounding_and_citations",
    "truncate_quote",
]
