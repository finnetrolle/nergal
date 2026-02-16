"""Speech-to-Text module for voice message transcription."""

from nergal.exceptions import AudioTooLongError, STTError
from nergal.stt.audio_utils import convert_ogg_to_wav
from nergal.stt.base import BaseSTTProvider
from nergal.stt.factory import create_stt_provider

__all__ = [
    "AudioTooLongError",
    "BaseSTTProvider",
    "STTError",
    "convert_ogg_to_wav",
    "create_stt_provider",
]
