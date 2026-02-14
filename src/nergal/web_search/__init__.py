"""Web search module for searching the internet.

This module provides web search capabilities using various providers
like Z.AI's search engine.
"""

from nergal.web_search.base import (
    BaseSearchProvider,
    SearchError,
    SearchProviderError,
    SearchRateLimitError,
    SearchRecency,
    SearchRequest,
    SearchResult,
    SearchResults,
)
from nergal.web_search.zai_mcp_http import ZaiMcpHttpSearchProvider

__all__ = [
    "BaseSearchProvider",
    "SearchError",
    "SearchProviderError",
    "SearchRateLimitError",
    "SearchRecency",
    "SearchRequest",
    "SearchResult",
    "SearchResults",
    "ZaiMcpHttpSearchProvider",
]
