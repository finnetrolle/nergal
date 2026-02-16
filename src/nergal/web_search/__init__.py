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
from nergal.web_search.zai_mcp_http import ZaiMcpHttpSearchProvider

__all__ = [
    "BaseSearchProvider",
    "SearchConnectionError",
    "SearchError",
    "SearchProviderError",
    "SearchRateLimitError",
    "SearchRecency",
    "SearchRequest",
    "SearchResult",
    "SearchResults",
    "SearchTimeoutError",
    "ZaiMcpHttpSearchProvider",
]
