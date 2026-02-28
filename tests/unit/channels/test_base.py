"""Tests for channel base classes."""

import pytest
from datetime import datetime

from nergal.channels.base import Channel, ChannelMessage, SendMessage


class TestChannelMessage:
    """Tests for ChannelMessage dataclass."""

    def test_channel_message_creation(self):
        """Test creating a channel message."""
        msg = ChannelMessage(
            id="msg123",
            sender="user123",
            content="Hello, world!",
            channel="telegram",
        )

        assert msg.id == "msg123"
        assert msg.sender == "user123"
        assert msg.content == "Hello, world!"
        assert msg.channel == "telegram"
        assert msg.timestamp is None
        assert msg.metadata == {}

    def test_channel_message_with_timestamp(self):
        """Test channel message with timestamp."""
        timestamp = int(datetime.now().timestamp())
        msg = ChannelMessage(
            id="msg456",
            sender="user456",
            content="Test message",
            channel="slack",
            timestamp=timestamp,
        )

        assert msg.timestamp == timestamp

    def test_channel_message_with_metadata(self):
        """Test channel message with metadata."""
        msg = ChannelMessage(
            id="msg789",
            sender="user789",
            content="Message with metadata",
            channel="discord",
            metadata={"reply_to": "msg123", "language": "en"},
        )

        assert msg.metadata == {"reply_to": "msg123", "language": "en"}

    def test_channel_message_default_values(self):
        """Test default values for optional fields."""
        msg = ChannelMessage(
            id="msg000",
            sender="user000",
            content="Minimal message",
            channel="cli",
        )

        assert msg.timestamp is None
        assert msg.metadata == {}

    def test_channel_message_unicode(self):
        """Test channel message with unicode content."""
        msg = ChannelMessage(
            id="msg_uni",
            sender="user_uni",
            content="Hello 🌍 Привет мир",
            channel="telegram",
        )

        assert "🌍" in msg.content
        assert "Привет" in msg.content

    def test_channel_message_long_content(self):
        """Test channel message with long content."""
        long_content = "A" * 10000
        msg = ChannelMessage(
            id="msg_long",
            sender="user_long",
            content=long_content,
            channel="telegram",
        )

        assert len(msg.content) == 10000


class TestSendMessage:
    """Tests for SendMessage dataclass."""

    def test_send_message_creation(self):
        """Test creating a send message."""
        msg = SendMessage(
            content="Hello back!",
            recipient="user123",
        )

        assert msg.content == "Hello back!"
        assert msg.recipient == "user123"
        assert msg.reply_to is None
        assert msg.metadata is None

    def test_send_message_with_reply_to(self):
        """Test send message with reply_to."""
        msg = SendMessage(
            content="Reply to previous",
            recipient="user123",
            reply_to="msg456",
        )

        assert msg.reply_to == "msg456"

    def test_send_message_with_metadata(self):
        """Test send message with metadata."""
        msg = SendMessage(
            content="Message with metadata",
            recipient="user123",
            metadata={"format": "markdown", "silent": True},
        )

        assert msg.metadata == {"format": "markdown", "silent": True}

    def test_send_message_all_fields(self):
        """Test send message with all fields."""
        msg = SendMessage(
            content="Complete message",
            recipient="user789",
            reply_to="msg999",
            metadata={"parse_mode": "HTML", "disable_preview": True},
        )

        assert msg.content == "Complete message"
        assert msg.recipient == "user789"
        assert msg.reply_to == "msg999"
        assert msg.metadata == {"parse_mode": "HTML", "disable_preview": True}


class TestChannel:
    """Tests for Channel abstract class."""

    def test_channel_is_abstract(self):
        """Test that Channel is an abstract class."""
        with pytest.raises(TypeError):
            Channel()

    def test_channel_subclass_implementations(self):
        """Test that Channel subclass can be implemented."""

        class MockChannel(Channel):
            @property
            def name(self) -> str:
                return "mock_channel"

            async def send(self, message: SendMessage) -> None:
                pass

            async def listen(self, handler) -> None:
                pass

            async def request_approval(self, tool_name: str, arguments: dict) -> bool:
                return True

        channel = MockChannel()
        assert channel.name == "mock_channel"

    def test_channel_name_property(self):
        """Test name property."""

        class TestChannel(Channel):
            @property
            def name(self) -> str:
                return "test_channel"

            async def send(self, message: SendMessage) -> None:
                pass

            async def listen(self, handler) -> None:
                pass

            async def request_approval(self, tool_name: str, arguments: dict) -> bool:
                return False

        channel = TestChannel()
        assert channel.name == "test_channel"

    def test_channel_abstract_methods_required(self):
        """Test that all abstract methods must be implemented."""

        class IncompleteChannel(Channel):
            @property
            def name(self) -> str:
                return "incomplete"

            # Missing send, listen, request_approval

        with pytest.raises(TypeError):
            IncompleteChannel()
