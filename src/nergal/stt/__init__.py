"""Speech-to-Text module for voice message transcription."""

from nergal.stt.audio_utils import AudioTooLongError, convert_ogg_to_wav
from nergal.stt.base import BaseSTTProvider
from nergal.stt.factory import create_stt_provider

__all__ = [
    "BaseSTTProvider",
    "create_stt_provider",
    "convert_ogg_to_wav",
    "AudioTooLongError",
]
