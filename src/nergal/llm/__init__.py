"""LLM service module for text generation.

DEPRECATED: This module has been moved to llm_lib.
This module now re-exports from llm_lib for backward compatibility.
New code should import directly from llm_lib.

Example:
    # Old way (still works for backward compatibility)
    from nergal.llm import create_llm_provider

    # New way (recommended)
    from llm_lib import create_llm_provider
"""

from llm_lib import (
    BaseLLMProvider,
    LLMConfig,
    LLMAuthenticationError,
    LLMError,
    LLMMessage,
    LLMModelNotFoundError,
    LLMRateLimitError,
    LLMResponse,
    MessageRole,
    create_llm_provider,
    get_supported_providers,
    register_provider,
)

# Re-export from nergal.exceptions for backward compatibility
from nergal.exceptions import (
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
)

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
    # Exceptions from llm_lib
    "LLMError",
    "LLMAuthenticationError",
    "LLMModelNotFoundError",
    "LLMRateLimitError",
    # Exceptions from nergal.exceptions (for backward compatibility)
    "LLMConnectionError",
    "LLMResponseError",
    "LLMTimeoutError",
]
