"""Moonshot Kimi LLM provider implementation.

Kimi uses an OpenAI-compatible API, so we can reuse the OpenAI client
with a custom base URL.
"""

import logging
from typing import AsyncIterator, List, Optional

from .base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

# Kimi API base URL
KIMI_API_BASE = "https://api.moonshot.cn/v1"


class KimiProvider(BaseLLMProvider):
    """Moonshot Kimi API provider (OpenAI-compatible)."""

    provider_name = "kimi"
    display_name = "Kimi"

    available_models = [
        "moonshot-v1-128k",
        "moonshot-v1-32k",
        "moonshot-v1-8k",
    ]

    default_model = "moonshot-v1-32k"

    def __init__(self, api_key: str, model: Optional[str] = None, api_base_url: Optional[str] = None):
        super().__init__(api_key, model, api_base_url or KIMI_API_BASE)
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI-compatible client for Kimi."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.api_base_url,
            )
        return self._client

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send a chat completion request to Kimi."""
        try:
            client = self._get_client()
            formatted_messages = self._format_messages(messages)

            kwargs = {
                "model": self.model,
                "messages": formatted_messages,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            response = await client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider=self.provider_name,
                usage=usage,
                finish_reason=choice.finish_reason,
            )

        except Exception as e:
            logger.error(f"Kimi API error: {e}")
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error=str(e),
            )

    async def stream_chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response from Kimi."""
        try:
            client = self._get_client()
            formatted_messages = self._format_messages(messages)

            kwargs = {
                "model": self.model,
                "messages": formatted_messages,
                "temperature": temperature,
                "stream": True,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            stream = await client.chat.completions.create(**kwargs)

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Kimi streaming error: {e}")
            raise

    async def validate_api_key(self) -> bool:
        """Validate the Kimi API key by making a simple request."""
        try:
            client = self._get_client()
            # List models to validate the API key
            await client.models.list()
            return True
        except Exception as e:
            logger.error(f"Kimi API key validation failed: {e}")
            return False
