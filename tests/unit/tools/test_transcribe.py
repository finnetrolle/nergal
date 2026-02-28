"""Tests for TranscribeTool."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from nergal.tools.base import ToolResult
from nergal.tools.stt.transcribe import TranscribeTool
from nergal.tools.exceptions import ToolValidationError, ToolExecutionError


@pytest.fixture
def mock_stt_provider():
    """Create a mock STT provider."""
    provider = MagicMock()
    provider.provider_name = "test_stt"
    provider.transcribe = AsyncMock(return_value="Test transcription")
    return provider


@pytest.fixture
def transcribe_tool(mock_stt_provider):
    """Create a TranscribeTool instance for testing."""
    return TranscribeTool(
        stt_provider=mock_stt_provider,
        default_language="ru",
    )


class TestTranscribeTool:
    """Tests for TranscribeTool class."""

    def test_name(self, transcribe_tool):
        """Test that tool name is 'transcribe_audio'."""
        assert transcribe_tool.name == "transcribe_audio"

    def test_description(self, transcribe_tool):
        """Test that tool description is correct."""
        assert "speech-to-text" in transcribe_tool.description.lower()

    def test_parameters_schema(self, transcribe_tool):
        """Test that parameters schema is correct."""
        schema = transcribe_tool.parameters_schema
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "audio_bytes" in schema["properties"]
        assert "language" in schema["properties"]
        assert "required" in schema
        assert "audio_bytes" in schema["required"]

    @pytest.mark.asyncio
    async def test_execute_success(self, transcribe_tool, mock_stt_provider):
        """Test successful transcription."""
        # Arrange
        import base64

        audio_data = b"fake audio data"
        encoded_audio = base64.b64encode(audio_data).decode()

        args = {
            "audio_bytes": encoded_audio,
            "language": "ru",
        }

        # Act
        result = await transcribe_tool.execute(args)

        # Assert
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.output == "Test transcription"
        assert result.metadata["provider"] == "test_stt"
        assert result.metadata["language"] == "ru"
        mock_stt_provider.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_default_language(self, transcribe_tool, mock_stt_provider):
        """Test transcription with default language."""
        # Arrange
        import base64

        audio_data = b"fake audio data"
        encoded_audio = base64.b64encode(audio_data).decode()

        args = {"audio_bytes": encoded_audio}

        # Act
        result = await transcribe_tool.execute(args)

        # Assert
        assert result.success is True
        assert result.metadata["language"] == "ru"

    @pytest.mark.asyncio
    async def test_execute_missing_audio_bytes(self, transcribe_tool, mock_stt_provider):
        """Test execution without audio_bytes."""
        # Arrange
        args = {"language": "ru"}

        # Act & Assert
        with pytest.raises(ToolValidationError) as exc_info:
            await transcribe_tool.execute(args)

        assert "Audio bytes are required" in str(exc_info.value)
        mock_stt_provider.transcribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_empty_audio_bytes(self, transcribe_tool, mock_stt_provider):
        """Test execution with empty audio_bytes."""
        # Arrange
        args = {"audio_bytes": ""}

        # Act & Assert
        with pytest.raises(ToolValidationError) as exc_info:
            await transcribe_tool.execute(args)

        assert "Audio bytes are required" in str(exc_info.value)
        mock_stt_provider.transcribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_invalid_base64(self, transcribe_tool, mock_stt_provider):
        """Test execution with invalid base64 data."""
        # Arrange
        args = {"audio_bytes": "not valid base64!!!"}

        # Act & Assert
        with pytest.raises(ToolValidationError) as exc_info:
            await transcribe_tool.execute(args)

        assert "Failed to decode base64 audio" in str(exc_info.value)
        mock_stt_provider.transcribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_stt_error(self, transcribe_tool, mock_stt_provider):
        """Test handling of STT provider error."""
        # Arrange
        import base64

        import stt_lib.exceptions as stt_exceptions

        audio_data = b"fake audio data"
        encoded_audio = base64.b64encode(audio_data).decode()

        mock_stt_provider.transcribe = AsyncMock(side_effect=stt_exceptions.STTError("STT failed"))

        args = {"audio_bytes": encoded_audio}

        # Act & Assert
        with pytest.raises(ToolExecutionError) as exc_info:
            await transcribe_tool.execute(args)

        assert "STT error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self, transcribe_tool, mock_stt_provider):
        """Test handling of unexpected error."""
        # Arrange
        import base64

        audio_data = b"fake audio data"
        encoded_audio = base64.b64encode(audio_data).decode()

        mock_stt_provider.transcribe = AsyncMock(side_effect=RuntimeError("Oops"))

        args = {"audio_bytes": encoded_audio}

        # Act & Assert
        with pytest.raises(ToolExecutionError) as exc_info:
            await transcribe_tool.execute(args)

        assert "Unexpected error during transcription" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_empty_transcription(self, transcribe_tool, mock_stt_provider):
        """Test handling of empty transcription result."""
        # Arrange
        import base64

        audio_data = b"fake audio data"
        encoded_audio = base64.b64encode(audio_data).decode()

        mock_stt_provider.transcribe = AsyncMock(return_value="   ")

        args = {"audio_bytes": encoded_audio}

        # Act
        result = await transcribe_tool.execute(args)

        # Assert
        assert result.success is False
        assert result.error == "Transcription returned empty result"
        assert result.output == ""

    @pytest.mark.asyncio
    async def test_execute_none_transcription(self, transcribe_tool, mock_stt_provider):
        """Test handling of None transcription result."""
        # Arrange
        import base64

        audio_data = b"fake audio data"
        encoded_audio = base64.b64encode(audio_data).decode()

        mock_stt_provider.transcribe = AsyncMock(return_value=None)

        args = {"audio_bytes": encoded_audio}

        # Act
        result = await transcribe_tool.execute(args)

        # Assert
        assert result.success is False
        assert result.error == "Transcription returned empty result"

    @pytest.mark.asyncio
    async def test_execute_with_whitespace_language(self, transcribe_tool, mock_stt_provider):
        """Test that whitespace-only language falls back to default."""
        # Arrange
        import base64

        audio_data = b"fake audio data"
        encoded_audio = base64.b64encode(audio_data).decode()

        args = {
            "audio_bytes": encoded_audio,
            "language": "   ",
        }

        # Act
        result = await transcribe_tool.execute(args)

        # Assert
        assert result.success is True
        assert result.metadata["language"] == "ru"

    @pytest.mark.asyncio
    async def test_execute_with_bytes_audio(self, transcribe_tool, mock_stt_provider):
        """Test execution with bytes (not base64 string) audio."""
        # Arrange
        audio_data = b"fake audio data"

        args = {
            "audio_bytes": audio_data,
            "language": "en",
        }

        # Act
        result = await transcribe_tool.execute(args)

        # Assert
        assert result.success is True
        assert result.metadata["language"] == "en"
