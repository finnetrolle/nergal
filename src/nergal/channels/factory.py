"""Channel factory for creating channel instances.

This module provides a factory function for creating
the appropriate channel based on configuration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nergal.channels.base import Channel

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def create_channel() -> Channel:
    """Create the appropriate channel instance.

    Currently only Telegram is implemented. Other channels
    (Slack, Discord, etc.) can be added in the future.

    Returns:
        Channel instance.

    Example:
        >>> from nergal.channels.factory import create_channel
        >>> channel = create_channel()
    """
    # For now, always return Telegram channel
    # In the future, this can be based on configuration
    from telegram_handlers_lib.base import TelegramHandlerService

    # We'll use the existing handler service as the channel
    # This is a thin wrapper for now
    return TelegramHandlerService  # type: ignore
