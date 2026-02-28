"""Speech-to-Text tool for Nergal.

This module provides the TranscribeTool which wraps the existing
stt_lib to provide speech-to-text capabilities as a tool.

Example:
    >>> from nergal.tools.stt.transcribe import TranscribeTool
    >>> from stt_lib import BaseSTTProvider
    >>>
    >>> tool = TranscribeTool(
    ...     stt_provider=stt_provider,
    ...     default_language="ru"
    ... )
    >>>
    >>> result = await tool.execute({
    ...     "audio_bytes": b"...audio data...",
    ...     "language": "ru"
    ... })
"""

from __future__ import annotations

from io import BytesIO

from nergal.tools.base import Tool, ToolResult
from nergal.tools.exceptions import ToolExecutionError, ToolValidationError


class TranscribeTool(Tool):
    """Tool for transcribing audio to text.

    This tool wraps the existing stt_lib to provide
    speech-to-text capabilities with:
    - Configurable default language
    - Support for WAV format audio
    - Automatic audio format validation

    Attributes:
        stt_provider: The STT provider instance.
        default_language: Default language for transcription.

    Examples:
        Basic usage:
        >>> from stt_lib import BaseSTTProvider
        >>> tool = TranscribeTool(stt_provider, default_language="ru")

        With custom language:
        >>> result = await tool.execute({
        ...     "audio_bytes": audio_data,
        ...     "language": "en"
        ... })
    """

    def __init__(
        self,
        stt_provider,
        default_language: str = "ru",
    ) -> None:
        """Initialize the transcribe tool.

        Args:
            stt_provider: The STT provider instance.
            default_language: Default language for transcription.
        """
        self._stt_provider = stt_provider
        self._default_language = default_language

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "transcribe_audio"

    @property
    def description(self) -> str:
        """Return the tool description."""
        return (
            "Transcribe audio to text using speech-to-text. "
            "Supports WAV format audio. Returns the transcribed text."
        )

    @property
    def parameters_schema(self) -> dict:
        """Return the JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "audio_bytes": {
                    "type": "string",
                    "description": (
                        "Base64-encoded audio data in WAV format. "
                        "The audio should be 16kHz mono WAV for best results."
                    ),
                },
                "language": {
                    "type": "string",
                    "description": "Language code for transcription (e.g., 'ru', 'en').",
                    "default": self._default_language,
                },
            },
            "required": ["audio_bytes"],
        }

    async def execute(self, args: dict) -> ToolResult:
        """Execute audio transcription.

        Args:
            args: Dictionary containing:
                - audio_bytes: Base64-encoded audio bytes (required)
                - language: Language code (optional, defaults to configured default)

        Returns:
            ToolResult containing:
                - success: True if transcription succeeded
                - output: Transcribed text
                - error: Error message if transcription failed
                - metadata: Provider info and language used

        Raises:
            ToolValidationError: If audio_bytes is invalid.
            ToolExecutionError: If transcription fails.
        """
        import base64

        # Validate and extract audio_bytes
        audio_bytes = args.get("audio_bytes")
        if not audio_bytes:
            raise ToolValidationError(
                tool_name=self.name,
                field="audio_bytes",
                message="Audio bytes are required",
            )

        # Decode base64 audio bytes
        try:
            if isinstance(audio_bytes, str):
                decoded_bytes = base64.b64decode(audio_bytes)
            else:
                decoded_bytes = audio_bytes
        except Exception as e:
            raise ToolValidationError(
                tool_name=self.name,
                field="audio_bytes",
                message=f"Failed to decode base64 audio: {e}",
            ) from e

        if not decoded_bytes:
            raise ToolValidationError(
                tool_name=self.name,
                field="audio_bytes",
                message="Audio data is empty after decoding",
            )

        # Extract and validate language
        language = args.get("language", self._default_language)
        if not isinstance(language, str) or not language.strip():
            language = self._default_language

        # Create BytesIO from audio data
        audio_file = BytesIO(decoded_bytes)

        # Transcribe audio
        try:
            transcription = await self._stt_provider.transcribe(
                audio_file,
                language=language,
            )
        except Exception as e:
            # Map stt_lib exceptions to ToolExecutionError
            import stt_lib.exceptions as stt_exceptions

            if isinstance(e, stt_exceptions.STTError):
                raise ToolExecutionError(
                    tool_name=self.name,
                    message=f"STT error: {e}",
                ) from e
            else:
                raise ToolExecutionError(
                    tool_name=self.name,
                    message=f"Unexpected error during transcription: {e}",
                ) from e

        # Validate transcription result
        if not transcription or not transcription.strip():
            return ToolResult(
                success=False,
                output="",
                error="Transcription returned empty result",
                metadata={
                    "provider": self._stt_provider.provider_name,
                    "language": language,
                },
            )

        return ToolResult(
            success=True,
            output=transcription.strip(),
            metadata={
                "provider": self._stt_provider.provider_name,
                "language": language,
                "length": len(transcription),
            },
        )
