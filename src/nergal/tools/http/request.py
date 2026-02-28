"""HttpRequestTool implementation.

This module provides HttpRequestTool which allows to agent
to make HTTP requests with configurable security.
"""

from __future__ import annotations

import logging

import httpx

from nergal.tools.base import Tool, ToolResult

logger = logging.getLogger(__name__)


class HttpRequestTool(Tool):
    """Tool for making HTTP requests.

    Supports GET, POST, PUT, PATCH, DELETE methods with configurable
    timeouts, headers, and security controls.

    Attributes:
        allowed_domains: Whitelist of allowed domains.
        max_redirects: Maximum number of redirects.
        timeout: Request timeout in seconds.

    Example:
        >>> tool = HttpRequestTool(allowed_domains=["api.example.com"])
        >>> result = await tool.execute({
        ...     "url": "https://api.example.com/data",
        ...     "method": "GET",
        ... })
    """

    def __init__(
        self,
        allowed_domains: list[str] | None = None,
        max_redirects: int = 10,
        timeout: float = 30.0,
    ) -> None:
        """Initialize HttpRequestTool.

        Args:
            allowed_domains: Optional whitelist of allowed domains.
                          If None, all domains are allowed.
            max_redirects: Maximum number of redirects (default 10).
            timeout: Request timeout in seconds (default 30.0).
        """
        self.allowed_domains = allowed_domains
        self.max_redirects = max_redirects
        self.timeout = timeout

    @property
    def name(self) -> str:
        """Return tool name."""
        return "http_request"

    @property
    def description(self) -> str:
        """Return tool description."""
        return "Make HTTP requests to any URL"

    @property
    def parameters_schema(self) -> dict:
        """Return JSON Schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to send the request to",
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method: GET, POST, PUT, PATCH, DELETE",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers as key-value pairs",
                },
                "data": {
                    "type": "string",
                    "description": "Optional request body (for POST, PUT, PATCH)",
                },
                "json": {
                    "type": "string",
                    "description": "Optional JSON request body (for POST, PUT, PATCH)",
                },
                "form": {
                    "type": "object",
                    "description": "Optional form data for x-www-form-urlencoded",
                },
                "params": {
                    "type": "object",
                    "description": "Optional query parameters for URL",
                },
                "timeout": {
                    "type": "number",
                    "description": f"Request timeout in seconds (max {self.timeout})",
                },
                "max_redirects": {
                    "type": "number",
                    "description": f"Maximum number of redirects (max {self.max_redirects})",
                },
            },
            "required": ["url", "method"],
        }

    async def execute(self, args: dict) -> ToolResult:
        """Execute HTTP request.

        Args:
            args: Dictionary with 'url', 'method' and optional:
                  'headers', 'data', 'json', 'form', 'params', 'timeout'.

        Returns:
            ToolResult with HTTP response content or error message.
        """
        url = args.get("url")
        method = args.get("method", "GET").upper()
        headers = args.get("headers")
        data = args.get("data")
        json_data = args.get("json")
        form = args.get("form")
        params = args.get("params")
        timeout = args.get("timeout", self.timeout)
        max_redirects = args.get("max_redirects", self.max_redirects)

        if not url:
            return ToolResult(
                success=False,
                output="",
                error="Missing required parameter: url",
            )

        # Validate method
        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        if method not in valid_methods:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid HTTP method: {method}",
            )

        # Security check: domain filtering
        if self.allowed_domains:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            hostname = parsed.hostname
            if hostname and hostname not in self.allowed_domains:
                logger.warning(f"Domain not in whitelist: {hostname}")
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Domain not allowed: {hostname}",
                )

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                max_redirects=max_redirects,
                follow_redirects=False,
            ) as http_client:
                request = self._build_request(
                    method,
                    url,
                    headers=headers,
                    data=data,
                    json=json_data,
                    form=form,
                    params=params,
                )

                response = await http_client.send(request)

                logger.info(f"HTTP {method} {url} - Status: {response.status_code}")

                # Return response content
                return ToolResult(
                    success=response.is_success,
                    output=response.text,
                )

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {url}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Request timeout after {timeout}s",
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {url}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"HTTP {e.response.status_code}: {str(e)}",
            )

        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Unexpected error: {str(e)}",
            )

    def _build_request(
        self,
        method: str,
        url: str,
        headers: dict | None,
        data: str | None = None,
        json: str | None = None,
        form: dict | None = None,
        params: dict | None = None,
    ) -> httpx.Request:
        """Build httpx request based on method and parameters."""
        kwargs = {}
        if headers:
            kwargs["headers"] = headers

        if method in ("POST", "PUT", "PATCH"):
            if json:
                kwargs["json"] = json
            elif form:
                kwargs["data"] = form
            elif data:
                kwargs["content"] = data

        if params and method in ("GET", "DELETE"):
            kwargs["params"] = params

        return httpx.Request(method, url, **kwargs)
