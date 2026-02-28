"""Channel system for messaging platform abstraction.

This package provides an abstraction layer for messaging platforms,
allowing the agent to work with Telegram, Slack, etc.
"""

from nergal.channels.factory import create_channel

__all__ = ["create_channel"]
