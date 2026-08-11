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
async def test_bge_m3_embedding_fallback() -> None:
    strategy = BGEM3EmbeddingStrategy(api_url="http://127.0.0.1:59999/invalid-endpoint")
    vectors = await strategy.embed_texts(["Nội dung test fallback"])

    assert len(vectors) == 1
    assert len(vectors[0]) == 1024
    norm = math.sqrt(sum(x * x for x in vectors[0]))
    assert math.isclose(norm, 1.0, rel_tol=1e-5)


@pytest.mark.asyncio
async def test_embedding_service_wrapper() -> None:
    service = EmbeddingService(provider="mock")
    q_vec = await service.embed_query("Search query")
    t_vecs = await service.embed_texts(["Doc 1", "Doc 2"])

    assert len(q_vec) == 1024
    assert len(t_vecs) == 2
