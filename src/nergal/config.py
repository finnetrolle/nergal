"""Configuration management using pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    model: str = Field(
        default="base", description="STT model (whisper-1 for API, base/small/medium for local)"
    )
    language: str = Field(default="ru", description="Language code for transcription")
    max_duration_seconds: int = Field(
        default=60, description="Maximum audio duration in seconds (1 minute)"
    )
    device: str = Field(default="cpu", description="Device for local Whisper (cpu, cuda)")
    compute_type: str = Field(
        default="int8", description="Compute type for local Whisper (int8, float16, float32)"
    )
    timeout: float = Field(default=60.0, description="Transcription timeout in seconds")


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: str = Field(
        default="zai", description="LLM provider (zai, openai, anthropic, minimax)"
    )
    api_key: str = Field(default="", description="API key for the LLM provider")
    model: str = Field(default="glm-4-flash", description="Model identifier to use")
    base_url: str | None = Field(default=None, description="Optional custom API endpoint")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int | None = Field(default=None, description="Maximum tokens to generate")
    max_history: int = Field(default=20, ge=1, le=100, description="Maximum message history length")
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


class GroupChatSettings(BaseSettings):
    """Group chat settings."""

    model_config = SettingsConfigDict(
        env_prefix="GROUP_CHAT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable bot to work in group chats")
    bot_name: str = Field(default="Sil", description="Bot name to detect mentions in messages")
    bot_username: str = Field(
        default="", description="Bot Telegram username (without @) for mention detection"
    )
    respond_to_replies: bool = Field(
        default=True, description="Respond when someone replies to bot's message"
    )
    respond_to_mentions: bool = Field(
        default=True, description="Respond when bot name or username is mentioned in message"
    )


class MemorySettings(BaseSettings):
    """Memory system settings."""

    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable persistent memory system")
    db_path: str = Field(
        default="~/.nergal/memory.db",
        description="Path to SQLite database for memory",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum results to recall from memory",
    )
    chunk_size: int = Field(
        default=500,
        ge=100,
        le=5000,
        description="Text chunk size in characters",
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=500,
        description="Character overlap between chunks",
    )


class SecuritySettings(BaseSettings):
    """Security settings."""

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    autonomy_level: str = Field(
        default="limited",
        description="Autonomy level: read_only, limited, full",
    )
    workspace_dir: str = Field(
        default="~/.nergal/workspace",
        description="Directory for file operations",
    )
    workspace_only: bool = Field(
        default=True,
        description="Restrict file access to workspace",
    )
    allowed_commands: list[str] = Field(
        default=[],
        description="Allowlist for shell commands (empty = no commands)",
    )
    allowed_domains: list[str] = Field(
        default=[],
        description="Allowlist for HTTP domains (empty = no restriction)",
    )
    max_actions_per_hour: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum tool actions per hour",
    )
    max_tool_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum tool iteration loops per message",
    )


class SkillsSettings(BaseSettings):
    """Skills system settings."""

    model_config = SettingsConfigDict(
        env_prefix="SKILLS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable skills system")
    skills_dir: str = Field(
        default="~/.nergal/skills",
        description="Directory containing skill definitions",
    )
    active_skills: list[str] = Field(
        default=[],
        description="List of active skill names (empty = all)",
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

    # LLM settings (nested)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    # Web search settings (nested)
    web_search: WebSearchSettings = Field(default_factory=WebSearchSettings)

    # STT settings (nested)
    stt: STTSettings = Field(default_factory=STTSettings)

    # Group chat settings (nested)
    group_chat: GroupChatSettings = Field(default_factory=GroupChatSettings)

    # Memory settings (nested)
    memory: MemorySettings = Field(default_factory=MemorySettings)

    # Security settings (nested)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # Skills settings (nested)
    skills: SkillsSettings = Field(default_factory=SkillsSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
