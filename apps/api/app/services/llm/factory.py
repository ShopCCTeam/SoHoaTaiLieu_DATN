"""Factory function for instantiating LLM provider."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.llm.base import AbstractLLMProvider
from app.services.llm.mock import MockLLMProvider
from app.services.llm.ollama import OllamaLLMProvider


def get_llm_provider(
    provider_override: str | None = None,
) -> AbstractLLMProvider:
    """Retrieve LLM provider based on settings configuration or explicit override."""
    settings = get_settings()
    provider = provider_override or settings.llm_provider

    if provider == "ollama":
        return OllamaLLMProvider(
            base_url=settings.llm_ollama_base_url,
            model_name=settings.llm_ollama_model_name,
            timeout_seconds=float(settings.llm_timeout_seconds),
            keep_alive=settings.llm_ollama_keep_alive,
        )
    return MockLLMProvider()
