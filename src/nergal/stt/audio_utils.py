"""Audio conversion utilities for STT processing."""

import logging
from io import BytesIO

from pydub import AudioSegment


class AudioTooLongError(Exception):
    """Raised when audio duration exceeds the maximum allowed."""

    def __init__(self, duration_seconds: float, max_seconds: int):
        self.duration_seconds = duration_seconds
        self.max_seconds = max_seconds
        super().__init__(
            f"Audio duration {duration_seconds:.1f}s exceeds maximum allowed {max_seconds}s"
        )


def convert_ogg_to_wav(
    ogg_data: bytes | bytearray,
    max_duration_seconds: int | None = None,
) -> tuple[BytesIO, float]:
    """Convert OGG audio data (Telegram voice format) to WAV format.

    Args:
        ogg_data: Raw OGG/Opus audio bytes from Telegram.
        max_duration_seconds: Maximum allowed duration in seconds.
                             If None, no duration check is performed.

    Returns:
        Tuple of ( BytesIO with WAV audio, duration in seconds).

    Raises:
        AudioTooLongError: If audio duration exceeds max_duration_seconds.
        ValueError: If audio data is invalid.
    """
    logger = logging.getLogger(__name__)

    try:
        # Load OGG audio (Telegram uses Opus codec in OGG container)
        audio = AudioSegment.from_ogg(BytesIO(ogg_data))
    except Exception as e:
        logger.error(f"Failed to load OGG audio: {e}")
        raise ValueError(f"Invalid OGG audio data: {e}") from e

    # Get duration in seconds
    duration_seconds = len(audio) / 1000.0
    logger.debug(f"Audio duration: {duration_seconds:.2f}s")

    # Check duration limit
    if max_duration_seconds is not None and duration_seconds > max_duration_seconds:
        raise AudioTooLongError(duration_seconds, max_duration_seconds)

    # Export to WAV format (16kHz mono, optimal for Whisper)
    output = BytesIO()
    audio = audio.set_frame_rate(16000)  # 16kHz sample rate
    audio = audio.set_channels(1)  # Mono
    audio.export(output, format="wav")
    output.seek(0)

    return output, duration_seconds
