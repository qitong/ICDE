"""Google Gemini LLM provider implementation."""

import logging
from typing import AsyncIterator, List, Optional

from .base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""

    provider_name = "gemini"
    display_name = "Gemini"

    available_models = [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
    ]

    default_model = "gemini-2.0-flash"

    def __init__(self, api_key: str, model: Optional[str] = None, api_base_url: Optional[str] = None):
        super().__init__(api_key, model, api_base_url)
        self._client = None

    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        return self._client

    def _format_messages_for_gemini(self, messages: List[LLMMessage]) -> tuple:
        """
        Format messages for Gemini API.
        Returns system instruction and conversation history.
        """
        system_instruction = None
        history = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "user":
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})

        return system_instruction, history

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send a chat completion request to Gemini."""
        try:
            import google.generativeai as genai

            system_instruction, history = self._format_messages_for_gemini(messages)

            # Configure generation settings
            generation_config = genai.GenerationConfig(
                temperature=temperature,
            )
            if max_tokens:
                generation_config.max_output_tokens = max_tokens

            # Create model with system instruction if provided
            model_kwargs = {"model_name": self.model}
            if system_instruction:
                model_kwargs["system_instruction"] = system_instruction

            model = genai.GenerativeModel(**model_kwargs)

            # Start chat with history (excluding the last user message)
            if history:
                chat_history = history[:-1] if len(history) > 1 else []
                last_message = history[-1]["parts"][0] if history else ""
            else:
                chat_history = []
                last_message = ""

            chat = model.start_chat(history=chat_history)

            # Send the last message
            response = await chat.send_message_async(
                last_message,
                generation_config=generation_config,
            )

            usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }

            return LLMResponse(
                content=response.text,
                model=self.model,
                provider=self.provider_name,
                usage=usage,
            )

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
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
        """Stream a chat completion response from Gemini."""
        try:
            import google.generativeai as genai

            system_instruction, history = self._format_messages_for_gemini(messages)

            # Configure generation settings
            generation_config = genai.GenerationConfig(
                temperature=temperature,
            )
            if max_tokens:
                generation_config.max_output_tokens = max_tokens

            # Create model with system instruction if provided
            model_kwargs = {"model_name": self.model}
            if system_instruction:
                model_kwargs["system_instruction"] = system_instruction

            model = genai.GenerativeModel(**model_kwargs)

            # Start chat with history
            if history:
                chat_history = history[:-1] if len(history) > 1 else []
                last_message = history[-1]["parts"][0] if history else ""
            else:
                chat_history = []
                last_message = ""

            chat = model.start_chat(history=chat_history)

            # Stream the response
            response = await chat.send_message_async(
                last_message,
                generation_config=generation_config,
                stream=True,
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise

    async def validate_api_key(self) -> bool:
        """Validate the Gemini API key by making a simple request."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            # Make a minimal request
            await model.generate_content_async("Hi", generation_config=genai.GenerationConfig(max_output_tokens=10))
            return True
        except Exception as e:
            logger.error(f"Gemini API key validation failed: {e}")
            return False
