"""Tests for LLM Provider Adapter Pattern."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm.base import AbstractLLMProvider
from app.services.llm.factory import get_llm_provider
from app.services.llm.mock import MockLLMProvider
from app.services.llm.ollama import OllamaLLMProvider


@pytest.mark.asyncio
async def test_mock_llm_provider_generate():
    provider = MockLLMProvider()
    assert isinstance(provider, AbstractLLMProvider)

    resp_general = await provider.generate("Xin chào")
    assert "tư vấn tự động" in resp_general

    resp_rag = await provider.generate("CÂU HỎI: Học bổng?\nTHÔNG TIN TRÍCH DẪN: Quyết định 123")
    assert "Dựa trên các tài liệu" in resp_rag

    custom_provider = MockLLMProvider(default_response="Custom mock answer")
    resp_custom = await custom_provider.generate("Test prompt")
    assert resp_custom == "Custom mock answer"


@pytest.mark.asyncio
async def test_mock_llm_provider_stream_generate():
    provider = MockLLMProvider(default_response="Xin chào Việt Nam")
    tokens = []
    async for token in provider.stream_generate("Test prompt"):
        tokens.append(token)

    reconstructed = "".join(tokens)
    assert reconstructed == "Xin chào Việt Nam"


@pytest.mark.asyncio
async def test_ollama_llm_provider_generate():
    provider = OllamaLLMProvider(base_url="http://localhost:11434", model_name="qwen2.5:8b")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"message": {"content": "Ollama response text"}}
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await provider.generate("Test prompt", system_prompt="System instructions")

        assert res == "Ollama response text"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["model"] == "qwen2.5:8b"
        assert call_kwargs["json"]["keep_alive"] == "5m"
        assert len(call_kwargs["json"]["messages"]) == 2
        assert call_kwargs["json"]["messages"][0]["role"] == "system"


@pytest.mark.asyncio
async def test_ollama_llm_provider_stream_generate():
    provider = OllamaLLMProvider(base_url="http://localhost:11434", model_name="qwen2.5:8b")

    async def mock_aiter_lines():
        yield json.dumps({"message": {"content": "Token1 "}})
        yield json.dumps({"message": {"content": "Token2"}})
        yield ""

    mock_stream_context = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.aiter_lines = mock_aiter_lines
    mock_stream_context.__aenter__.return_value = mock_response

    with patch("httpx.AsyncClient.stream", return_value=mock_stream_context):
        tokens = []
        async for token in provider.stream_generate("Test prompt"):
            tokens.append(token)

        assert tokens == ["Token1 ", "Token2"]


def test_llm_factory(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from app.core.config import get_settings

    get_settings.cache_clear()

    default_llm = get_llm_provider()
    assert isinstance(default_llm, MockLLMProvider)

    ollama_llm = get_llm_provider("ollama")
    assert isinstance(ollama_llm, OllamaLLMProvider)
