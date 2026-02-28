"""llm_lib - A reusable LLM library.

This library provides a clean, independent interface for text generation
using various LLM providers. It's designed to be reusable across
different applications without any external dependencies.

Example:
    >>> from llm_lib import create_llm_provider, LLMMessage, MessageRole
    >>>
    >>> # Create provider
    >>> llm = create_llm_provider(
    ...     provider_type="zai",
    ...     api_key="your-api-key",
    ...     model="glm-4-flash"
    ... )
    >>>
    >>> # Generate text
    >>> messages = [
    ...     LLMMessage(role=MessageRole.SYSTEM, content="You are helpful."),
    ...     LLMMessage(role=MessageRole.USER, content="Hello!"),
    ... ]
    >>> response = await llm.generate(messages)
    >>> print(response.content)

Configuration:
    Configuration can be done programmatically:

    >>> from llm_lib import LLMConfig, create_llm_provider
    >>> config = LLMConfig(provider="zai", api_key="your-key", model="glm-4-flash")
    >>> llm = create_llm_provider(**config.to_dict())

Extensibility:
    Adding a new LLM provider:
    1. Create a new provider class inheriting from BaseLLMProvider
    2. Implement the generate() and generate_stream() methods
    3. Add the provider to factory.py
"""

from llm_lib.base import BaseLLMProvider, LLMMessage, LLMResponse, MessageRole
from llm_lib.config import LLMConfig
from llm_lib.exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMModelNotFoundError,
    LLMRateLimitError,
)
from llm_lib.factory import create_llm_provider, get_supported_providers, register_provider
from llm_lib.providers import ZaiProvider

__version__ = "0.1.0"

__all__ = [
    # Core
    "BaseLLMProvider",
    "create_llm_provider",
    "get_supported_providers",
    "register_provider",
    # Data models
    "LLMMessage",
    "LLMResponse",
    "MessageRole",
    # Configuration
    "LLMConfig",
    # Exceptions
    "LLMError",
    "LLMAuthenticationError",
    "LLMModelNotFoundError",
    "LLMRateLimitError",
    # Providers
    "ZaiProvider",
]
