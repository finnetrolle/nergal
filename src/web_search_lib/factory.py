"""Factory for creating web search providers."""

import logging
from typing import Literal

from web_search_lib.base import BaseSearchProvider
from web_search_lib.config import WebSearchConfig
from web_search_lib.providers import ZaiMcpHttpSearchProvider
from web_search_lib.reliability import CircuitBreaker, RetryConfig


def create_search_provider(
    config: WebSearchConfig | None = None,
    provider_type: Literal["zai"] | None = None,
    api_key: str | None = None,
    timeout: float | None = None,
    retry_config: RetryConfig | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> BaseSearchProvider:
    """Create a web search provider instance based on configuration.

    This is a flexible factory function that can accept either a config object
    or individual parameters. Config object takes precedence.

    Args:
        config: WebSearchConfig object with all settings. If provided, individual
               parameters are ignored.
        provider_type: Type of search provider ("zai"). Ignored if config is provided.
        api_key: API key for the search provider. Ignored if config is provided.
        timeout: Timeout in seconds for search requests. Ignored if config is provided.
        retry_config: Optional retry configuration for the provider.
        circuit_breaker: Optional circuit breaker instance for the provider.

    Returns:
        Configured web search provider instance.

    Raises:
        ValueError: If provider type is not supported.

    Example:
        >>> # Using config object
        >>> config = WebSearchConfig(provider="zai", api_key="your-key")
        >>> search = create_search_provider(config)
        >>> request = SearchRequest(query="python async await")
        >>> results = await search.search(request)

        >>> # Using individual parameters
        >>> search = create_search_provider(
        ...     provider_type="zai",
        ...     api_key="your-key",
        ...     timeout=30.0
        ... )
    """
    logger = logging.getLogger(__name__)

    # Use config if provided, otherwise build from individual parameters
    if config is None:
        if provider_type is None:
            provider_type = "zai"
        if timeout is None:
            timeout = 30.0
    else:
        # provider_type is str from config, but function expects Literal | None
        actual_provider_type: str = config.provider
        provider_type = actual_provider_type  # type: ignore[assignment]
        api_key = api_key or config.api_key
        timeout = timeout or config.timeout

    # Create provider based on type
    if provider_type == "zai":
        logger.info(f"Creating ZaiMcpHttpSearchProvider with timeout={timeout}")
        return ZaiMcpHttpSearchProvider(
            api_key=api_key or "",
            timeout=timeout,
            retry_config=retry_config,
            circuit_breaker=circuit_breaker,
        )
    else:
        raise ValueError(
            f"Unsupported web search provider: {provider_type}. Supported providers: zai"
        )
