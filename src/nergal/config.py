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
    timeout: float = Field(default=60.0, description="Transcription timeout in seconds")


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


class AuthSettings(BaseSettings):
    """Authorization settings."""

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(
        default=True, description="Enable user authorization (only allowed users can use bot)"
    )
    admin_user_ids: list[int] = Field(
        default_factory=list, description="List of admin Telegram user IDs"
    )


class GroupChatSettings(BaseSettings):
    """Group chat settings."""

    model_config = SettingsConfigDict(
        env_prefix="GROUP_CHAT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(
        default=True, description="Enable bot to work in group chats"
    )
    bot_name: str = Field(
        default="Sil", description="Bot name to detect mentions in messages"
    )
    bot_username: str = Field(
        default="", description="Bot Telegram username (without @) for mention detection"
    )
    respond_to_replies: bool = Field(
        default=True, description="Respond when someone replies to bot's message"
    )
    respond_to_mentions: bool = Field(
        default=True, description="Respond when bot name or username is mentioned in message"
    )


class CacheSettings(BaseSettings):
    """Cache settings for agent results."""

    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(
        default=True, description="Enable caching of agent results"
    )
    ttl_seconds: int = Field(
        default=300, ge=0, description="Time-to-live for cache entries in seconds (default: 5 minutes)"
    )
    max_size: int = Field(
        default=1000, ge=1, description="Maximum number of entries in the cache"
    )


class AgentSettings(BaseSettings):
    """Agent registration settings."""

    model_config = SettingsConfigDict(
        env_prefix="AGENTS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Enable/disable specific agents
    web_search_enabled: bool = Field(
        default=True, description="Enable WebSearchAgent"
    )


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

    # Agent settings (nested)
    agents: AgentSettings = Field(default_factory=AgentSettings)

    # Authorization settings (nested)
    auth: AuthSettings = Field(default_factory=AuthSettings)

    # Group chat settings (nested)
    group_chat: GroupChatSettings = Field(default_factory=GroupChatSettings)

    # Cache settings (nested)
    cache: CacheSettings = Field(default_factory=CacheSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
