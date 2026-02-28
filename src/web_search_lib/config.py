"""Configuration for web search providers.

This module provides configuration classes for web search providers using pydantic.
The configuration can be loaded from environment variables with the WEB_SEARCH_ prefix.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebSearchConfig(BaseSettings):
    """Web search provider configuration.

    Configuration can be loaded from environment variables with the WEB_SEARCH_ prefix:

    - WEB_SEARCH_PROVIDER: Provider type (zai, google, bing, serpapi)
    - WEB_SEARCH_API_KEY: API key for the search provider
    - WEB_SEARCH_TIMEOUT: Timeout in seconds
    - WEB_SEARCH_MAX_RESULTS: Maximum number of results to return
    - WEB_SEARCH_DEFAULT_COUNT: Default number of results per search
    - WEB_SEARCH_DEFAULT_RECENCY: Default time filter for results
    """

    model_config = SettingsConfigDict(
        env_prefix="WEB_SEARCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: str = Field(
        default="zai",
        description="Web search provider (zai, google, bing, serpapi)",
    )
    api_key: str = Field(
        default="",
        description="API key for search provider",
    )
    timeout: float = Field(
        default=30.0,
        description="Search request timeout in seconds",
    )
    max_results: int = Field(
        default=50,
        description="Maximum number of results to return (API limit)",
    )
    default_count: int = Field(
        default=10,
        description="Default number of results to return per search",
    )
    default_recency: str = Field(
        default="noLimit",
        description="Default time filter (oneDay, oneWeek, oneMonth, oneYear, noLimit)",
    )
