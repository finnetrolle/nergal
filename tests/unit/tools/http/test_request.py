"""Unit tests for HttpRequestTool.

Tests follow TDD Red-Green-Refactor pattern.
"""

import tempfile
from pathlib import Path

import pytest

from nergal.tools.http.request import HttpRequestTool


class TestHttpRequestTool:
    """Tests for HttpRequestTool functionality."""

    @pytest.mark.asyncio
    async def test_get_request_success(self) -> None:
        """Test successful GET request."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple HTTP server that responds with data
            # For testing, we'll use httpbin or similar
            tool = HttpRequestTool()
            result = await tool.execute({
                "url": "https://httpbin.org/get",
                "method": "GET",
            })

            assert result.success is True
            assert "httpbin.org" in result.output.lower()

            assert result.success is True
            assert "httpbin.org" in result.output.lower()

    @pytest.mark.asyncio
    async def test_post_request_with_data(self) -> None:
        """Test POST request with data."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/post",
            "method": "POST",
            "data": '{"key": "value"}',
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_request_with_headers(self) -> None:
        """Test GET request with custom headers."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/get",
            "method": "GET",
            "headers": {
                "Authorization": "Bearer token123",
            },
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_request_timeout(self) -> None:
        """Test request timeout."""
        tool = HttpRequestTool(timeout=0.1)
        result = await tool.execute({
            "url": "https://httpbin.org/delay/5",
            "method": "GET",
        })

        assert result.success is False
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_request_missing_url(self) -> None:
        """Test request without URL."""
        tool = HttpRequestTool()
        result = await tool.execute({"method": "GET"})

        assert result.success is False
        assert "url" in result.error.lower()

    @pytest.mark.asyncio
    async def test_request_invalid_method(self) -> None:
        """Test request with invalid HTTP method."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/get",
            "method": "INVALID",
        })

        assert result.success is False
        assert "method" in result.error.lower()

    @pytest.mark.asyncio
    async def test_request_json_response(self) -> None:
        """Test request that returns JSON."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/json",
            "method": "GET",
        })

        assert result.success is True
        # Should return JSON as string
        assert "{" in result.output

    @pytest.mark.asyncio
    async def test_tool_properties(self) -> None:
        """Test tool properties."""
        tool = HttpRequestTool()

        assert tool.name == "http_request"
        assert tool.description is not None
        assert "http" in tool.description.lower()
        assert "request" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_post_with_form_data(self) -> None:
        """Test POST request with form data."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/post",
            "method": "POST",
            "form": {
                "username": "testuser",
                "password": "testpass",
            },
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_request_with_query_params(self) -> None:
        """Test request with query parameters."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/get?param1=value1&param2=value2",
            "method": "GET",
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_put_request(self) -> None:
        """Test PUT request."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/put",
            "method": "PUT",
            "data": '{"updated": true}',
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_delete_request(self) -> None:
        """Test DELETE request."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/delete",
            "method": "DELETE",
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_patch_request(self) -> None:
        """Test PATCH request."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/patch",
            "method": "PATCH",
            "data": '{"patched": true}',
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_request_empty_response(self) -> None:
        """Test request that returns empty response."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/status/204",
            "method": "GET",
        })

        assert result.success is True
        assert result.output == "" or result.output.strip() == ""

    @pytest.mark.asyncio
    async def test_request_with_json_data(self) -> None:
        """Test request with JSON data (different from form)."""
        tool = HttpRequestTool()
        result = await tool.execute({
            "url": "https://httpbin.org/post",
            "method": "POST",
            "json": '{"key": "value"}',
        })

        assert result.success is True
