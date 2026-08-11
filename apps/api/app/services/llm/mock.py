"""Mock LLM Provider yielding realistic text/tokens for unit tests and CI."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from app.services.llm.base import AbstractLLMProvider


class MockLLMProvider(AbstractLLMProvider):
    """Mock LLM Provider for unit testing and CI without external model server."""

    def __init__(self, default_response: str | None = None) -> None:
        self.default_response = default_response

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Return realistic response based on prompt contents or default string."""
        if self.default_response is not None:
            return self.default_response

        # Check prompt for RAG evidence / search grounding cues
        if "THÔNG TIN TRÍCH DẪN" in prompt or "CONTEXT:" in prompt or "Tài liệu" in prompt:
            return (
                "Dựa trên các tài liệu công tác sinh viên được cung cấp, "
                "hệ thống xác nhận quy định đã nêu rõ các điều khoản và thủ tục thực hiện. "
                "Sinh viên cần tuân thủ đầy đủ các hướng dẫn của Nhà trường."
            )
        return (
            "Chào bạn, đây là hệ thống tư vấn tự động Công tác Sinh viên. "
            "Tôi có thể hỗ trợ giải đáp thắc mắc về quy chế và thủ tục sinh viên."
        )

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncGenerator[str, None]:
        """Stream response token by token."""
        full_text = await self.generate(
            prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens
        )
        words = full_text.split(" ")
        for i, word in enumerate(words):
            token = word if i == len(words) - 1 else word + " "
            yield token
            await asyncio.sleep(0.001)
