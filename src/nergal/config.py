"""Configuration management using pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from nergal.dialog.styles import StyleType


class STTSettings(BaseSettings):
    """Speech-to-Text provider settings."""

    model_config = SettingsConfigDict(
        env_prefix="STT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable voice message processing")
    provider: str = Field(default="local", description="STT provider (local, openai)")
    api_key: str = Field(default="", description="API key for STT provider (not needed for local)")
    model: str = Field(default="base", description="STT model (whisper-1 for API, base/small/medium for local)")
    language: str = Field(default="ru", description="Language code for transcription")
    max_duration_seconds: int = Field(default=60, description="Maximum audio duration in seconds (1 minute)")
    device: str = Field(default="cpu", description="Device for local Whisper (cpu, cuda)")
    compute_type: str = Field(default="int8", description="Compute type for local Whisper (int8, float16, float32)")


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: str = Field(default="zai", description="LLM provider (zai, openai, anthropic, minimax)")
    api_key: str = Field(default="", description="API key for the LLM provider")
    model: str = Field(default="glm-4-flash", description="Model identifier to use")
    base_url: str | None = Field(default=None, description="Optional custom API endpoint")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int | None = Field(default=None, description="Maximum tokens to generate")
    timeout: float = Field(default=120.0, description="Request timeout in seconds")


class WebSearchSettings(BaseSettings):
    """Web search provider settings."""

    model_config = SettingsConfigDict(
        env_prefix="WEB_SEARCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=False, description="Enable web search functionality")
    api_key: str = Field(default="", description="API key for web search (defaults to LLM API key)")
    mcp_url: str = Field(
        default="https://api.z.ai/api/mcp/web_search_prime/mcp",
        description="MCP endpoint URL for web search",
    )
    max_results: int = Field(default=5, ge=1, le=50, description="Maximum search results to return")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str
    log_level: str = "INFO"

    # Response style setting
    style: StyleType = Field(
        default=StyleType.DEFAULT,
        description="Response style (default, silvio_dante)",
    )

    # LLM settings (nested)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    # Web search settings (nested)
    web_search: WebSearchSettings = Field(default_factory=WebSearchSettings)

    # STT settings (nested)
    stt: STTSettings = Field(default_factory=STTSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
