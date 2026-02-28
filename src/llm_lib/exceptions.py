"""Exceptions for LLM providers."""


class LLMError(Exception):
    """Base exception for all LLM errors.

    All LLM-related exceptions inherit from this class.

    Attributes:
        provider: Name of the LLM provider (optional).
    """

    def __init__(self, message: str, provider: str | None = None) -> None:
        """Initialize LLM error.

        Args:
            message: Human-readable error description.
            provider: Name of the LLM provider.
        """
        self.provider = provider
        if provider:
            message = f"[{provider}] {message}"
        super().__init__(message)


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded (429)."""

    pass


class LLMAuthenticationError(LLMError):
    """Raised when authentication fails (401)."""

    pass


class LLMModelNotFoundError(LLMError):
    """Raised when the specified model is not found (404)."""

    pass
