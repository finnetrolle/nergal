"""Exceptions for the web search library.

This module defines a hierarchy of exceptions for web search operations.
The exceptions are independent and can be used without any other dependencies.
"""


class SearchError(Exception):
    """Base exception for all web search errors.

    All custom exceptions in the web search library should inherit from this class.
    This allows catching all search-specific errors with a single except clause.

    Attributes:
        message: Human-readable error description.
        provider: Name of the search provider that raised the error.
        cause: Optional underlying exception that caused this error.
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error description.
            provider: Name of the search provider.
            cause: Optional underlying exception that caused this error.
        """
        self.message = message
        self.provider = provider
        self.cause = cause
        super().__init__(message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.provider:
            if self.cause:
                return f"[{self.provider}] {self.message} (caused by: {self.cause})"
            return f"[{self.provider}] {self.message}"
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class SearchConnectionError(SearchError):
    """Error connecting to search provider.

    Raised when network issues prevent reaching the search API.
    """

    pass


class SearchTimeoutError(SearchError):
    """Error when search request times out.

    Raised when the search provider does not respond within the timeout period.
    """

    pass


class SearchRateLimitError(SearchError):
    """Error when rate limit is exceeded.

    Raised when the search provider rate limits the API calls.
    """

    def __init__(
        self,
        message: str = "Search rate limit exceeded",
        provider: str | None = None,
        retry_after: int | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the rate limit error.

        Args:
            message: Human-readable error description.
            provider: Name of the search provider.
            retry_after: Suggested number of seconds to wait before retrying.
            cause: Optional underlying exception.
        """
        self.retry_after = retry_after
        if retry_after:
            message = f"{message} (retry after {retry_after}s)"
        super().__init__(message, provider, cause)


class SearchProviderError(SearchError):
    """Error returned by the search provider.

    Raised when the search provider returns an error response.
    """

    pass
