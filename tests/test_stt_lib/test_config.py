"""Tests for stt_lib config."""

import pytest

from stt_lib.config import STTConfig


class TestSTTConfig:
    """Tests for STTConfig class."""

    def test_default_values(self):
        """Test STTConfig has correct default values."""
        config = STTConfig()
        assert config.provider == "local"
        assert config.model == "base"
        assert config.device == "cpu"
        assert config.compute_type == "int8"
        assert config.api_key == ""
        assert config.timeout == 60.0
        assert config.max_duration == 60

    def test_custom_values(self):
        """Test STTConfig accepts custom values."""
        config = STTConfig(
            provider="openai",
            model="large-v3",
            device="cuda",
            compute_type="float16",
            api_key="test-key",
            timeout=120.0,
            max_duration=120,
        )
        assert config.provider == "openai"
        assert config.model == "large-v3"
        assert config.device == "cuda"
        assert config.compute_type == "float16"
        assert config.api_key == "test-key"
        assert config.timeout == 120.0
        assert config.max_duration == 120

    def test_from_environment_variables(self, monkeypatch):
        """Test STTConfig loads from environment variables."""
        monkeypatch.setenv("STT_PROVIDER", "openai")
        monkeypatch.setenv("STT_MODEL", "small")
        config = STTConfig()
        assert config.provider == "openai"
        assert config.model == "small"
