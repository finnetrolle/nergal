"""Web search tool for Nergal.

This module provides the WebSearchTool which wraps the existing
web_search_lib to provide web search capabilities as a tool.

Example:
    >>> from nergal.tools.search.web import WebSearchTool
    >>> from web_search_lib import create_search_provider
    >>>
    >>> provider = create_search_provider(
    ...     provider_type="zai",
    ...     api_key="your-api-key"
    ... )
    >>>
    >>> tool = WebSearchTool(
    ...     search_provider=provider,
    ...     max_results=10,
    ...     allowed_domains=None
    ... )
    >>>
    >>> result = await tool.execute({
    ...     "query": "Python async await tutorial",
    ...     "count": 5
    ... })
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nergal.tools.base import Tool, ToolResult
from nergal.tools.exceptions import ToolExecutionError, ToolValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from web_search_lib.base import BaseSearchProvider, SearchRecency


class WebSearchTool(Tool):
    """Tool for performing web searches.

    This tool wraps the existing web_search_lib to provide
    web search capabilities with:
    - Configurable result count limit
    - Optional domain filtering
    - Time filter support (recency)
    - Rate limiting integration

    Attributes:
        search_provider: The web search provider instance.
        max_results: Maximum number of results per search (1-50).
        allowed_domains: Optional list of allowed domains for filtering.
                         None means no domain filtering.

    Examples:
        Basic usage:
        >>> from web_search_lib import create_search_provider
        >>> provider = create_search_provider(provider_type="zai", api_key="key")
        >>> tool = WebSearchTool(search_provider=provider)

        With domain filtering:
        >>> tool = WebSearchTool(
        ...     search_provider=provider,
        ...     allowed_domains=["github.com", "stackoverflow.com"]
        ... )

        With custom result limit:
        >>> tool = WebSearchTool(
        ...     search_provider=provider,
        ...     max_results=20
        ... )
    """

    def __init__(
        self,
        search_provider: BaseSearchProvider,
        max_results: int = 10,
        allowed_domains: Sequence[str] | None = None,
    ) -> None:
        """Initialize the web search tool.

        Args:
            search_provider: The web search provider instance.
            max_results: Maximum number of results per search (1-50). Default: 10.
            allowed_domains: Optional list of allowed domains for filtering.

        Raises:
            ValueError: If max_results is not between 1 and 50.
        """
        if not 1 <= max_results <= 50:
            raise ValueError(f"max_results must be between 1 and 50, got {max_results}")

        self._search_provider = search_provider
        self._max_results = max_results
        self._allowed_domains = list(allowed_domains) if allowed_domains else None

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "web_search"

    @property
    def description(self) -> str:
        """Return the tool description."""
        desc = (
            "Search the web for information. "
            "Returns titles, summaries, and links to relevant web pages."
        )

        if self._allowed_domains:
            desc += f" Results limited to: {', '.join(self._allowed_domains)}."

        return desc

    @property
    def parameters_schema(self) -> dict:
        """Return the JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to execute.",
                },
                "count": {
                    "type": "integer",
                    "description": (
                        "Number of results to return. "
                        f"Must be between 1 and {self._max_results}."
                    ),
                    "minimum": 1,
                    "maximum": self._max_results,
                    "default": 10,
                },
                "recency": {
                    "type": "string",
                    "description": "Time filter for search results.",
                    "enum": ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"],
                    "default": "noLimit",
                },
            },
            "required": ["query"],
        }

    async def execute(self, args: dict) -> ToolResult:
        """Execute a web search.

        Args:
            args: Dictionary containing:
                - query: The search query (required)
                - count: Number of results (optional, defaults to 10)
                - recency: Time filter (optional, defaults to "noLimit")

        Returns:
            ToolResult containing:
                - success: True if search succeeded
                - output: Formatted search results
                - error: Error message if search failed
                - metadata: Result count, query, and provider info

        Raises:
            ToolValidationError: If query is invalid.
            ToolExecutionError: If search fails.
        """
        from web_search_lib.base import SearchRecency, SearchRequest

        # Validate and extract query
        query = args.get("query")
        if not isinstance(query, str):
            raise ToolValidationError(
                tool_name=self.name,
                field="query",
                message="Query must be a non-empty string",
            )

        query = query.strip()
        if not query:
            raise ToolValidationError(
                tool_name=self.name,
                field="query",
                message="Query cannot be empty or whitespace",
            )

        # Validate and extract count
        count = args.get("count", 10)
        try:
            count = int(count) if isinstance(count, str) else count
            if not isinstance(count, int):
                raise TypeError("count must be an integer")
        except (ValueError, TypeError) as e:
            raise ToolValidationError(
                tool_name=self.name,
                field="count",
                message=f"Count must be a valid integer: {e}",
            ) from e

        count = min(max(1, count), self._max_results)

        # Validate and extract recency
        recency_str = args.get("recency", "noLimit")
        try:
            recency: SearchRecency = SearchRecency(recency_str)
        except ValueError as e:
            raise ToolValidationError(
                tool_name=self.name,
                field="recency",
                message=f"Invalid recency value: {recency_str}",
            ) from e

        # Apply domain filtering if configured
        domain_filter = None
        if self._allowed_domains:
            # For domain filtering, we'd need provider support.
            # Currently, this is a placeholder - actual implementation
            # would depend on provider capabilities.
            # Some providers like Zai MCP support domain_filter in SearchRequest.
            domain_filter = ",".join(self._allowed_domains) if self._allowed_domains else None

        # Create search request
        try:
            request = SearchRequest(
                query=query,
                count=count,
                recency=recency,
                domain_filter=domain_filter,
            )
        except ValueError as e:
            raise ToolValidationError(
                tool_name=self.name,
                message=f"Invalid search request: {e}",
            ) from e

        # Perform search
        try:
            results = await self._search_provider.search(request)
        except Exception as e:
            import web_search_lib.exceptions as search_exceptions

            # Map web_search_lib exceptions to ToolExecutionError
            if isinstance(e, (search_exceptions.SearchError,)):
                raise ToolExecutionError(
                    tool_name=self.name,
                    message=f"Search failed: {e}",
                ) from e
            else:
                raise ToolExecutionError(
                    tool_name=self.name,
                    message=f"Unexpected error during search: {e}",
                ) from e

        # Format results
        formatted_output = results.to_text(max_results=count)

        # Build metadata
        metadata = {
            "provider": self._search_provider.provider_name,
            "query": query,
            "requested_count": count,
            "actual_count": len(results.results),
            "recency": recency_str,
        }

        if results.total is not None:
            metadata["total_available"] = results.total

        if results.search_id:
            metadata["search_id"] = results.search_id

        return ToolResult(
            success=results.has_results(),
            output=formatted_output,
            metadata=metadata,
        )
