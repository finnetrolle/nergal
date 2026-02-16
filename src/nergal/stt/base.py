"""Base class for Speech-to-Text providers."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class BaseSTTProvider(ABC):
    """Abstract base class for STT providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the STT provider.

        Returns:
            Provider name string.
        """
        pass

    def preload_model(self) -> None:
        """Pre-load the model to avoid timeout on first transcription.

        This method should be called at startup to ensure the model is loaded
        before any transcription requests come in. Default implementation does nothing.
        """
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_data: BinaryIO,
        language: str = "ru",
    ) -> str:
        """Transcribe audio data to text.

        Args:
            audio_data: Audio file-like object ( BytesIO or file handle).
            language: Language code for transcription (e.g., "ru", "en").

        Returns:
            Transcribed text string.

        Raises:
            TranscriptionError: If transcription fails.
        """
        pass
