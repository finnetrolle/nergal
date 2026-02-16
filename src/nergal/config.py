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


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings."""

    model_config = SettingsConfigDict(
        env_prefix="MONITORING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable monitoring and metrics collection")
    metrics_port: int = Field(default=8000, description="Port for Prometheus metrics endpoint")
    json_logs: bool = Field(default=True, description="Use JSON format for logs (recommended for production)")
    log_level: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    user: str = Field(default="nergal", description="Database user")
    password: str = Field(default="nergal_secret", description="Database password")
    name: str = Field(default="nergal", description="Database name")
    min_pool_size: int = Field(default=5, description="Minimum connection pool size")
    max_pool_size: int = Field(default=20, description="Maximum connection pool size")
    connection_timeout: float = Field(default=30.0, description="Connection timeout in seconds")

    @property
    def dsn(self) -> str:
        """Get the database connection string (DSN)."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def async_dsn(self) -> str:
        """Get the async database connection string (DSN) for asyncpg."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class MemorySettings(BaseSettings):
    """Memory system settings."""

    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Short-term memory settings
    short_term_max_messages: int = Field(
        default=50, description="Maximum number of messages in short-term memory"
    )
    short_term_session_timeout: int = Field(
        default=3600, description="Session timeout in seconds (1 hour)"
    )

    # Long-term memory settings
    long_term_enabled: bool = Field(
        default=True, description="Enable long-term memory (user profiles)"
    )
    long_term_extraction_enabled: bool = Field(
        default=True, description="Enable automatic extraction of facts for long-term memory"
    )
    long_term_confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum confidence to store extracted fact"
    )

    # Memory cleanup
    cleanup_days: int = Field(
        default=30, description="Days to keep old messages before cleanup"
    )


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
    admin_port: int = Field(
        default=8001, description="Port for admin web interface"
    )
    admin_enabled: bool = Field(
        default=True, description="Enable admin web interface"
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

    # Monitoring settings (nested)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)

    # Database settings (nested)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # Memory settings (nested)
    memory: MemorySettings = Field(default_factory=MemorySettings)

    # Authorization settings (nested)
    auth: AuthSettings = Field(default_factory=AuthSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
