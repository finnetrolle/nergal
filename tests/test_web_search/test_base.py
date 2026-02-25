"""Tests for web_search base classes and data models."""

import pytest

from nergal.web_search.base import (
    SearchRecency,
    SearchResult,
    SearchResults,
    SearchRequest,
    SearchProviderError,
    BaseSearchProvider,
)


class TestSearchRecency:
    """Tests for SearchRecency enum."""

    def test_recency_values(self) -> None:
        """Test that all recency values are defined."""
        assert SearchRecency.ONE_DAY.value == "oneDay"
        assert SearchRecency.ONE_WEEK.value == "oneWeek"
        assert SearchRecency.ONE_MONTH.value == "oneMonth"
        assert SearchRecency.ONE_YEAR.value == "oneYear"
        assert SearchRecency.NO_LIMIT.value == "noLimit"


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_create_minimal(self) -> None:
        """Test creating a minimal search result."""
        result = SearchResult(
            title="Test Title",
            content="Test content",
            link="https://example.com",
        )
        assert result.title == "Test Title"
        assert result.content == "Test content"
        assert result.link == "https://example.com"
        assert result.media is None
        assert result.icon is None

    def test_create_full(self) -> None:
        """Test creating a full search result."""
        result = SearchResult(
            title="Test Title",
            content="Test content",
            link="https://example.com",
            media="Example Site",
            icon="https://example.com/favicon.ico",
            refer="1",
            publish_date="2024-01-01",
        )
        assert result.media == "Example Site"
        assert result.icon == "https://example.com/favicon.ico"
        assert result.refer == "1"
        assert result.publish_date == "2024-01-01"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        result = SearchResult(
            title="Test",
            content="Content",
            link="https://example.com",
            media="Site",
        )
        data = result.to_dict()
        assert data["title"] == "Test"
        assert data["content"] == "Content"
        assert data["link"] == "https://example.com"
        assert data["media"] == "Site"
        assert data["icon"] is None

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "title": "Test",
            "content": "Content",
            "link": "https://example.com",
            "media": "Site",
        }
        result = SearchResult.from_dict(data)
        assert result.title == "Test"
        assert result.content == "Content"
        assert result.link == "https://example.com"
        assert result.media == "Site"

    def test_str_representation(self) -> None:
        """Test string representation."""
        result = SearchResult(
            title="Test Title",
            content="Test content",
            link="https://example.com",
            media="Example",
        )
        s = str(result)
        assert "**Test Title**" in s
        assert "_Example_" in s
        assert "Test content" in s
        assert "https://example.com" in s


class TestSearchResults:
    """Tests for SearchResults dataclass."""

    @pytest.fixture
    def sample_results(self) -> SearchResults:
        """Create sample search results."""
        return SearchResults(
            results=[
                SearchResult(
                    title="Result 1",
                    content="Content 1",
                    link="https://example.com/1",
                ),
                SearchResult(
                    title="Result 2",
                    content="Content 2",
                    link="https://example.com/2",
                ),
            ],
            query="test query",
            total=2,
            search_id="abc123",
            created=1234567890,
        )

    def test_is_empty_false(self, sample_results: SearchResults) -> None:
        """Test is_empty returns False when there are results."""
        assert sample_results.is_empty() is False

    def test_is_empty_true(self) -> None:
        """Test is_empty returns True when there are no results."""
        results = SearchResults(results=[], query="test")
        assert results.is_empty() is True

    def test_has_results_true(self, sample_results: SearchResults) -> None:
        """Test has_results returns True when there are results."""
        assert sample_results.has_results() is True

    def test_has_results_false(self) -> None:
        """Test has_results returns False when there are no results."""
        results = SearchResults(results=[], query="test")
        assert results.has_results() is False

    def test_to_text(self, sample_results: SearchResults) -> None:
        """Test converting results to text."""
        text = sample_results.to_text()
        assert "test query" in text
        assert "Result 1" in text
        assert "Result 2" in text
        assert "https://example.com/1" in text

    def test_to_text_max_results(self, sample_results: SearchResults) -> None:
        """Test converting results to text with max_results limit."""
        text = sample_results.to_text(max_results=1)
        assert "Result 1" in text
        assert "Result 2" not in text

    def test_to_text_empty(self) -> None:
        """Test converting empty results to text."""
        results = SearchResults(results=[], query="test")
        text = results.to_text()
        assert "No results found" in text

    def test_to_dict(self, sample_results: SearchResults) -> None:
        """Test converting to dictionary."""
        data = sample_results.to_dict()
        assert data["query"] == "test query"
        assert data["total"] == 2
        assert data["search_id"] == "abc123"
        assert len(data["results"]) == 2


class TestSearchRequest:
    """Tests for SearchRequest dataclass."""

    def test_create_minimal(self) -> None:
        """Test creating a minimal search request."""
        request = SearchRequest(query="test query")
        assert request.query == "test query"
        assert request.count == 10
        assert request.recency == SearchRecency.NO_LIMIT
        assert request.domain_filter is None

    def test_create_full(self) -> None:
        """Test creating a full search request."""
        request = SearchRequest(
            query="test query",
            count=20,
            recency=SearchRecency.ONE_WEEK,
            domain_filter="example.com",
        )
        assert request.count == 20
        assert request.recency == SearchRecency.ONE_WEEK
        assert request.domain_filter == "example.com"

    def test_empty_query_raises(self) -> None:
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SearchRequest(query="")

    def test_whitespace_query_raises(self) -> None:
        """Test that whitespace-only query raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SearchRequest(query="   ")

    def test_count_too_low_raises(self) -> None:
        """Test that count below 1 raises ValueError."""
        with pytest.raises(ValueError, match="must be between"):
            SearchRequest(query="test", count=0)

    def test_count_too_high_raises(self) -> None:
        """Test that count above 50 raises ValueError."""
        with pytest.raises(ValueError, match="must be between"):
            SearchRequest(query="test", count=51)


class TestSearchProviderError:
    """Tests for SearchProviderError exception."""

    def test_create_error(self) -> None:
        """Test creating a SearchProviderError."""
        error = SearchProviderError("Test error")
        assert str(error) == "Test error"

    def test_with_provider(self) -> None:
        """Test creating error with provider name."""
        error = SearchProviderError("Test error", provider="TestProvider")
        assert "TestProvider" in str(error)


class MockSearchProvider(BaseSearchProvider):
    """Mock search provider for testing."""

    @property
    def provider_name(self) -> str:
        return "MockProvider"

    async def search(self, request: SearchRequest) -> SearchResults:
        return SearchResults(results=[], query=request.query)


class TestBaseSearchProvider:
    """Tests for BaseSearchProvider."""

    def test_init(self) -> None:
        """Test initializing a search provider."""
        provider = MockSearchProvider(api_key="test_key", timeout=60.0)
        assert provider.api_key == "test_key"
        assert provider.timeout == 60.0

    def test_validate_config_empty_key(self) -> None:
        """Test that empty API key raises ValueError."""
        provider = MockSearchProvider(api_key="")
        with pytest.raises(ValueError, match="API key is required"):
            provider.validate_config()

    def test_validate_config_valid(self) -> None:
        """Test that valid config passes validation."""
        provider = MockSearchProvider(api_key="test_key")
        provider.validate_config()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_default(self) -> None:
        """Test default close method does nothing."""
        provider = MockSearchProvider(api_key="test_key")
        await provider.close()  # Should not raise
