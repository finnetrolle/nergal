"""Telegram channel implementation for Nergal.

This module provides the TelegramChannel class which implements
the Channel interface for the Telegram messaging platform.

Example:
    >>> from nergal.channels.telegram import TelegramChannel
    >>> from telegram.ext import Application
    >>>
    >>> # Create application
    >>> app = Application.builder().token("TOKEN").build()
    >>>
    >>> # Create channel
    >>> channel = TelegramChannel(
    ...     application=app,
    ...     bot_token="TOKEN",
    ...     use_polling=True
    ... )
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nergal.channels.base import Channel, ChannelMessage, SendMessage

if TYPE_CHECKING:
    from collections.abc import Callable

    from telegram import Update

logger = logging.getLogger(__name__)


class TelegramChannel(Channel):
    """Telegram implementation of the Channel interface.

    This channel handles message sending, receiving, and approval
    requests through the Telegram platform.

    Args:
        application: Telegram Application instance.
        bot_token: Telegram bot token.
        use_polling: Whether to use polling (True) or webhooks (False).
    """

    def __init__(
        self,
        application,
        bot_token: str,
        use_polling: bool = True,
    ) -> None:
        """Initialize the Telegram channel.

        Args:
            application: Telegram Application instance.
            bot_token: Telegram bot token.
            use_polling: Whether to use polling or webhooks.
        """
        self._application = application
        self._bot_token = bot_token
        self._use_polling = use_polling
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Return the channel name."""
        return "telegram"

    async def send(self, message: SendMessage) -> None:
        """Send a message through Telegram.

        Args:
            message: The message to send.
        """
        try:
            # Get bot from application
            bot = self._application.bot

            # Parse recipient
            try:
                chat_id = int(message.recipient)
            except (ValueError, TypeError):
                self._logger.warning(f"Invalid recipient ID: {message.recipient}, skipping send")
                return

            # Prepare reply_to_message_id
            reply_to_message_id = None
            if message.reply_to:
                try:
                    reply_to_message_id = int(message.reply_to)
                except (ValueError, TypeError):
                    pass

            # Send message
            await bot.send_message(
                chat_id=chat_id,
                text=message.content,
                parse_mode="HTML",
                reply_to_message_id=reply_to_message_id,
                disable_web_page_preview=message.metadata.get("disable_preview", False)
                if message.metadata
                else False,
            )

            self._logger.debug(f"Message sent to chat {chat_id}: {message.content[:50]}...")

        except Exception as e:
            self._logger.error(f"Failed to send message: {e}", exc_info=True)
            raise

    async def listen(
        self,
        handler: Callable[[ChannelMessage], None],
    ) -> None:
        """Listen for incoming messages from Telegram.

        This method starts the Telegram bot and registers
        a message handler that converts Update objects to
        ChannelMessage and passes them to the provided handler.

        Args:
            handler: Callback for incoming ChannelMessage objects.
        """
        self._logger.info("Starting Telegram channel listener...")

        # Define the update handler
        async def _update_handler(update: Update, context) -> None:
            """Handle Telegram update and convert to ChannelMessage."""
            if not update.message or not update.message.text:
                return

            # Get user information
            user = update.effective_user
            if not user:
                return

            # Create ChannelMessage
            channel_message = ChannelMessage(
                id=str(update.message.message_id),
                sender=str(user.id),
                content=update.message.text,
                channel=self.name,
                timestamp=update.message.date.timestamp() if update.message.date else None,
                metadata={
                    "chat_id": str(update.message.chat.id),
                    "chat_type": update.message.chat.type,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "language_code": user.language_code,
                    "reply_to_message_id": (
                        str(update.message.reply_to_message.message_id)
                        if update.message.reply_to_message
                        else None
                    ),
                },
            )

            # Call the handler
            try:
                handler(channel_message)
            except Exception as e:
                self._logger.error(
                    f"Handler failed for message {channel_message.id}: {e}",
                    exc_info=True,
                )

        # Register message handler with the application
        from telegram.ext import MessageHandler, filters

        self._application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, _update_handler)
        )

        # Start the application
        if self._use_polling:
            self._logger.info("Starting with polling mode")
            await self._application.initialize()
            await self._application.start()
            await self._application.updater.start_polling(
                allowed_updates=None, drop_pending_updates=True
            )
        else:
            # Webhook mode
            self._logger.info("Starting with webhook mode")
            await self._application.initialize()
            await self._application.start()

    async def stop(self) -> None:
        """Stop the Telegram channel listener.

        This method cleanly shuts down the Telegram application.
        """
        self._logger.info("Stopping Telegram channel...")

        try:
            if self._use_polling and self._application.updater:
                await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()
            self._logger.info("Telegram channel stopped successfully")
        except Exception as e:
            self._logger.error(f"Error stopping Telegram channel: {e}", exc_info=True)

    async def request_approval(
        self,
        tool_name: str,
        arguments: dict,
    ) -> bool:
        """Request approval from user for tool execution.

        This is currently a no-op implementation. A full implementation
        would send an inline keyboard with approve/reject buttons
        and wait for the user's response.

        Args:
            tool_name: The tool being called.
            arguments: The tool arguments.

        Returns:
            True if approved, False otherwise.

        Note:
            This is a placeholder. A full implementation requires:
            - Tracking pending approvals
            - Sending inline keyboards
            - Handling callback queries
            - Timeout handling
        """
        self._logger.debug(f"Approval requested for tool '{tool_name}' with args: {arguments}")
        # TODO: Implement full approval UI with inline keyboards
        return True


class TelegramMessageAdapter:
    """Adapter for converting between Telegram Update and ChannelMessage.

    This utility class provides methods for converting Telegram-specific
    objects to/from the generic ChannelMessage format.

    Args:
        channel: The TelegramChannel instance.
    """

    def __init__(self, channel: TelegramChannel) -> None:
        """Initialize the adapter.

        Args:
            channel: The TelegramChannel instance.
        """
        self._channel = channel

    def update_to_channel_message(self, update: Update) -> ChannelMessage | None:
        """Convert a Telegram Update to a ChannelMessage.

        Args:
            update: Telegram Update object.

        Returns:
            ChannelMessage or None if conversion fails.
        """
        if not update.message:
            return None

        message = update.message
        user = update.effective_user

        if not user:
            return None

        # Extract content (text or voice transcription)
        content = ""
        if message.text:
            content = message.text
        elif message.caption:
            content = message.caption
        else:
            # For voice messages, transcription should be provided
            # before calling this method
            return None

        return ChannelMessage(
            id=str(message.message_id),
            sender=str(user.id),
            content=content,
            channel=self._channel.name,
            timestamp=message.date.timestamp() if message.date else None,
            metadata={
                "chat_id": str(message.chat.id),
                "chat_type": message.chat.type,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language_code": user.language_code,
                "reply_to_message_id": (
                    str(message.reply_to_message.message_id) if message.reply_to_message else None
                ),
                "update": update,  # Store original update for full access
            },
        )

    def send_message_to_telegram(
        self,
        send_message: SendMessage,
        chat_id: int,
    ) -> None:
        """Prepare SendMessage for Telegram bot.

        This method prepares a SendMessage for sending through
        the Telegram bot API.

        Args:
            send_message: The SendMessage object.
            chat_id: The Telegram chat ID to send to.

        Returns:
            None (message is prepared but not sent)
        """
        # Update recipient with chat_id
        send_message.recipient = str(chat_id)
        # Actual sending is done by TelegramChannel.send()
