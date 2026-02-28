"""Configuration for LLM providers."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMConfig:
    """Configuration for LLM providers.

    Attributes:
        provider: Type of LLM provider (zai, openai, anthropic, minimax).
        api_key: API key for authentication.
        model: Model identifier to use.
        base_url: Optional custom API endpoint.
        temperature: Sampling temperature (0.0 to 2.0).
        max_tokens: Maximum tokens to generate.
        timeout: Request timeout in seconds.
        **kwargs: Additional provider-specific configuration.
    """

    provider: str = "zai"
    api_key: str = ""
    model: str = "glm-4-flash"
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    timeout: float = 120.0
    extra_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration.
        """
        config: dict[str, Any] = {
            "provider": self.provider,
            "api_key": self.api_key,
            "model": self.model,
            "temperature": self.temperature,
            "timeout": self.timeout,
        }

        if self.base_url:
            config["base_url"] = self.base_url

        if self.max_tokens is not None:
            config["max_tokens"] = self.max_tokens

        config.update(self.extra_config)

        return config
