"""Tests for stt_lib exceptions."""

import pytest

from stt_lib.exceptions import (
    STTError,
    STTConnectionError,
    STTUnsupportedFormatError,
    AudioTooLongError,
)


class TestSTTError:
    """Tests for STTError base class."""

    def test_init_with_message(self):
        """Test STTError initialization with message."""
        error = STTError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.cause is None

    def test_init_with_cause(self):
        """Test STTError initialization with cause."""
        cause = ValueError("Original error")
        error = STTError("Test error message", cause=cause)
        assert str(error) == "Test error message (caused by: Original error)"
        assert error.cause is cause


class TestSTTConnectionError:
    """Tests for STTConnectionError."""

    def test_init(self):
        """Test STTConnectionError initialization."""
        error = STTConnectionError("Connection failed")
        assert isinstance(error, STTError)
        assert str(error) == "Connection failed"


class TestSTTUnsupportedFormatError:
    """Tests for STTUnsupportedFormatError."""

    def test_init_without_format(self):
        """Test STTUnsupportedFormatError without format."""
        error = STTUnsupportedFormatError("Unsupported format")
        assert str(error) == "Unsupported format"
        assert error.format is None

    def test_init_with_format(self):
        """Test STTUnsupportedFormatError with format."""
        error = STTUnsupportedFormatError("Unsupported format", format="mp3")
        assert str(error) == "Unsupported format: mp3"
        assert error.format == "mp3"


class TestAudioTooLongError:
    """Tests for AudioTooLongError."""

    def test_init(self):
        """Test AudioTooLongError initialization."""
        error = AudioTooLongError(90.5, 60)
        assert isinstance(error, STTError)
        assert error.duration_seconds == 90.5
        assert error.max_seconds == 60
        assert "90.5s" in str(error)
        assert "60s" in str(error)

    def test_message_format(self):
        """Test AudioTooLongError message format."""
        error = AudioTooLongError(45.7, 30)
        expected = "Audio duration (45.7s) exceeds maximum allowed (30s)"
        assert str(error) == expected
