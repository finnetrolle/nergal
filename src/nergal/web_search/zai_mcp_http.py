"""Z.AI web search provider using direct MCP over HTTP with SSE."""

import json
import logging
import time
import traceback
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
from nergal.web_search.reliability import (
    CircuitBreaker,
    ClassifiedError,
    RetryConfig,
    RetryStats,
    classify_search_error,
    execute_with_retry,
)

logger = logging.getLogger(__name__)

ZAI_MCP_URL = "https://api.z.ai/api/mcp/web_search_prime/mcp"


class TelemetryContext:
    """Context for collecting telemetry data during search."""

    def __init__(self) -> None:
        """Initialize telemetry context."""
        self.start_time: float = time.time()
        self.init_start_time: float | None = None
        self.init_duration_ms: int | None = None
        self.tools_list_start_time: float | None = None
        self.tools_list_duration_ms: int | None = None
        self.search_call_start_time: float | None = None
        self.search_call_duration_ms: int | None = None
        self.api_session_id: str | None = None
        self.tool_used: str | None = None
        self.http_status_code: int | None = None
        self.raw_response: dict[str, Any] | None = None
        self.error_type: str | None = None
        self.error_message: str | None = None
        self.error_stack_trace: str | None = None

        # Retry telemetry
        self.retry_count: int = 0
        self.retry_reasons: list[str] = []
        self.total_retry_delay_ms: int = 0

        # Error classification
        self.error_category: str | None = None
        self.should_retry: bool = False

    def start_init(self) -> None:
        """Mark the start of MCP initialization."""
        self.init_start_time = time.time()

    def end_init(self) -> None:
        """Mark the end of MCP initialization."""
        if self.init_start_time:
            self.init_duration_ms = int((time.time() - self.init_start_time) * 1000)

    def start_tools_list(self) -> None:
        """Mark the start of tools/list call."""
        self.tools_list_start_time = time.time()

    def end_tools_list(self) -> None:
        """Mark the end of tools/list call."""
        if self.tools_list_start_time:
            self.tools_list_duration_ms = int((time.time() - self.tools_list_start_time) * 1000)

    def start_search_call(self) -> None:
        """Mark the start of search call."""
        self.search_call_start_time = time.time()

    def end_search_call(self) -> None:
        """Mark the end of search call."""
        if self.search_call_start_time:
            self.search_call_duration_ms = int((time.time() - self.search_call_start_time) * 1000)

    def get_total_duration_ms(self) -> int:
        """Get total duration in milliseconds."""
        return int((time.time() - self.start_time) * 1000)

    def set_error(self, error: Exception, classified: ClassifiedError | None = None) -> None:
        """Set error information from an exception.

        Args:
            error: The exception that occurred.
            classified: Optional pre-classified error. If not provided, will classify.
        """
        self.error_type = type(error).__name__
        self.error_message = str(error)
        self.error_stack_trace = traceback.format_exc()

        # Classify error if not provided
        if classified is None:
            classified = classify_search_error(error)

        self.error_category = classified.category.value
        self.should_retry = classified.should_retry

    def update_from_retry_stats(self, stats: RetryStats) -> None:
        """Update telemetry from retry statistics.

        Args:
            stats: Retry statistics to merge into telemetry.
        """
        self.retry_count = stats.attempts - 1  # First attempt is not a retry
        self.retry_reasons = stats.retry_reasons
        self.total_retry_delay_ms = stats.total_delay_ms


class ZaiMcpHttpSearchProvider(BaseSearchProvider):
    """Z.AI web search provider using direct MCP over HTTP.

    Implements MCP protocol directly using HTTP POST with SSE response.
    Includes comprehensive telemetry tracking.
    """

    DEFAULT_MCP_URL = ZAI_MCP_URL

    def __init__(
        self,
        api_key: str,
        mcp_url: str | None = None,
        timeout: float = 30.0,
        telemetry_enabled: bool = True,
        retry_config: RetryConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Z.AI web search provider.

        Args:
            api_key: Z.AI API key.
            mcp_url: Optional custom MCP endpoint URL.
            timeout: Request timeout in seconds.
            telemetry_enabled: Whether to save telemetry to database.
            retry_config: Configuration for retry behavior. Uses defaults if not provided.
            circuit_breaker: Circuit breaker instance. Creates new one if not provided.
            **kwargs: Additional configuration options.
        """
        super().__init__(api_key, timeout, **kwargs)
        self.mcp_url = mcp_url or self.DEFAULT_MCP_URL
        self._session_id: str | None = None
        self._telemetry_enabled = telemetry_enabled
        self._telemetry_repo: Any = None  # Lazy-loaded WebSearchTelemetryRepository

        # Reliability components
        self._retry_config = retry_config or RetryConfig()
        self._circuit_breaker = circuit_breaker or CircuitBreaker()

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "Z.AI Web Search (MCP/HTTP)"

    def _get_telemetry_repo(self) -> Any:
        """Get the telemetry repository (lazy-loaded to avoid circular imports)."""
        if self._telemetry_repo is None:
            from nergal.database.repositories import WebSearchTelemetryRepository

            self._telemetry_repo = WebSearchTelemetryRepository()
        return self._telemetry_repo

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

    async def _initialize_session(
        self, client: httpx.AsyncClient, telemetry: TelemetryContext
    ) -> dict[str, Any]:
        """Initialize MCP session.

        Args:
            client: HTTPX async client.
            telemetry: Telemetry context for timing.

        Returns:
            Initialize result from server.

        Raises:
            SearchProviderError: If initialization fails.
        """
        telemetry.start_init()
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

        telemetry.http_status_code = response.status_code

        if response.status_code >= 400:
            telemetry.end_init()
            raise SearchProviderError(
                f"MCP init failed: {response.status_code}",
                provider=self.provider_name,
            )

        self._session_id = response.headers.get("mcp-session-id")
        telemetry.api_session_id = self._session_id
        logger.debug(f"MCP session initialized: {self._session_id}")

        response_text = response.text.strip()
        telemetry.end_init()

        if not response_text:
            return {}

        return self._parse_sse_response(response_text)

    async def _list_tools(
        self, client: httpx.AsyncClient, telemetry: TelemetryContext
    ) -> list[dict[str, Any]]:
        """List available MCP tools.

        Args:
            client: HTTPX async client.
            telemetry: Telemetry context for timing.

        Returns:
            List of tool definitions.
        """
        telemetry.start_tools_list()
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
            telemetry.end_tools_list()
            return []

        response_text = response.text.strip()
        telemetry.end_tools_list()

        if not response_text:
            return []

        data = self._parse_sse_response(response_text)
        return data.get("result", {}).get("tools", [])

    async def _call_tool(
        self,
        client: httpx.AsyncClient,
        tool_name: str,
        arguments: dict[str, Any],
        telemetry: TelemetryContext,
    ) -> dict[str, Any]:
        """Call an MCP tool.

        Args:
            client: HTTPX async client.
            tool_name: Name of the tool to call.
            arguments: Tool arguments.
            telemetry: Telemetry context for timing.

        Returns:
            Tool result.

        Raises:
            SearchProviderError: If tool call fails.
        """
        telemetry.start_search_call()
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

        telemetry.http_status_code = response.status_code

        if response.status_code >= 400:
            telemetry.end_search_call()
            raise SearchProviderError(
                f"MCP tool call failed: {response.status_code}",
                provider=self.provider_name,
            )

        response_text = response.text.strip()
        telemetry.end_search_call()

        if not response_text:
            return {}

        result = self._parse_sse_response(response_text)
        telemetry.raw_response = result
        return result

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

    async def _save_telemetry(
        self,
        request: SearchRequest,
        telemetry: TelemetryContext,
        status: str,
        results_count: int = 0,
        results: list[dict[str, Any]] | None = None,
        user_id: int | None = None,
        session_id: str | None = None,
    ) -> None:
        """Save telemetry data to database.

        Args:
            request: The search request.
            telemetry: Telemetry context with timing data.
            status: Search status (success, error, timeout, empty).
            results_count: Number of results returned.
            results: List of result dictionaries.
            user_id: Optional user ID.
            session_id: Optional session ID.
        """
        if not self._telemetry_enabled:
            return

        try:
            repo = self._get_telemetry_repo()
            await repo.record_search(
                query=request.query,
                status=status,
                user_id=user_id,
                session_id=session_id,
                result_count_requested=request.count,
                recency_filter=request.recency.value if request.recency else None,
                domain_filter=request.domain_filter,
                results_count=results_count,
                results=results,
                error_type=telemetry.error_type,
                error_message=telemetry.error_message,
                error_stack_trace=telemetry.error_stack_trace,
                http_status_code=telemetry.http_status_code,
                api_response_time_ms=telemetry.search_call_duration_ms,
                api_session_id=telemetry.api_session_id,
                raw_response=telemetry.raw_response,
                total_duration_ms=telemetry.get_total_duration_ms(),
                init_duration_ms=telemetry.init_duration_ms,
                tools_list_duration_ms=telemetry.tools_list_duration_ms,
                search_call_duration_ms=telemetry.search_call_duration_ms,
                provider_name=self.provider_name,
                tool_used=telemetry.tool_used,
                # New retry and classification fields
                retry_count=telemetry.retry_count,
                retry_reasons=telemetry.retry_reasons,
                error_category=telemetry.error_category,
            )
        except Exception as e:
            # Don't let telemetry failures affect search
            logger.warning(f"Failed to save search telemetry: {e}")

    async def _do_search(
        self,
        request: SearchRequest,
        telemetry: TelemetryContext,
    ) -> SearchResults:
        """Execute a single search attempt without retry logic.

        This is the core search implementation that communicates with the MCP server.

        Args:
            request: Search request parameters.
            telemetry: Telemetry context for tracking this attempt.

        Returns:
            SearchResults containing the search results.

        Raises:
            Various exceptions for different failure modes.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            await self._initialize_session(client, telemetry)

            tools = await self._list_tools(client, telemetry)
            tool_names = [t.get("name") for t in tools if t.get("name")]
            logger.debug(f"Available tools: {tool_names}")

            tool_name = self._find_search_tool(tool_names)
            if not tool_name:
                raise SearchError(
                    "No tools available on MCP server",
                    provider=self.provider_name,
                )

            telemetry.tool_used = tool_name

            result = await self._call_tool(
                client,
                tool_name,
                {"search_query": request.query, "count": request.count},
                telemetry,
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

            return SearchResults(
                results=results,
                query=request.query,
                total=len(results),
            )

    async def search(
        self,
        request: SearchRequest,
        user_id: int | None = None,
        session_id: str | None = None,
    ) -> SearchResults:
        """Perform a web search using Z.AI MCP with retry logic.

        This method wraps the core search implementation with:
        - Circuit breaker pattern to prevent cascading failures
        - Retry with exponential backoff for transient errors
        - Comprehensive telemetry tracking

        Args:
            request: Search request parameters.
            user_id: Optional user ID for telemetry.
            session_id: Optional session ID for telemetry.

        Returns:
            SearchResults containing the search results.

        Raises:
            SearchRateLimitError: If rate limit is exceeded.
            SearchProviderError: If the API returns an error.
            SearchError: For other search failures.
        """
        logger.info(f"Searching for: {request.query}")
        telemetry = TelemetryContext()
        retry_stats = RetryStats()

        async with track_web_search():
            try:
                # Execute search with retry logic
                async def _search_operation() -> SearchResults:
                    return await self._do_search(request, telemetry)

                results, retry_stats = await execute_with_retry(
                    operation=_search_operation,
                    config=self._retry_config,
                    circuit_breaker=self._circuit_breaker,
                    operation_name="web_search",
                )

                # Update telemetry with retry info
                telemetry.update_from_retry_stats(retry_stats)

                # Determine status
                status = "success" if results.has_results() else "empty"

                # Convert results to dict for telemetry
                results_dict = [r.to_dict() for r in results.results[:10]]

                logger.info(
                    f"Search completed: {len(results.results)} results for '{request.query}' "
                    f"(attempts: {retry_stats.attempts})"
                )

                # Save telemetry
                await self._save_telemetry(
                    request,
                    telemetry,
                    status,
                    results_count=len(results.results),
                    results=results_dict,
                    user_id=user_id,
                    session_id=session_id,
                )

                return results

            except SearchError:
                # Re-raise SearchError as-is (already classified)
                telemetry.set_error(ClassifiedError(
                    category=classify_search_error(Exception()).category,
                    original_error=Exception(),
                    should_retry=False,
                    alert_severity="warning",
                    suggested_action="Search error",
                ))
                telemetry.update_from_retry_stats(retry_stats)
                await self._save_telemetry(
                    request, telemetry, "error", user_id=user_id, session_id=session_id
                )
                raise

            except httpx.TimeoutException as e:
                logger.error(f"Timeout for query '{request.query}' after {retry_stats.attempts} attempts")
                classified = classify_search_error(e)
                telemetry.set_error(e, classified)
                telemetry.update_from_retry_stats(retry_stats)
                await self._save_telemetry(
                    request, telemetry, "timeout", user_id=user_id, session_id=session_id
                )
                raise SearchError("Request timeout", provider=self.provider_name) from e

            except httpx.RequestError as e:
                logger.error(f"Request error: {e} after {retry_stats.attempts} attempts")
                classified = classify_search_error(e)
                telemetry.set_error(e, classified)
                telemetry.update_from_retry_stats(retry_stats)
                await self._save_telemetry(
                    request, telemetry, "error", user_id=user_id, session_id=session_id
                )
                raise SearchError(f"Request failed: {e}", provider=self.provider_name) from e

            except Exception as e:
                logger.error(f"Search failed: {type(e).__name__}: {e}", exc_info=True)
                classified = classify_search_error(e)
                telemetry.set_error(e, classified)
                telemetry.update_from_retry_stats(retry_stats)
                await self._save_telemetry(
                    request, telemetry, "error", user_id=user_id, session_id=session_id
                )
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

    async def quick_search(
        self,
        query: str,
        count: int = 5,
        user_id: int | None = None,
        session_id: str | None = None,
    ) -> SearchResults:
        """Perform a quick search with minimal parameters.

        Args:
            query: Search query string.
            count: Number of results to return.
            user_id: Optional user ID for telemetry.
            session_id: Optional session ID for telemetry.

        Returns:
            SearchResults containing the search results.
        """
        request = SearchRequest(query=query, count=count)
        return await self.search(request, user_id=user_id, session_id=session_id)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ZaiMcpHttpSearchProvider(mcp_url={self.mcp_url!r})"
