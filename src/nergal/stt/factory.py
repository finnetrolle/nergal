"""Factory for creating STT providers."""

import logging
from typing import Literal

from nergal.stt.base import BaseSTTProvider
from nergal.stt.providers.local_whisper import LocalWhisperProvider


def create_stt_provider(
    provider_type: Literal["local", "openai"] = "local",
    model: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    api_key: str | None = None,
) -> BaseSTTProvider:
    """Create an STT provider instance based on configuration.

    Args:
        provider_type: Type of STT provider ("local" or "openai").
        model: Model to use for transcription.
        device: Device for local Whisper ("cpu" or "cuda").
        compute_type: Compute type for local Whisper ("int8", "float16", "float32").
        api_key: API key for cloud providers (not needed for local).

    Returns:
        Configured STT provider instance.

    Raises:
        ValueError: If provider type is not supported.
    """
    logger = logging.getLogger(__name__)

    if provider_type == "local":
        logger.info(f"Creating LocalWhisperProvider with model={model}, device={device}")
        return LocalWhisperProvider(
            model=model,
            device=device,
            compute_type=compute_type,
        )
    elif provider_type == "openai":
        # OpenAI provider would be implemented here
        # For now, raise an error
        raise ValueError(
            "OpenAI Whisper API provider is not implemented yet. "
            "Use 'local' provider instead."
        )
    else:
        raise ValueError(
            f"Unsupported STT provider: {provider_type}. "
            f"Supported providers: local, openai"
        )
