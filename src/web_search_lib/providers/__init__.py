"""Web search provider implementations.

This package contains concrete implementations of search providers.
Each provider implements the BaseSearchProvider interface from web_search_lib.base.

Available providers:
    - ZaiMcpHttpSearchProvider: Z.AI search via MCP/HTTP

Adding a new provider:
    1. Create a new file in this directory (e.g., google_search.py)
    2. Inherit from BaseSearchProvider
    3. Implement the search() method
    4. Import in factory.py and add to create_search_provider()
"""

from web_search_lib.providers.zai_mcp_http import ZaiMcpHttpSearchProvider

__all__ = [
    "ZaiMcpHttpSearchProvider",
]
