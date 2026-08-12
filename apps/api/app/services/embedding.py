"""EmbeddingService for Phase D RAG Vector Engine.

Strategy Pattern:
- EmbeddingStrategy (Abstract Base Class)
- MockEmbeddingStrategy (Deterministic SHA-256 Mock adapter for pytest/dev)
- BGEM3EmbeddingStrategy (Primary adapter targeting BGE-M3 1024-dim endpoint)
- EmbeddingService (Context wrapper)
"""

from __future__ import annotations

import abc
import hashlib
import math

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


class EmbeddingStrategy(abc.ABC):
    """Base interface for embedding strategy implementations."""

    @abc.abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate 1024-dim embeddings for a list of text strings."""
        pass

    @abc.abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Generate 1024-dim embedding for a search query string."""
        pass


class MockEmbeddingStrategy(EmbeddingStrategy):
    """Deterministic SHA-256 Mock embedding strategy.

    Generates 1024-dim L2-normalized floating point vector deterministically.
    """

    def _generate_vector(self, text: str) -> list[float]:
        vec: list[float] = []
        for i in range(32):
            h = hashlib.sha256(f"{text}:{i}".encode()).digest()
            for j in range(32):
                val = (h[j % len(h)] + j * 7 + i * 13) % 256
                flt = (val / 127.5) - 1.0
                vec.append(flt)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return [1.0 / math.sqrt(1024)] * 1024  # pragma: no cover

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._generate_vector(query)


class BGEM3EmbeddingStrategy(EmbeddingStrategy):
    """BGE-M3 1024-dim primary adapter.

    No silent mock fallback: any transport failure or an unexpected/invalid
    embedding response raises RuntimeError so callers see the real problem.
    """

    def __init__(self, api_url: str | None = None, model_name: str | None = None) -> None:
        settings = get_settings()
        self.api_url = api_url or settings.embedding_api_url
        self.model_name = model_name or settings.embedding_model_name
        self.keep_alive = settings.embedding_ollama_keep_alive

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.api_url,
                    json={
                        "model": self.model_name,
                        "input": texts,
                        "keep_alive": self.keep_alive,
                    },
                )
                if response.status_code != 200:
                    raise RuntimeError(
                        f"BGE-M3 embedding API returned status {response.status_code}."
                    )

                data = response.json()
                raw_emb = data.get("embeddings") or data.get("embedding")
                if not raw_emb and isinstance(data.get("data"), list):
                    raw_emb = [
                        item.get("embedding") for item in data["data"] if isinstance(item, dict)
                    ]

                if (
                    isinstance(raw_emb, list)
                    and raw_emb
                    and isinstance(raw_emb[0], int | float)
                    and len(raw_emb) == 1024
                ):
                    embeddings: list[list[float]] | None = [raw_emb] * len(texts)
                elif isinstance(raw_emb, list) and len(raw_emb) == len(texts):
                    embeddings = raw_emb
                else:
                    embeddings = None

                if not (
                    isinstance(embeddings, list)
                    and len(embeddings) == len(texts)
                    and all(
                        isinstance(embedding, list) and len(embedding) == 1024
                        for embedding in embeddings
                    )
                ):
                    raise RuntimeError(
                        "BGE-M3 embedding API returned invalid embeddings "
                        "(expected one 1024-dim vector per input)."
                    )
                return embeddings
        except Exception as exc:
            raise RuntimeError(
                f"BGE-M3 embedding API failed: {exc}. "
                "Ensure Ollama is running with bge-m3 model loaded."
            ) from exc

    async def embed_query(self, query: str) -> list[float]:
        results = await self.embed_texts([query])
        return results[0]


class EmbeddingService:
    """Service wrapper for generating text embeddings."""

    def __init__(
        self,
        provider: str | None = None,
        strategy: EmbeddingStrategy | None = None,
    ) -> None:
        if strategy:
            self._strategy = strategy
        else:
            p = provider or get_settings().embedding_provider
            if p == "bge-m3":
                self._strategy = BGEM3EmbeddingStrategy()
            else:
                self._strategy = MockEmbeddingStrategy()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self._strategy.embed_texts(texts)

    async def embed_query(self, query: str) -> list[float]:
        return await self._strategy.embed_query(query)
