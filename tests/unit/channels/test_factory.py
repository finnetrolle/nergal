"""Tests for channel factory."""

import pytest


class TestCreateChannel:
    """Tests for create_channel function."""

    def test_create_channel_requires_telegram_lib(self):
        """Test that create_channel requires telegram_handlers_lib."""
        # The factory requires telegram_handlers_lib which is an external dependency
        # This test documents that requirement
        pytest.importorskip("telegram_handlers_lib")

        from nergal.channels.factory import create_channel

        # If import succeeds, just verify the function is callable
        assert callable(create_channel)
