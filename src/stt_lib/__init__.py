"""stt_lib - A reusable Speech-to-Text library.

This library provides a clean, independent interface for transcribing
audio to text using various STT providers. It's designed to be reusable
across different applications without any external dependencies.

Example:
    >>> from stt_lib import create_stt_provider, convert_ogg_to_wav
    >>>
    >>> # Create provider
    >>> stt = create_stt_provider(provider_type="local", model="base")
    >>> stt.preload_model()
    >>>
    >>> # Transcribe audio
    >>> with open("audio.wav", "rb") as f:
    ...     text = await stt.transcribe(f, language="ru")
    >>> print(text)

Configuration:
    Configuration can be done via environment variables with STT_ prefix:

    - STT_PROVIDER: Provider type (local, openai)
    - STT_MODEL: Model name
    - STT_DEVICE: Device (cpu, cuda)
    - STT_TIMEOUT: Timeout in seconds

    Or programmatically:

    >>> from stt_lib import STTConfig
    >>> config = STTConfig(provider="local", model="base")
    >>> stt = create_stt_provider(config)
"""

from stt_lib.audio import convert_ogg_to_wav
from stt_lib.base import BaseSTTProvider
from stt_lib.config import STTConfig
from stt_lib.exceptions import (
    AudioTooLongError,
    STTConnectionError,
    STTError,
    STTUnsupportedFormatError,
)
from stt_lib.factory import create_stt_provider
from stt_lib.providers import LocalWhisperProvider

__version__ = "0.1.0"

__all__ = [
    # Core
    "BaseSTTProvider",
    "create_stt_provider",
    # Exceptions
    "STTError",
    "STTConnectionError",
    "STTUnsupportedFormatError",
    "AudioTooLongError",
    # Audio utilities
    "convert_ogg_to_wav",
    # Configuration
    "STTConfig",
    # Providers
    "LocalWhisperProvider",
]
