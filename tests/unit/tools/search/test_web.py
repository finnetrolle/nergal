"""Unit tests for WebSearchTool."""

import pytest

from nergal.tools.exceptions import ToolValidationError
from nergal.tools.search.web import WebSearchTool


class MockSearchProvider:
    """Mock search provider for testing."""

    def __init__(self, results=None):
        self.provider_name = "MockSearch"
        from web_search_lib.base import SearchResults

        # Support both list and SearchResults input
        if isinstance(results, SearchResults):
            self._results = results
        else:
            self._results = results or []

    async def search(self, request):
        """Mock search method."""
        from web_search_lib.base import SearchResults

        # If _results is already SearchResults, return it
        if hasattr(self._results, "results"):
            return self._results

        # Otherwise create SearchResults from list
        return SearchResults(
            results=self._results,
            query=request.query,
            total=len(self._results),
        )


class TestWebSearchTool:
    """Tests for WebSearchTool."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider)

        assert tool._search_provider is provider
        assert tool._max_results == 10
        assert tool._allowed_domains is None

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        provider = MockSearchProvider()
        tool = WebSearchTool(
            search_provider=provider,
            max_results=20,
            allowed_domains=["example.com", "test.com"],
        )

        assert tool._max_results == 20
        assert tool._allowed_domains == ["example.com", "test.com"]

    def test_init_invalid_max_results_too_low(self):
        """Test that max_results < 1 raises ValueError."""
        provider = MockSearchProvider()

        with pytest.raises(ValueError, match="max_results must be between 1 and 50"):
            WebSearchTool(search_provider=provider, max_results=0)

    def test_init_invalid_max_results_too_high(self):
        """Test that max_results > 50 raises ValueError."""
        provider = MockSearchProvider()

        with pytest.raises(ValueError, match="max_results must be between 1 and 50"):
            WebSearchTool(search_provider=provider, max_results=100)

    def test_name_property(self):
        """Test name property."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider)
        assert tool.name == "web_search"

    def test_description_without_domain_filter(self):
        """Test description without domain filtering."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider)

        desc = tool.description
        assert "Search the web" in desc
        assert "domains" not in desc.lower()

    def test_description_with_domain_filter(self):
        """Test description with domain filtering."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider, allowed_domains=["example.com"])

        desc = tool.description
        assert "example.com" in desc

    def test_parameters_schema(self):
        """Test parameters_schema property."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider)

        schema = tool.parameters_schema

        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "count" in schema["properties"]
        assert "recency" in schema["properties"]

        # Required fields
        assert "query" in schema["required"]
        assert "count" not in schema["required"]

        # Query property
        assert schema["properties"]["query"]["type"] == "string"

        # Count property
        assert schema["properties"]["count"]["type"] == "integer"
        assert schema["properties"]["count"]["default"] == 10
        assert schema["properties"]["count"]["minimum"] == 1
        assert schema["properties"]["count"]["maximum"] == 10

        # Recency property
        assert schema["properties"]["recency"]["type"] == "string"
        assert schema["properties"]["recency"]["default"] == "noLimit"
        assert "enum" in schema["properties"]["recency"]

    @pytest.mark.asyncio
    async def test_execute_missing_query(self):
        """Test execute with missing query argument."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider)

        with pytest.raises(ToolValidationError, match="Query must be a non-empty string"):
            await tool.execute({})

    @pytest.mark.asyncio
    async def test_execute_empty_query(self):
        """Test execute with empty query."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider)

        with pytest.raises(ToolValidationError, match="Query cannot be empty or whitespace"):
            await tool.execute({"query": ""})

        with pytest.raises(ToolValidationError, match="Query cannot be empty or whitespace"):
            await tool.execute({"query": "   "})

    @pytest.mark.asyncio
    async def test_execute_invalid_query_type(self):
        """Test execute with non-string query."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider)

        with pytest.raises(ToolValidationError, match="Query must be a non-empty string"):
            await tool.execute({"query": 123})

    @pytest.mark.asyncio
    async def test_execute_invalid_count_type(self):
        """Test execute with invalid count type."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider)

        with pytest.raises(ToolValidationError, match="Count must be a valid integer"):
            await tool.execute({"query": "test", "count": "invalid"})

    @pytest.mark.asyncio
    async def test_execute_count_out_of_range(self):
        """Test execute with count out of valid range."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider, max_results=5)

        # Below minimum
        result1 = await tool.execute({"query": "test", "count": 0})
        assert result1.metadata["requested_count"] == 1

        # Above maximum
        result2 = await tool.execute({"query": "test", "count": 100})
        assert result2.metadata["requested_count"] == 5

    @pytest.mark.asyncio
    async def test_execute_invalid_recency(self):
        """Test execute with invalid recency value."""
        provider = MockSearchProvider()
        tool = WebSearchTool(search_provider=provider)

        with pytest.raises(ToolValidationError, match="Invalid recency value"):
            await tool.execute({"query": "test", "recency": "invalid_value"})

    @pytest.mark.asyncio
    async def test_execute_valid_recency_values(self):
        """Test execute with all valid recency values."""
        from web_search_lib.base import SearchResults

        provider = MockSearchProvider(results=SearchResults(results=[], query="test"))
        tool = WebSearchTool(search_provider=provider)

        recency_values = ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]

        for recency in recency_values:
            result = await tool.execute({"query": "test", "recency": recency})
            assert result.success is False  # No results

    @pytest.mark.asyncio
    async def test_execute_with_results(self):
        """Test execute that returns search results."""
        from web_search_lib.base import SearchResults, SearchResult

        search_result = SearchResult(
            title="Test Result",
            content="This is test content",
            link="https://example.com/test",
        )
        provider = MockSearchProvider(
            results=SearchResults(
                results=[search_result],
                query="test query",
                total=1,
            )
        )
        tool = WebSearchTool(search_provider=provider)

        result = await tool.execute({"query": "test query"})

        assert result.success is True
        assert "Test Result" in result.output
        assert "This is test content" in result.output
        assert result.metadata["provider"] == "MockSearch"
        assert result.metadata["query"] == "test query"
        assert result.metadata["actual_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_no_results(self):
        """Test execute that returns no results."""
        from web_search_lib.base import SearchResults

        provider = MockSearchProvider(results=SearchResults(results=[], query="test"))
        tool = WebSearchTool(search_provider=provider)

        result = await tool.execute({"query": "test"})

        assert result.success is False
        assert "No results found" in result.output

    @pytest.mark.asyncio
    async def test_execute_custom_count(self):
        """Test execute with custom count."""
        from web_search_lib.base import SearchResults, SearchResult

        results = [
            SearchResult(
                title=f"Result {i}",
                content=f"Content {i}",
                link=f"https://example.com/{i}",
            )
            for i in range(5)
        ]
        provider = MockSearchProvider(results=SearchResults(results=results, query="test"))
        tool = WebSearchTool(search_provider=provider)

        result = await tool.execute({"query": "test", "count": 3})

        assert result.metadata["requested_count"] == 3
        # Verify only 3 results are shown in output
        assert "Result 0" in result.output
        assert "Result 2" in result.output
        # Result 3 should not appear
        assert "Result 3" not in result.output

    @pytest.mark.asyncio
    async def test_execute_with_metadata(self):
        """Test that metadata is properly set."""
        from web_search_lib.base import SearchResults, SearchResult

        search_result = SearchResult(
            title="Test",
            content="Content",
            link="https://example.com",
        )
        provider = MockSearchProvider(
            results=SearchResults(
                results=[search_result],
                query="test",
                total=100,
                search_id="abc123",
            )
        )
        tool = WebSearchTool(search_provider=provider)

        result = await tool.execute({"query": "test", "count": 5, "recency": "oneWeek"})

        metadata = result.metadata
        assert metadata["provider"] == "MockSearch"
        assert metadata["query"] == "test"
        assert metadata["requested_count"] == 5
        assert metadata["actual_count"] == 1
        assert metadata["recency"] == "oneWeek"
        assert metadata["total_available"] == 100
        assert metadata["search_id"] == "abc123"
