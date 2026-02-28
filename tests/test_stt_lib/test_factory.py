"""Tests for stt_lib factory."""

import pytest
from stt_lib import create_stt_provider, LocalWhisperProvider
from stt_lib.config import STTConfig


class TestCreateSTTProvider:
    """Tests for create_stt_provider factory function."""

    def test_create_local_provider_default_params(self):
        """Test creating local provider with default parameters."""
        provider = create_stt_provider()
        assert isinstance(provider, LocalWhisperProvider)
        assert provider.provider_name == "local_whisper"

    def test_create_local_provider_with_params(self):
        """Test creating local provider with custom parameters."""
        provider = create_stt_provider(
            provider_type="local",
            model="small",
            device="cpu",
            compute_type="int8",
            timeout=30.0,
        )
        assert isinstance(provider, LocalWhisperProvider)
        assert provider.provider_name == "local_whisper"

    def test_create_from_config(self):
        """Test creating provider from config object."""
        config = STTConfig(
            provider="local",
            model="small",
            device="cpu",
            timeout=45.0,
        )
        provider = create_stt_provider(config=config)
        assert isinstance(provider, LocalWhisperProvider)
        assert provider.provider_name == "local_whisper"

    def test_openai_provider_not_implemented(self):
        """Test openai provider raises ValueError."""
        with pytest.raises(ValueError, match="OpenAI Whisper API provider is not implemented"):
            create_stt_provider(provider_type="openai")

    def test_unsupported_provider_raises_error(self):
        """Test unsupported provider raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported STT provider"):
            create_stt_provider(provider_type="unsupported")

    def test_config_overrides_individual_params(self):
        """Test config takes precedence over individual parameters."""
        config = STTConfig(provider="local", model="small")
        # Config should override model param
        provider = create_stt_provider(config=config, model="tiny")
        # Should use config's model ("small") not the param ("tiny")
        assert isinstance(provider, LocalWhisperProvider)
