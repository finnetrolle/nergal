"""Z.AI web search provider using direct MCP over HTTP with SSE."""

import json
import logging
import uuid
from typing import Any

import httpx

from nergal.monitoring import track_web_search
from nergal.web_search.base import (
    BaseSearchProvider,
    SearchError,
    SearchProviderError,
    SearchRequest,
    SearchResult,
    SearchResults,
)

logger = logging.getLogger(__name__)

ZAI_MCP_URL = "https://api.z.ai/api/mcp/web_search_prime/mcp"


class ZaiMcpHttpSearchProvider(BaseSearchProvider):
    """Z.AI web search provider using direct MCP over HTTP.

    Implements MCP protocol directly using HTTP POST with SSE response.
    """

    DEFAULT_MCP_URL = ZAI_MCP_URL

    def __init__(
        self,
        api_key: str,
        mcp_url: str | None = None,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> None:
        """Initialize Z.AI web search provider.

        Args:
            api_key: Z.AI API key.
            mcp_url: Optional custom MCP endpoint URL.
            timeout: Request timeout in seconds.
            **kwargs: Additional configuration options.
        """
        super().__init__(api_key, timeout, **kwargs)
        self.mcp_url = mcp_url or self.DEFAULT_MCP_URL
        self._session_id: str | None = None

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "Z.AI Web Search (MCP/HTTP)"

    def _parse_sse_response(self, text: str) -> dict[str, Any]:
        """Parse SSE response and extract JSON data.

        Args:
            text: SSE response text.

        Returns:
            Parsed JSON data from SSE data: lines.
        """
        result: dict[str, Any] = {}
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                json_str = line[5:].strip()
                if json_str:
                    try:
                        result = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        logger.debug(f"Failed to parse SSE data: {e}")
        return result

    def _generate_request_id(self) -> int:
        """Generate a unique request ID."""
        return abs(uuid.uuid4().int % (2**31))

    def _get_headers(self) -> dict[str, str]:
        """Get common headers for MCP requests."""
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        return headers

    async def _initialize_session(self, client: httpx.AsyncClient) -> dict[str, Any]:
        """Initialize MCP session.

        Args:
            client: HTTPX async client.

        Returns:
            Initialize result from server.

        Raises:
            SearchProviderError: If initialization fails.
        """
        request_id = self._generate_request_id()
        init_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "nergal-bot",
                    "version": "1.0.0",
                },
            },
        }

        response = await client.post(
            self.mcp_url,
            json=init_request,
            headers=self._get_headers(),
        )

        if response.status_code >= 400:
            raise SearchProviderError(
                f"MCP init failed: {response.status_code}",
                provider=self.provider_name,
            )

        self._session_id = response.headers.get("mcp-session-id")
        logger.debug(f"MCP session initialized: {self._session_id}")

        response_text = response.text.strip()
        if not response_text:
            return {}

        return self._parse_sse_response(response_text)

    async def _list_tools(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """List available MCP tools.

        Args:
            client: HTTPX async client.

        Returns:
            List of tool definitions.
        """
        request_id = self._generate_request_id()
        list_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/list",
            "params": {},
        }

        response = await client.post(
            self.mcp_url,
            json=list_request,
            headers=self._get_headers(),
        )

        if response.status_code >= 400:
            logger.warning(f"List tools failed: {response.status_code}")
            return []

        response_text = response.text.strip()
        if not response_text:
            return []

        data = self._parse_sse_response(response_text)
        return data.get("result", {}).get("tools", [])

    async def _call_tool(
        self,
        client: httpx.AsyncClient,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call an MCP tool.

        Args:
            client: HTTPX async client.
            tool_name: Name of the tool to call.
            arguments: Tool arguments.

        Returns:
            Tool result.

        Raises:
            SearchProviderError: If tool call fails.
        """
        request_id = self._generate_request_id()
        call_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        response = await client.post(
            self.mcp_url,
            json=call_request,
            headers=self._get_headers(),
        )

        if response.status_code >= 400:
            raise SearchProviderError(
                f"MCP tool call failed: {response.status_code}",
                provider=self.provider_name,
            )

        response_text = response.text.strip()
        if not response_text:
            return {}

        return self._parse_sse_response(response_text)

    def _find_search_tool(self, tool_names: list[str]) -> str | None:
        """Find the appropriate search tool from available tools.

        Args:
            tool_names: List of available tool names.

        Returns:
            Name of the search tool or None if not found.
        """
        candidates = ["webSearchPrime", "web_search", "search", "web_search_prime"]
        for candidate in candidates:
            if candidate in tool_names:
                return candidate

        if tool_names:
            logger.warning(f"Using first available tool: {tool_names[0]}")
            return tool_names[0]

        return None

    def _parse_content_response(self, content: list[dict[str, Any]]) -> list[SearchResult]:
        """Parse content items from tool response.

        Args:
            content: List of content items.

        Returns:
            List of SearchResult objects.
        """
        results: list[SearchResult] = []

        for item in content:
            if item.get("type") != "text":
                continue

            text = item.get("text", "")
            try:
                data = json.loads(text)

                # Handle double-encoded JSON
                if isinstance(data, str):
                    data = json.loads(data)

                results.extend(self._extract_results_from_data(data))

            except json.JSONDecodeError:
                logger.debug(f"Non-JSON response: {text[:100]}")

        return results

    def _extract_results_from_data(self, data: Any) -> list[SearchResult]:
        """Extract search results from parsed JSON data.

        Args:
            data: Parsed JSON data.

        Returns:
            List of SearchResult objects.
        """
        results: list[SearchResult] = []

        if isinstance(data, list):
            for item_data in data:
                if isinstance(item_data, dict):
                    results.append(self._parse_result_item(item_data))
        elif isinstance(data, dict):
            items = data.get(
                "results",
                data.get("search_result", data.get("items", data.get("data", []))),
            )
            if isinstance(items, list):
                for item_data in items:
                    if isinstance(item_data, dict):
                        results.append(self._parse_result_item(item_data))

        return results

    async def search(self, request: SearchRequest) -> SearchResults:
        """Perform a web search using Z.AI MCP.

        Args:
            request: Search request parameters.

        Returns:
            SearchResults containing the search results.

        Raises:
            SearchRateLimitError: If rate limit is exceeded.
            SearchProviderError: If the API returns an error.
            SearchError: For other search failures.
        """
        logger.info(f"Searching for: {request.query}")

        async with track_web_search():
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    await self._initialize_session(client)

                    tools = await self._list_tools(client)
                    tool_names = [t.get("name") for t in tools if t.get("name")]
                    logger.debug(f"Available tools: {tool_names}")

                    tool_name = self._find_search_tool(tool_names)
                    if not tool_name:
                        raise SearchError(
                            "No tools available on MCP server",
                            provider=self.provider_name,
                        )

                    result = await self._call_tool(
                        client,
                        tool_name,
                        {"search_query": request.query, "count": request.count},
                    )

                    if "error" in result:
                        raise SearchProviderError(
                            str(result["error"]),
                            provider=self.provider_name,
                        )

                    results: list[SearchResult] = []
                    if "result" in result:
                        content = result["result"].get("content", [])
                        results = self._parse_content_response(content)

                    logger.info(f"Search completed: {len(results)} results for '{request.query}'")

                    return SearchResults(
                        results=results,
                        query=request.query,
                        total=len(results),
                    )

            except httpx.TimeoutException:
                logger.error(f"Timeout for query '{request.query}'")
                raise SearchError("Request timeout", provider=self.provider_name)
            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                raise SearchError(f"Request failed: {e}", provider=self.provider_name)
            except (SearchRateLimitError, SearchProviderError):
                raise
            except Exception as e:
                logger.error(f"Search failed: {type(e).__name__}: {e}", exc_info=True)
                raise SearchError(f"Search failed: {e}", provider=self.provider_name) from e

    def _parse_result_item(self, item: dict[str, Any]) -> SearchResult:
        """Parse a single search result item.

        Args:
            item: Raw result dictionary.

        Returns:
            SearchResult object.
        """
        return SearchResult(
            title=item.get("title", ""),
            content=item.get("content", item.get("snippet", item.get("summary", ""))),
            link=item.get("link", item.get("url", "")),
            media=item.get("media", item.get("source", "")),
            icon=item.get("icon", item.get("favicon", "")),
            refer=item.get("refer", item.get("id", "")),
            publish_date=item.get("publish_date", item.get("date", "")),
        )

    async def quick_search(self, query: str, count: int = 5) -> SearchResults:
        """Perform a quick search with minimal parameters.

        Args:
            query: Search query string.
            count: Number of results to return.

        Returns:
            SearchResults containing the search results.
        """
        request = SearchRequest(query=query, count=count)
        return await self.search(request)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ZaiMcpHttpSearchProvider(mcp_url={self.mcp_url!r})"
