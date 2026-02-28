"""Local Whisper STT provider using faster-whisper."""

import asyncio
import logging
from typing import BinaryIO

from faster_whisper import WhisperModel

from stt_lib.base import BaseSTTProvider
from stt_lib.exceptions import STTError


class LocalWhisperProvider(BaseSTTProvider):
    """Local Whisper STT provider using faster-whisper.

    This provider runs Whisper locally on CPU or GPU using the faster-whisper
    library, which is optimized for inference using CTranslate2.

    Example:
        >>> provider = LocalWhisperProvider(model="base", device="cpu")
        >>> provider.preload_model()  # Optional: load on startup
        >>> with open("audio.wav", "rb") as f:
        ...     text = await provider.transcribe(f, language="ru")
        >>> print(text)
    """

    def __init__(
        self,
        model: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        timeout: float = 60.0,
    ):
        """Initialize the local Whisper provider.

        Args:
            model: Model size to use (tiny, base, small, medium, large-v3).
                   Smaller models are faster but less accurate.
            device: Device to run on ("cpu" or "cuda").
                   Use "cuda" for GPU acceleration.
            compute_type: Computation type ("int8", "float16", "float32").
                         Use "int8" for CPU, "float16" for GPU.
            timeout: Timeout in seconds for transcription.
        """
        self._model_name = model
        self._device = device
        self._compute_type = compute_type
        self._timeout = timeout
        self._model: WhisperModel | None = None
        self._logger = logging.getLogger(__name__)

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "local_whisper"

    def preload_model(self) -> None:
        """Pre-load the Whisper model to avoid timeout on first transcription.

        This method should be called at startup to ensure the model is loaded
        before any transcription requests come in.

        Example:
            >>> provider = LocalWhisperProvider(model="base")
            >>> provider.preload_model()
        """
        self._logger.info(
            f"Pre-loading Whisper model: {self._model_name}, "
            f"device: {self._device}, compute_type: {self._compute_type}"
        )
        self._model = WhisperModel(
            self._model_name,
            device=self._device,
            compute_type=self._compute_type,
        )
        self._logger.info(f"Whisper model {self._model_name} pre-loaded successfully")

    def _get_model(self) -> WhisperModel:
        """Lazy load the Whisper model to save memory.

        Returns:
            Loaded WhisperModel instance.
        """
        if self._model is None:
            self._logger.info(
                f"Loading Whisper model: {self._model_name}, "
                f"device: {self._device}, compute_type: {self._compute_type}"
            )
            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type,
            )
            self._logger.info(f"Whisper model {self._model_name} loaded successfully")
        return self._model

    async def transcribe(
        self,
        audio_data: BinaryIO,
        language: str = "ru",
    ) -> str:
        """Transcribe audio data using local Whisper model.

        Args:
            audio_data: Audio file-like object (WAV format recommended).
            language: Language code for transcription (e.g., "ru", "en").

        Returns:
            Transcribed text string.

        Raises:
            STTError: If transcription fails.
            asyncio.TimeoutError: If transcription times out.
        """
        loop = asyncio.get_event_loop()

        def _transcribe() -> str:
            model = self._get_model()
            try:
                segments, info = model.transcribe(
                    audio_data,
                    language=language,
                    beam_size=5,
                    vad_filter=True,  # Voice Activity Detection filter
                )
                text = "".join(segment.text for segment in segments)
                self._logger.debug(
                    f"Transcription completed: language={info.language}, "
                    f"probability={info.language_probability:.2f}, "
                    f"duration={info.duration:.2f}s"
                )
                return text.strip()
            except Exception as e:
                self._logger.error(f"Transcription failed: {e}")
                raise STTError(f"Transcription failed: {e}") from e

        # Run in thread pool to avoid blocking the event loop with timeout
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, _transcribe), timeout=self._timeout
            )
        except TimeoutError:
            self._logger.error(f"Transcription timed out after {self._timeout}s")
            raise
