"""Factory for creating STT providers."""

import logging
from typing import Literal

from stt_lib.base import BaseSTTProvider
from stt_lib.config import STTConfig
from stt_lib.providers import LocalWhisperProvider


def create_stt_provider(
    config: STTConfig | None = None,
    provider_type: Literal["local", "openai"] | None = None,
    model: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
    api_key: str | None = None,
    timeout: float | None = None,
) -> BaseSTTProvider:
    """Create an STT provider instance based on configuration.

    This is a flexible factory function that can accept either a config object
    or individual parameters. Config object takes precedence.

    Args:
        config: STTConfig object with all settings. If provided, individual
               parameters are ignored.
        provider_type: Type of STT provider ("local" or "openai").
                       Ignored if config is provided.
        model: Model to use for transcription. Ignored if config is provided.
        device: Device for local Whisper ("cpu" or "cuda").
               Ignored if config is provided.
        compute_type: Compute type for local Whisper ("int8", "float16", "float32").
                     Ignored if config is provided.
        api_key: API key for cloud providers (not needed for local).
               Ignored if config is provided.
        timeout: Timeout in seconds for transcription.
                Ignored if config is provided.

    Returns:
        Configured STT provider instance.

    Raises:
        ValueError: If provider type is not supported.

    Example:
        >>> # Using config object
        >>> config = STTConfig(provider="local", model="base")
        >>> stt = create_stt_provider(config)

        >>> # Using individual parameters
        >>> stt = create_stt_provider(
        ...     provider_type="local",
        ...     model="base",
        ...     device="cpu"
        ... )

        >>> # Pre-load model for faster first transcription
        >>> stt.preload_model()
    """
    logger = logging.getLogger(__name__)

    # Use config if provided, otherwise build from individual parameters
    if config is None:
        if provider_type is None:
            provider_type = "local"
        if model is None:
            model = "base"
        if device is None:
            device = "cpu"
        if compute_type is None:
            compute_type = "int8"
        if timeout is None:
            timeout = 60.0
    else:
        provider_type = config.provider
        model = config.model
        device = config.device
        compute_type = config.compute_type
        timeout = config.timeout

    # Create provider based on type
    if provider_type == "local":
        logger.info(f"Creating LocalWhisperProvider with model={model}, device={device}")
        return LocalWhisperProvider(
            model=model,
            device=device,
            compute_type=compute_type,
            timeout=timeout,
        )
    elif provider_type == "openai":
        # OpenAI provider would be implemented here
        raise ValueError(
            "OpenAI Whisper API provider is not implemented yet. Use 'local' provider instead."
        )
    else:
        raise ValueError(
            f"Unsupported STT provider: {provider_type}. Supported providers: local, openai"
        )
