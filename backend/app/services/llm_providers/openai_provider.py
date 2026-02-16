"""OpenAI LLM provider implementation."""

import logging
from typing import AsyncIterator, List, Optional

from .base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider (GPT-4, GPT-3.5, etc.)."""

    provider_name = "openai"
    display_name = "OpenAI"

    available_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ]

    default_model = "gpt-4o"

    def __init__(self, api_key: str, model: Optional[str] = None, api_base_url: Optional[str] = None):
        super().__init__(api_key, model, api_base_url)
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI
            kwargs = {"api_key": self.api_key}
            if self.api_base_url:
                kwargs["base_url"] = self.api_base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send a chat completion request to OpenAI."""
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
            logger.error(f"OpenAI API error: {e}")
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
        """Stream a chat completion response from OpenAI."""
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
            logger.error(f"OpenAI streaming error: {e}")
            raise

    async def validate_api_key(self) -> bool:
        """Validate the OpenAI API key by making a simple request."""
        try:
            client = self._get_client()
            # List models to validate the API key
            await client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI API key validation failed: {e}")
            return False
