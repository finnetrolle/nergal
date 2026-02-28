"""Tests for stt_lib base provider."""

import pytest
from stt_lib.base import BaseSTTProvider


class DummySTTProvider(BaseSTTProvider):
    """Dummy provider for testing."""

    @property
    def provider_name(self) -> str:
        return "dummy"

    async def transcribe(self, audio_data, language="ru") -> str:
        return "dummy transcription"


class TestBaseSTTProvider:
    """Tests for BaseSTTProvider."""

    def test_provider_name_is_abstract(self):
        """Test provider_name is abstract."""
        with pytest.raises(TypeError):
            BaseSTTProvider()

    def test_preload_model_default_implementation(self):
        """Test preload_model has default implementation."""
        provider = DummySTTProvider()
        # Should not raise an error
        provider.preload_model()

    def test_dummy_provider_name(self):
        """Test dummy provider returns correct name."""
        provider = DummySTTProvider()
        assert provider.provider_name == "dummy"

    @pytest.mark.asyncio
    async def test_dummy_provider_transcribe(self):
        """Test dummy provider transcribes correctly."""
        provider = DummySTTProvider()
        result = await provider.transcribe(b"test audio", language="ru")
        assert result == "dummy transcription"
