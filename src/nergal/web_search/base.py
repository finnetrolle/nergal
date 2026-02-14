"""Base classes and data models for web search providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SearchRecency(str, Enum):
    """Time filter for search results."""

    ONE_DAY = "oneDay"
    ONE_WEEK = "oneWeek"
    ONE_MONTH = "oneMonth"
    ONE_YEAR = "oneYear"
    NO_LIMIT = "noLimit"


@dataclass
class SearchResult:
    """Represents a single search result.

    Attributes:
        title: Title of the webpage.
        content: Summary/content of the webpage.
        link: URL of the result.
        media: Website name.
        icon: Website favicon URL.
        refer: Index number.
        publish_date: Publication date of the webpage.
    """

    title: str
    content: str
    link: str
    media: str | None = None
    icon: str | None = None
    refer: str | None = None
    publish_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert search result to dictionary."""
        return {
            "title": self.title,
            "content": self.content,
            "link": self.link,
            "media": self.media,
            "icon": self.icon,
            "refer": self.refer,
            "publish_date": self.publish_date,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchResult":
        """Create SearchResult from dictionary."""
        return cls(
            title=data.get("title", ""),
            content=data.get("content", ""),
            link=data.get("link", ""),
            media=data.get("media"),
            icon=data.get("icon"),
            refer=data.get("refer"),
            publish_date=data.get("publish_date"),
        )

    def __str__(self) -> str:
        """Return string representation for display."""
        parts = [f"**{self.title}**"]
        if self.media:
            parts.append(f"_{self.media}_")
        parts.append(self.content)
        parts.append(f"[{self.link}]")
        return "\n".join(parts)


@dataclass
class SearchResults:
    """Container for search results.

    Attributes:
        results: List of search results.
        query: Original search query.
        total: Total number of results (if known).
        search_id: Search task ID from the API.
        created: Unix timestamp of when the search was created.
    """

    results: list[SearchResult]
    query: str
    total: int | None = None
    search_id: str | None = None
    created: int | None = None

    def is_empty(self) -> bool:
        """Check if there are no results."""
        return len(self.results) == 0

    def to_text(self, max_results: int | None = None) -> str:
        """Convert results to a formatted text string.

        Args:
            max_results: Maximum number of results to include.

        Returns:
            Formatted text with all results.
        """
        results_to_show = self.results[:max_results] if max_results else self.results
        if not results_to_show:
            return f"No results found for: {self.query}"

        lines = [f"Search results for: {self.query}\n"]
        for i, result in enumerate(results_to_show, 1):
            lines.append(f"{i}. {result.title}")
            lines.append(f"   {result.content}")
            lines.append(f"   Source: {result.link}")
            if result.media:
                lines.append(f"   Site: {result.media}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "results": [r.to_dict() for r in self.results],
            "query": self.query,
            "total": self.total,
            "search_id": self.search_id,
            "created": self.created,
        }


@dataclass
class SearchRequest:
    """Search request parameters.

    Attributes:
        query: Search query string.
        count: Number of results to return (1-50).
        recency: Time filter for results.
        domain_filter: Domain whitelist filter.
    """

    query: str
    count: int = 10
    recency: SearchRecency = SearchRecency.NO_LIMIT
    domain_filter: str | None = None

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not self.query.strip():
            raise ValueError("Search query cannot be empty")
        if not 1 <= self.count <= 50:
            raise ValueError("Count must be between 1 and 50")


class SearchError(Exception):
    """Base exception for search-related errors."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}" if provider else message)


class SearchRateLimitError(SearchError):
    """Raised when rate limit is exceeded."""

    pass


class SearchProviderError(SearchError):
    """Raised when the search provider returns an error."""

    pass


class BaseSearchProvider(ABC):
    """Abstract base class for web search providers.

    All search providers should inherit from this class
    and implement the required methods.
    """

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> None:
        """Initialize the search provider.

        Args:
            api_key: API key for authentication.
            timeout: Request timeout in seconds.
            **kwargs: Additional provider-specific configuration.
        """
        self.api_key = api_key
        self.timeout = timeout
        self.config = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider."""
        pass

    @abstractmethod
    async def search(self, request: SearchRequest) -> SearchResults:
        """Perform a web search.

        Args:
            request: Search request parameters.

        Returns:
            SearchResults containing the search results.

        Raises:
            SearchError: If the search fails.
        """
        pass

    async def close(self) -> None:
        """Close any resources used by the provider.

        Override this method if the provider needs to clean up resources.
        """
        pass

    def validate_config(self) -> None:
        """Validate the provider configuration.

        Raises:
            ValueError: If configuration is invalid.
        """
        if not self.api_key:
            raise ValueError(f"{self.provider_name}: API key is required")
