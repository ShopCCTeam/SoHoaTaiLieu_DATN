from __future__ import annotations

from app.modules.chat.service import evaluate_grounding_and_citations
from app.modules.search.schemas import SearchResultItem


def _search_item(*, score: float, vector_score: float | None) -> SearchResultItem:
    return SearchResultItem(
        chunk_id="chunk_grounding_01",
        document_id="doc_grounding_01",
        version_id="ver_grounding_01",
        document_title="Tài liệu kiểm chứng grounding",
        document_scope="PUBLIC",
        document_type="QUY_DINH",
        page_number=1,
        chunk_index=0,
        text="Nội dung có thể dùng để kiểm chứng trích dẫn.",
        bbox=[10.0, 20.0, 30.0, 40.0],
        score=score,
        vector_score=vector_score,
        fulltext_score=0.7,
    )


def test_should_reject_high_rrf_score_when_cosine_is_below_threshold() -> None:
    """RRF cannot override the semantic-evidence guardrail."""
    grounded, citations = evaluate_grounding_and_citations(
        [_search_item(score=0.02, vector_score=0.59)],
        vector_score_threshold=0.6,
    )

    assert grounded is False
    assert citations == []


def test_should_accept_cosine_score_at_threshold_and_preserve_rrf_for_ranking() -> None:
    """The guardrail uses cosine; citation score remains the hybrid ranking score."""
    grounded, citations = evaluate_grounding_and_citations(
        [_search_item(score=0.0137, vector_score=0.6)],
        vector_score_threshold=0.6,
    )

    assert grounded is True
    assert len(citations) == 1
    assert citations[0].score == 0.0137


def test_should_reject_result_without_vector_score() -> None:
    grounded, citations = evaluate_grounding_and_citations(
        [_search_item(score=0.05, vector_score=None)],
        vector_score_threshold=0.6,
    )

    assert grounded is False
    assert citations == []
