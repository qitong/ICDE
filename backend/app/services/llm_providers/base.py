"""Base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Dict, Any, Optional


@dataclass
class LLMMessage:
    """A single message in the conversation."""
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)  # token counts
    finish_reason: Optional[str] = None
    error: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    # Provider identifier
    provider_name: str = "base"
    display_name: str = "Base Provider"

    # Available models for this provider
    available_models: List[str] = []

    # Default model
    default_model: str = ""

    def __init__(self, api_key: str, model: Optional[str] = None, api_base_url: Optional[str] = None):
        """Initialize the provider with API key and optional model override."""
        self.api_key = api_key
        self.model = model or self.default_model
        self.api_base_url = api_base_url

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send a chat completion request to the LLM.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with the assistant's reply
        """
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion response from the LLM.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Yields:
            String chunks of the response as they arrive
        """
        pass

    @abstractmethod
    async def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.

        Returns:
            True if the API key is valid, False otherwise
        """
        pass

    def _format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """Convert LLMMessage objects to provider-specific format."""
        return [{"role": m.role, "content": m.content} for m in messages]
