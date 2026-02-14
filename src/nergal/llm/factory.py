"""Factory for creating LLM providers."""

from enum import Enum
from typing import Any

from nergal.llm.base import BaseLLMProvider, LLMError
from nergal.llm.providers.zai import ZaiProvider


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""

    ZAI = "zai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MINIMAX = "minimax"


# Registry of provider implementations
# New providers should be added here
_PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {
    LLMProviderType.ZAI: ZaiProvider,
    # Future providers will be added here:
    # LLMProviderType.OPENAI: OpenAIProvider,
    # LLMProviderType.ANTHROPIC: AnthropicProvider,
    # LLMProviderType.MINIMAX: MinimaxProvider,
}


def create_llm_provider(
    provider_type: str | LLMProviderType,
    api_key: str,
    model: str,
    base_url: str | None = None,
    **kwargs: Any,
) -> BaseLLMProvider:
    """Create an LLM provider instance.

    This factory function creates the appropriate provider based on the
    specified type. New providers can be easily added by extending the
    registry.

    Args:
        provider_type: Type of provider (e.g., 'zai', 'openai', 'anthropic').
        api_key: API key for authentication.
        model: Model identifier to use.
        base_url: Optional custom API endpoint.
        **kwargs: Additional provider-specific configuration.

    Returns:
        Configured LLM provider instance.

    Raises:
        LLMError: If the provider type is not supported.

    Example:
        >>> provider = create_llm_provider(
        ...     provider_type="zai",
        ...     api_key="your-api-key",
        ...     model="glm-4-flash"
        ... )
        >>> response = await provider.generate(messages)
    """
    # Normalize provider type to string
    provider_key = provider_type.value if isinstance(provider_type, Enum) else provider_type
    provider_key = provider_key.lower()

    provider_class = _PROVIDER_REGISTRY.get(provider_key)

    if provider_class is None:
        supported = ", ".join(_PROVIDER_REGISTRY.keys())
        raise LLMError(
            f"Unsupported provider type: {provider_type}. "
            f"Supported providers: {supported}"
        )

    return provider_class(
        api_key=api_key,
        model=model,
        base_url=base_url,
        **kwargs,
    )


def register_provider(provider_type: str, provider_class: type[BaseLLMProvider]) -> None:
    """Register a new LLM provider.

    This allows extending the factory with custom providers without
    modifying the factory code directly.

    Args:
        provider_type: Unique identifier for the provider.
        provider_class: Provider class (must inherit from BaseLLMProvider).

    Example:
        >>> class CustomProvider(BaseLLMProvider):
        ...     # Implementation
        ...     pass
        >>> register_provider("custom", CustomProvider)
        >>> provider = create_llm_provider("custom", api_key="...", model="...")
    """
    _PROVIDER_REGISTRY[provider_type.lower()] = provider_class


def get_supported_providers() -> list[str]:
    """Get list of supported provider types.

    Returns:
        List of provider type identifiers.
    """
    return list(_PROVIDER_REGISTRY.keys())
