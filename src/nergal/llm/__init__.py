"""LLM service module for text generation."""

from nergal.exceptions import (
    LLMConnectionError,
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
)
from nergal.llm.base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMMessage,
    LLMModelNotFoundError,
    LLMRateLimitError,
    LLMResponse,
    MessageRole,
)
from nergal.llm.factory import create_llm_provider

__all__ = [
    "BaseLLMProvider",
    "LLMAuthenticationError",
    "LLMConnectionError",
    "LLMError",
    "LLMMessage",
    "LLMModelNotFoundError",
    "LLMRateLimitError",
    "LLMResponse",
    "LLMResponseError",
    "LLMTimeoutError",
    "MessageRole",
    "create_llm_provider",
]
