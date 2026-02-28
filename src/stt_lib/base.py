"""Base class for STT providers."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class BaseSTTProvider(ABC):
    """Abstract base class for STT providers.

    All STT providers must implement this interface. The provider
    is responsible for transcribing audio data to text.

    Example:
        >>> provider = create_stt_provider()
        >>> with open("audio.wav", "rb") as f:
        ...     text = await provider.transcribe(f, language="ru")
        >>> print(text)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the STT provider.

        Returns:
            Provider name string (e.g., "local_whisper", "openai_whisper").
        """
        pass

    def preload_model(self) -> None:
        """Pre-load the model to avoid timeout on first transcription.

        This method should be called at startup to ensure the model is loaded
        before any transcription requests come in. Default implementation does nothing.

        Example:
            >>> provider = create_stt_provider()
            >>> provider.preload_model()  # Load model on startup
            >>> # Later, transcription will be faster
        """
        pass  # noqa: B027  # Intentional empty default implementation

    @abstractmethod
    async def transcribe(
        self,
        audio_data: BinaryIO,
        language: str = "ru",
    ) -> str:
        """Transcribe audio data to text.

        Args:
            audio_data: Audio file-like object (BytesIO or file handle).
                        The audio should be in WAV format (16kHz mono recommended).
            language: Language code for transcription (e.g., "ru", "en").

        Returns:
            Transcribed text string.

        Raises:
            STTError: If transcription fails.
            STTConnectionError: If there's a network or connection issue.
            STTUnsupportedFormatError: If the audio format is not supported.
        """
        pass
