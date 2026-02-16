"""Anthropic Claude LLM provider implementation."""

import logging
from typing import AsyncIterator, List, Optional

from .base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""

    provider_name = "claude"
    display_name = "Claude"

    available_models = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ]

    default_model = "claude-sonnet-4-20250514"

    def __init__(self, api_key: str, model: Optional[str] = None, api_base_url: Optional[str] = None):
        super().__init__(api_key, model, api_base_url)
        self._client = None

    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            from anthropic import AsyncAnthropic
            kwargs = {"api_key": self.api_key}
            if self.api_base_url:
                kwargs["base_url"] = self.api_base_url
            self._client = AsyncAnthropic(**kwargs)
        return self._client

    def _format_messages_for_claude(self, messages: List[LLMMessage]) -> tuple:
        """
        Format messages for Claude API.
        Claude uses a separate system parameter instead of a system message.
        """
        system_prompt = None
        formatted = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                formatted.append({"role": msg.role, "content": msg.content})

        return system_prompt, formatted

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send a chat completion request to Claude."""
        try:
            client = self._get_client()
            system_prompt, formatted_messages = self._format_messages_for_claude(messages)

            kwargs = {
                "model": self.model,
                "messages": formatted_messages,
                "max_tokens": max_tokens or 4096,
                "temperature": temperature,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = await client.messages.create(**kwargs)

            # Extract content from response
            content = ""
            if response.content:
                content = response.content[0].text if response.content[0].type == "text" else ""

            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }

            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.provider_name,
                usage=usage,
                finish_reason=response.stop_reason,
            )

        except Exception as e:
            logger.error(f"Claude API error: {e}")
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
        """Stream a chat completion response from Claude."""
        try:
            client = self._get_client()
            system_prompt, formatted_messages = self._format_messages_for_claude(messages)

            kwargs = {
                "model": self.model,
                "messages": formatted_messages,
                "max_tokens": max_tokens or 4096,
                "temperature": temperature,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Claude streaming error: {e}")
            raise

    async def validate_api_key(self) -> bool:
        """Validate the Claude API key by making a simple request."""
        try:
            client = self._get_client()
            # Make a minimal request to validate the key
            await client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except Exception as e:
            logger.error(f"Claude API key validation failed: {e}")
            return False
