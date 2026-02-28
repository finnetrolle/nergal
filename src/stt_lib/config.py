"""Configuration for STT providers.

This module provides configuration classes for STT providers using pydantic.
The configuration can be loaded from environment variables with the STT_ prefix.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class STTConfig(BaseSettings):
    """Speech-to-Text provider configuration.

    Configuration can be loaded from environment variables with the STT_ prefix:

    - STT_PROVIDER: Provider type (local, openai)
    - STT_MODEL: Model name (base, small, medium, large-v3)
    - STT_DEVICE: Device for local Whisper (cpu, cuda)
    - STT_COMPUTE_TYPE: Compute type (int8, float16, float32)
    - STT_API_KEY: API key for cloud providers
    - STT_TIMEOUT: Timeout in seconds
    - STT_MAX_DURATION: Maximum audio duration in seconds
    """

    model_config = SettingsConfigDict(
        env_prefix="STT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: str = Field(
        default="local",
        description="STT provider (local, openai)",
    )
    model: str = Field(
        default="base",
        description="STT model (whisper-1 for API, base/small/medium for local)",
    )
    device: str = Field(
        default="cpu",
        description="Device for local Whisper (cpu, cuda)",
    )
    compute_type: str = Field(
        default="int8",
        description="Compute type for local Whisper (int8, float16, float32)",
    )
    api_key: str = Field(
        default="",
        description="API key for STT provider (not needed for local)",
    )
    timeout: float = Field(
        default=60.0,
        description="Transcription timeout in seconds",
    )
    max_duration: int = Field(
        default=60,
        description="Maximum audio duration in seconds (1 minute)",
    )
