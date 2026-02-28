"""Pytest fixtures for stt_lib tests."""

import pytest
from io import BytesIO
from unittest.mock import Mock, patch


@pytest.fixture
def mock_stt_config():
    """Create a mock STTConfig for testing."""
    from stt_lib import STTConfig
    return STTConfig(
        provider="local",
        model="base",
        device="cpu",
        compute_type="int8",
        timeout=60.0,
        max_duration=60,
    )


@pytest.fixture
def mock_audio_data():
    """Create mock audio data for testing."""
    return b"fake audio data"


@pytest.fixture
def mock_wav_audio():
    """Create mock WAV audio data for testing."""
    # Create minimal WAV header (44 bytes) + silence
    return BytesIO(
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x44\xAC\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00"
        b"data\x00\x00\x00\x00" + b"\x00" * 1000
    )


@pytest.fixture
def sample_ogg_data():
    """Create sample OGG data for testing."""
    return b"OggS" + b"\x00" * 100
