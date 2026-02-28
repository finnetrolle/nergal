"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from typing import Any

from llm_lib.exceptions import LLMError


class MessageRole(str, Enum):
    """Role of a message in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """Represents a message in an LLM conversation.

    Attributes:
        role: The role of the message sender (system, user, or assistant).
        content: The content of the message.
    """

    role: MessageRole
    content: str

    def to_dict(self) -> dict[str, str]:
        """Convert message to dictionary format for API calls.

        Returns:
            Dictionary with 'role' and 'content' keys.
        """
        return {"role": self.role.value, "content": self.content}


@dataclass
class LLMResponse:
    """Represents a response from an LLM provider.

    Attributes:
        content: The generated text content.
        model: The model name that generated the response.
        usage: Optional dictionary with token usage information.
        finish_reason: Optional reason why the generation finished.
        raw_response: Optional raw response data from the API.
    """

    content: str
    model: str
    usage: dict[str, int] | None = None
    finish_reason: str | None = None
    raw_response: dict[str, Any] | None = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers (Z.ai, Anthropic, OpenAI, Minimax, etc.) should
    inherit from this class and implement the required methods.

    This class provides a common interface for interacting with different
    LLM backends, allowing easy switching between providers.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize LLM provider.

        Args:
            api_key: API key for authentication.
            model: Model identifier to use.
            base_url: Optional base URL for API (for custom endpoints).
            **kwargs: Additional provider-specific configuration.
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.config = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from LLM.

        Args:
            messages: List of messages in the conversation.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse containing the generated content.

        Raises:
            LLMError: If generation fails.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from LLM.

        Args:
            messages: List of messages in the conversation.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific parameters.

        Yields:
            Chunks of the generated response as they arrive.

        Raises:
            LLMError: If generation fails.
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider.

        Returns:
            Provider name string for logging and error messages.
        """
        pass

    def validate_config(self) -> None:
        """Validate provider configuration.

        Override this method to add provider-specific validation.

        Raises:
            ValueError: If configuration is invalid.
        """
        if not self.api_key:
            raise ValueError(f"{self.provider_name}: API key is required")
        if not self.model:
            raise ValueError(f"{self.provider_name}: Model name is required")
