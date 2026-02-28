"""Tests for TelegramChannel."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nergal.channels.base import ChannelMessage, SendMessage
from nergal.channels.telegram import TelegramChannel, TelegramMessageAdapter


@pytest.fixture
def mock_telegram_app():
    """Create a mock Telegram Application."""
    app = MagicMock()
    app.bot = MagicMock()
    app.updater = MagicMock()
    app.add_handler = MagicMock()
    return app


@pytest.fixture
def telegram_channel(mock_telegram_app):
    """Create a TelegramChannel instance for testing."""
    return TelegramChannel(
        application=mock_telegram_app,
        bot_token="test_token",
        use_polling=True,
    )


class TestTelegramChannel:
    """Tests for TelegramChannel class."""

    def test_name(self, telegram_channel):
        """Test that channel name is 'telegram'."""
        assert telegram_channel.name == "telegram"

    @pytest.mark.asyncio
    async def test_send_message(self, telegram_channel, mock_telegram_app):
        """Test sending a message through Telegram."""
        # Arrange
        message = SendMessage(
            content="Test message",
            recipient="123456",
            reply_to="789",
        )

        mock_telegram_app.bot.send_message = AsyncMock()

        # Act
        await telegram_channel.send(message)

        # Assert
        mock_telegram_app.bot.send_message.assert_called_once_with(
            chat_id=123456,
            text="Test message",
            parse_mode="HTML",
            reply_to_message_id=789,
            disable_web_page_preview=False,
        )

    @pytest.mark.asyncio
    async def test_send_message_with_metadata(self, telegram_channel, mock_telegram_app):
        """Test sending a message with metadata."""
        # Arrange
        message = SendMessage(
            content="Test message",
            recipient="123456",
            metadata={"disable_preview": True},
        )

        mock_telegram_app.bot.send_message = AsyncMock()

        # Act
        await telegram_channel.send(message)

        # Assert
        mock_telegram_app.bot.send_message.assert_called_once_with(
            chat_id=123456,
            text="Test message",
            parse_mode="HTML",
            reply_to_message_id=None,
            disable_web_page_preview=True,
        )

    @pytest.mark.asyncio
    async def test_send_message_invalid_recipient(self, telegram_channel, mock_telegram_app):
        """Test sending message with invalid recipient ID."""
        # Arrange
        message = SendMessage(
            content="Test message",
            recipient="invalid",
        )

        mock_telegram_app.bot.send_message = AsyncMock()

        # Act
        await telegram_channel.send(message)

        # Assert
        mock_telegram_app.bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_failure(self, telegram_channel, mock_telegram_app):
        """Test handling of send message failure."""
        # Arrange
        message = SendMessage(
            content="Test message",
            recipient="123456",
        )

        mock_telegram_app.bot.send_message = AsyncMock(side_effect=Exception("API Error"))

        # Act & Assert
        with pytest.raises(Exception, match="API Error"):
            await telegram_channel.send(message)

    @pytest.mark.asyncio
    async def test_stop(self, telegram_channel, mock_telegram_app):
        """Test stopping the Telegram channel."""
        # Arrange
        mock_telegram_app.updater.stop = AsyncMock()
        mock_telegram_app.stop = AsyncMock()
        mock_telegram_app.shutdown = AsyncMock()

        # Act
        await telegram_channel.stop()

        # Assert
        mock_telegram_app.updater.stop.assert_called_once()
        mock_telegram_app.stop.assert_called_once()
        mock_telegram_app.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_without_updater(self, telegram_channel, mock_telegram_app):
        """Test stopping the channel when updater is None."""
        # Arrange
        telegram_channel._use_polling = False
        telegram_channel._application.updater = None
        mock_telegram_app.stop = AsyncMock()
        mock_telegram_app.shutdown = AsyncMock()

        # Act
        await telegram_channel.stop()

        # Assert
        mock_telegram_app.stop.assert_called_once()
        mock_telegram_app.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen(self, telegram_channel, mock_telegram_app):
        """Test listening for messages."""
        # Arrange
        handler_called = []

        def test_handler(message: ChannelMessage):
            handler_called.append(message)

        # Mock the async methods
        mock_telegram_app.initialize = AsyncMock()
        mock_telegram_app.start = AsyncMock()
        mock_telegram_app.updater.start_polling = AsyncMock()

        # Act
        with patch("telegram.ext.MessageHandler") as mock_handler_class:
            await telegram_channel.listen(test_handler)
            # Verify handler was added to application
            mock_telegram_app.add_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_approval(self, telegram_channel):
        """Test the approval request method (currently returns True)."""
        # Act
        result = await telegram_channel.request_approval(
            tool_name="web_search",
            arguments={"query": "test"},
        )

        # Assert
        # Currently returns True by default (placeholder implementation)
        assert result is True


class TestTelegramMessageAdapter:
    """Tests for TelegramMessageAdapter class."""

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram Update."""
        update = MagicMock()
        update.message = MagicMock()
        update.message.message_id = 123
        update.message.text = "Test message"
        update.message.date = MagicMock()
        update.message.date.timestamp = MagicMock(return_value=1234567890)
        update.message.chat.id = 987654321
        update.message.chat.type = "private"
        update.message.reply_to_message = None
        update.effective_user = MagicMock()
        update.effective_user.id = 111222
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"
        update.effective_user.language_code = "en"
        return update

    @pytest.fixture
    def adapter(self, telegram_channel):
        """Create a TelegramMessageAdapter instance."""
        return TelegramMessageAdapter(telegram_channel)

    def test_update_to_channel_message(self, adapter, mock_update):
        """Test converting Update to ChannelMessage."""
        # Act
        result = adapter.update_to_channel_message(mock_update)

        # Assert
        assert isinstance(result, ChannelMessage)
        assert result.id == "123"
        assert result.sender == "111222"
        assert result.content == "Test message"
        assert result.channel == "telegram"
        assert result.timestamp == 1234567890
        assert result.metadata["chat_id"] == "987654321"
        assert result.metadata["chat_type"] == "private"
        assert result.metadata["username"] == "testuser"

    def test_update_to_channel_message_no_message(self, adapter):
        """Test converting Update without message."""
        # Arrange
        mock_update = MagicMock()
        mock_update.message = None

        # Act
        result = adapter.update_to_channel_message(mock_update)

        # Assert
        assert result is None

    def test_update_to_channel_message_no_user(self, adapter):
        """Test converting Update without user."""
        # Arrange
        mock_update = MagicMock()
        mock_update.message = MagicMock()
        mock_update.effective_user = None

        # Act
        result = adapter.update_to_channel_message(mock_update)

        # Assert
        assert result is None

    def test_update_to_channel_message_with_reply(self, adapter, mock_update):
        """Test converting Update with reply_to_message."""
        # Arrange
        mock_update.message.reply_to_message = MagicMock()
        mock_update.message.reply_to_message.message_id = 999

        # Act
        result = adapter.update_to_channel_message(mock_update)

        # Assert
        assert result.metadata["reply_to_message_id"] == "999"

    def test_send_message_to_telegram(self, adapter):
        """Test preparing SendMessage for Telegram."""
        # Arrange
        send_message = SendMessage(
            content="Test",
            recipient="",
        )

        # Act
        adapter.send_message_to_telegram(send_message, chat_id=123456)

        # Assert
        assert send_message.recipient == "123456"
