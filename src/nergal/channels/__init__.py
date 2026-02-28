"""Channel system for messaging platform abstraction.

This package provides an abstraction layer for messaging platforms,
allowing the agent to work with Telegram, Slack, etc.
"""

from nergal.channels.base import Channel, ChannelMessage, SendMessage
from nergal.channels.factory import create_channel
from nergal.channels.telegram import TelegramChannel, TelegramMessageAdapter

__all__ = [
    "create_channel",
    "Channel",
    "ChannelMessage",
    "SendMessage",
    "TelegramChannel",
    "TelegramMessageAdapter",
]
