"""Channel factory for creating channel instances.

This module provides a factory function for creating
the appropriate channel based on configuration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nergal.channels.base import Channel

if TYPE_CHECKING:
    from telegram.ext import Application

logger = logging.getLogger(__name__)


def create_channel(
    application: "Application | None" = None,
    bot_token: str | None = None,
    use_polling: bool = True,
) -> Channel:
    """Create the appropriate channel instance.

    Currently only Telegram is implemented. Other channels
    (Slack, Discord, etc.) can be added in the future.

    Args:
        application: Telegram Application instance.
        bot_token: Telegram bot token.
        use_polling: Whether to use polling (True) or webhooks (False).

    Returns:
        Channel instance.

    Example:
        >>> from nergal.channels.factory import create_channel
        >>> channel = create_channel(
        ...     application=app,
        ...     bot_token="TOKEN",
        ...     use_polling=True
        ... )
    """
    if not bot_token:
        from nergal.config import get_settings

        settings = get_settings()
        bot_token = settings.telegram_bot_token

    # Create Telegram channel
    from nergal.channels.telegram import TelegramChannel

    if application is None:
        from telegram.ext import Application

        application = Application.builder().token(bot_token).build()

    return TelegramChannel(
        application=application,
        bot_token=bot_token,
        use_polling=use_polling,
    )
