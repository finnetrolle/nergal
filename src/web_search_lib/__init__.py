"""web_search_lib - A reusable Web Search library.

This library provides a clean, independent interface for searching
the internet using various search providers. It's designed to be reusable
across different applications without any external dependencies.

Example:
    >>> from web_search_lib import create_search_provider, SearchRequest
    >>>
    >>> # Create provider
    >>> search = create_search_provider(provider_type="zai", api_key="your-key")
    >>>
    >>> # Perform search
    >>> request = SearchRequest(query="python async await", count=5)
    >>> results = await search.search(request)
    >>> print(results.to_text())

Configuration:
    Configuration can be done via environment variables with WEB_SEARCH_ prefix:

    - WEB_SEARCH_PROVIDER: Provider type (zai, google, bing, serpapi)
    - WEB_SEARCH_API_KEY: API key for search provider
    - WEB_SEARCH_TIMEOUT: Timeout in seconds

    Or programmatically:

    >>> from web_search_lib import WebSearchConfig
    >>> config = WebSearchConfig(provider="zai", api_key="your-key")
    >>> search = create_search_provider(config)

Extensibility:
    Adding a new search provider:
    1. Create a new provider class inheriting from BaseSearchProvider
    2. Implement the search() method
    3. Add the provider to factory.py
"""

from web_search_lib.base import (
    BaseSearchProvider,
    SearchRecency,
    SearchRequest,
    SearchResult,
    SearchResults,
)
from web_search_lib.config import WebSearchConfig
from web_search_lib.exceptions import (
    SearchConnectionError,
    SearchError,
    SearchProviderError,
    SearchRateLimitError,
    SearchTimeoutError,
)
from web_search_lib.factory import create_search_provider
from web_search_lib.providers import ZaiMcpHttpSearchProvider
from web_search_lib.reliability import (
    CircuitBreaker,
    CircuitState,
    ClassifiedError,
    RetryConfig,
    RetryStats,
    SearchErrorCategory,
    classify_search_error,
    execute_with_retry,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "BaseSearchProvider",
    "create_search_provider",
    # Data models
    "SearchRecency",
    "SearchRequest",
    "SearchResult",
    "SearchResults",
    # Configuration
    "WebSearchConfig",
    # Exceptions
    "SearchError",
    "SearchConnectionError",
    "SearchTimeoutError",
    "SearchRateLimitError",
    "SearchProviderError",
    # Reliability components
    "CircuitBreaker",
    "CircuitState",
    "ClassifiedError",
    "RetryConfig",
    "RetryStats",
    "SearchErrorCategory",
    "classify_search_error",
    "execute_with_retry",
    # Providers
    "ZaiMcpHttpSearchProvider",
]
