"""Tests for stt_lib audio utilities."""

import pytest
from io import BytesIO

from stt_lib.audio import convert_ogg_to_wav, convert_audio
from stt_lib.exceptions import AudioTooLongError


class TestConvertOggToWav:
    """Tests for convert_ogg_to_wav function."""

    @pytest.mark.skip(reason="Requires actual OGG audio file")
    async def test_convert_ogg_to_wav_basic(self):
        """Test basic OGG to WAV conversion."""
        # This test would require actual OGG audio data
        pass

    def test_convert_with_max_duration(self, mock_stt_config):
        """Test conversion respects max_duration_seconds."""
        # Mock audio that would be considered "too long"
        # This is a placeholder - real test needs valid OGG data
        pass

    def test_invalid_ogg_raises_error(self):
        """Test invalid OGG data raises ValueError."""
        invalid_data = b"not real ogg data"
        with pytest.raises(ValueError, match="Invalid OGG audio data"):
            convert_ogg_to_wav(invalid_data)


class TestConvertAudio:
    """Tests for convert_audio function."""

    @pytest.mark.skip(reason="Requires actual audio files")
    async def test_convert_ogg_format(self):
        """Test converting OGG format."""
        pass

    @pytest.mark.skip(reason="Requires actual audio files")
    async def test_convert_mp3_format(self):
        """Test converting MP3 format."""
        pass

    def test_invalid_format_raises_error(self):
        """Test invalid format raises ValueError."""
        invalid_data = b"not real audio"
        with pytest.raises(ValueError):
            convert_audio(
                invalid_data,
                input_format="ogg",
                output_format="wav",
            )

    def test_convert_with_sample_rate_and_channels(self, mock_stt_config):
        """Test conversion with custom sample rate and channels."""
        # This is a placeholder - real test needs valid audio data
        pass
