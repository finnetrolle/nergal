"""Web search module for searching the internet.

This module provides web search capabilities using various providers
like Z.AI's search engine.
"""

from nergal.exceptions import (
    SearchConnectionError,
    SearchError,
    SearchRateLimitError,
    SearchTimeoutError,
)
from nergal.web_search.base import (
    BaseSearchProvider,
    SearchProviderError,
    SearchRecency,
    SearchRequest,
    SearchResult,
    SearchResults,
)
from nergal.web_search.reliability import (
    CircuitBreaker,
    CircuitState,
    ClassifiedError,
    RetryConfig,
    RetryStats,
    SearchErrorCategory,
    classify_search_error,
    execute_with_retry,
)
from nergal.web_search.zai_mcp_http import ZaiMcpHttpSearchProvider

__all__ = [
    # Base classes
    "BaseSearchProvider",
    "SearchProviderError",
    "SearchRecency",
    "SearchRequest",
    "SearchResult",
    "SearchResults",
    # Exceptions
    "SearchConnectionError",
    "SearchError",
    "SearchRateLimitError",
    "SearchTimeoutError",
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
