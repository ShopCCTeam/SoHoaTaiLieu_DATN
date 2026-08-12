"""Unit tests for EmbeddingService & Strategies."""

from __future__ import annotations

import math

import pytest

from app.services.embedding import (
    BGEM3EmbeddingStrategy,
    EmbeddingService,
    MockEmbeddingStrategy,
)


@pytest.mark.asyncio
async def test_mock_embedding_dimensions_and_normalization() -> None:
    strategy = MockEmbeddingStrategy()
    vector = await strategy.embed_query("Test quy chế đào tạo 2026")

    assert len(vector) == 1024
    norm = math.sqrt(sum(x * x for x in vector))
    assert math.isclose(norm, 1.0, rel_tol=1e-5)


@pytest.mark.asyncio
async def test_mock_embedding_determinism() -> None:
    strategy = MockEmbeddingStrategy()
    text = "Thông báo học bổng học tập"

    vec1 = await strategy.embed_query(text)
    vec2 = await strategy.embed_query(text)
    vec_diff = await strategy.embed_query("Thông báo học bổng khác")

    assert vec1 == vec2
    assert vec1 != vec_diff


@pytest.mark.asyncio
async def test_mock_embedding_batch() -> None:
    strategy = MockEmbeddingStrategy()
    texts = ["Văn bản 1", "Văn bản 2", "Văn bản 3"]
    vectors = await strategy.embed_texts(texts)

    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 1024
        norm = math.sqrt(sum(x * x for x in v))
        assert math.isclose(norm, 1.0, rel_tol=1e-5)


@pytest.mark.asyncio
async def test_bge_m3_embedding_uses_ollama_embed_batch_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BGE-M3 phải dùng endpoint batch `/api/embed` của Ollama nội bộ."""
    endpoint = "http://ollama:11434/api/embed"
    requests: list[tuple[str, dict[str, object]]] = []

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, list[list[float]]]:
            return {"embeddings": [[0.25] * 1024, [0.5] * 1024]}

    class FakeAsyncClient:
        def __init__(self, **_: object) -> None:
            pass

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
            requests.append((url, json))
            return FakeResponse()

    monkeypatch.setattr("app.services.embedding.httpx.AsyncClient", FakeAsyncClient)
    strategy = BGEM3EmbeddingStrategy(api_url=endpoint, model_name="bge-m3")

    embeddings = await strategy.embed_texts(["Văn bản một", "Văn bản hai"])

    assert embeddings == [[0.25] * 1024, [0.5] * 1024]
    assert requests == [
        (
            endpoint,
            {"model": "bge-m3", "input": ["Văn bản một", "Văn bản hai"]},
        )
    ]


@pytest.mark.asyncio
async def test_bge_m3_embedding_raises_on_unreachable_api() -> None:
    """BGE-M3 no longer silently falls back to mock: unreachable API must raise."""
    strategy = BGEM3EmbeddingStrategy(api_url="http://127.0.0.1:59999/invalid-endpoint")
    with pytest.raises(RuntimeError, match="BGE-M3 embedding API failed"):
        await strategy.embed_texts(["Nội dung test fallback"])


@pytest.mark.asyncio
async def test_embedding_service_wrapper() -> None:
    service = EmbeddingService(provider="mock")
    q_vec = await service.embed_query("Search query")
    t_vecs = await service.embed_texts(["Doc 1", "Doc 2"])

    assert len(q_vec) == 1024
    assert len(t_vecs) == 2
