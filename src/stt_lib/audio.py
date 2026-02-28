"""Audio conversion utilities for STT processing.

This module provides utilities for converting audio formats,
particularly for converting Telegram's OGG/Opus format to WAV.
"""

import logging
from io import BytesIO
from typing import Literal

from pydub import AudioSegment

from stt_lib.exceptions import AudioTooLongError


def convert_ogg_to_wav(
    ogg_data: bytes | bytearray,
    max_duration_seconds: int | None = None,
    sample_rate: int = 16000,
    channels: int = 1,
) -> tuple[BytesIO, float]:
    """Convert OGG audio data (Telegram voice format) to WAV format.

    This function converts OGG/Opus audio (used by Telegram) to WAV format
    with optimized settings for Whisper models (16kHz, mono).

    Args:
        ogg_data: Raw OGG/Opus audio bytes from Telegram or another source.
        max_duration_seconds: Maximum allowed duration in seconds.
                             If None, no duration check is performed.
        sample_rate: Target sample rate in Hz (default: 16000 for Whisper).
        channels: Number of audio channels (default: 1 for mono).

    Returns:
        Tuple of (BytesIO with WAV audio, duration in seconds).
        The BytesIO object is positioned at the beginning for reading.

    Raises:
        AudioTooLongError: If audio duration exceeds max_duration_seconds.
        ValueError: If audio data is invalid or cannot be converted.

    Example:
        >>> with open("voice.ogg", "rb") as f:
        ...     ogg_bytes = f.read()
        >>> wav_audio, duration = convert_ogg_to_wav(
        ...     ogg_bytes,
        ...     max_duration_seconds=60
        ... )
        >>> print(f"Audio duration: {duration:.2f}s")
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

    # Export to WAV format with specified settings
    output = BytesIO()
    audio = audio.set_frame_rate(sample_rate)
    audio = audio.set_channels(channels)
    audio.export(output, format="wav")
    output.seek(0)

    return output, duration_seconds


def convert_audio(
    audio_data: bytes | bytearray,
    input_format: Literal["ogg", "mp3", "wav", "flac"] = "ogg",
    output_format: Literal["wav", "flac"] = "wav",
    max_duration_seconds: int | None = None,
    sample_rate: int = 16000,
    channels: int = 1,
) -> tuple[BytesIO, float]:
    """Convert audio between formats.

    Generic audio conversion function that supports multiple input formats.

    Args:
        audio_data: Raw audio bytes.
        input_format: Input audio format (ogg, mp3, wav, flac).
        output_format: Output audio format (wav, flac).
        max_duration_seconds: Maximum allowed duration in seconds.
        sample_rate: Target sample rate in Hz.
        channels: Number of audio channels.

    Returns:
        Tuple of (BytesIO with converted audio, duration in seconds).

    Raises:
        AudioTooLongError: If audio duration exceeds max_duration_seconds.
        ValueError: If audio data is invalid or format is unsupported.
    """
    logger = logging.getLogger(__name__)

    try:
        # Load audio based on input format
        audio = AudioSegment.from_file(BytesIO(audio_data), format=input_format)
    except Exception as e:
        logger.error(f"Failed to load {input_format.upper()} audio: {e}")
        raise ValueError(f"Invalid {input_format.upper()} audio data: {e}") from e

    # Get duration in seconds
    duration_seconds = len(audio) / 1000.0
    logger.debug(f"Audio duration: {duration_seconds:.2f}s")

    # Check duration limit
    if max_duration_seconds is not None and duration_seconds > max_duration_seconds:
        raise AudioTooLongError(duration_seconds, max_duration_seconds)

    # Export to target format
    output = BytesIO()
    audio = audio.set_frame_rate(sample_rate)
    audio = audio.set_channels(channels)
    audio.export(output, format=output_format)
    output.seek(0)

    return output, duration_seconds
