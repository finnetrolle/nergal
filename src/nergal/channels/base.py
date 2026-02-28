"""Base classes and interfaces for Channel system.

This module provides the core abstractions for the channel system,
including the Channel interface and message dataclasses.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ChannelMessage:
    """Message received from channel.

    Represents a message received from a messaging platform.

    Attributes:
        id: Unique message identifier.
        sender: The user who sent the message.
        content: The message content.
        channel: The channel name.
        timestamp: Message timestamp.
        metadata: Additional metadata.
    """

    id: str
    """Unique message identifier."""

    sender: str
    """The user who sent the message."""

    content: str
    """The message content."""

    channel: str
    """The channel name."""

    timestamp: int | None = field(default=None)
    """Message timestamp (Unix timestamp)."""

    metadata: dict = field(default_factory=dict)
    """Additional metadata."""


@dataclass
class SendMessage:
    """Message to send via channel.

    Represents a message to be sent through a channel.

    Attributes:
        content: The message content.
        recipient: The recipient identifier.
        reply_to: Optional message ID to reply to.
        metadata: Optional additional metadata.
    """

    content: str
    """The message content."""

    recipient: str
    """The recipient identifier."""

    reply_to: str | None = field(default=None)
    """Optional message ID to reply to."""

    metadata: dict | None = field(default=None)
    """Optional additional metadata."""


class Channel(ABC):
    """Abstraction for messaging platforms.

    Channels provide a unified interface for different messaging
    platforms (Telegram, Slack, CLI, etc.).

    Example:
        >>> from nergal.channels.base import Channel
        >>>
        >>> class MyChannel(Channel):
        ...     async def send(self, message: SendMessage) -> None:
        ...         # Send message
        ...         pass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel name.

        Returns:
            Channel name identifier.
        """
        pass

    @abstractmethod
    async def send(
        self,
        message: SendMessage,
    ) -> None:
        """Send a message.

        Args:
            message: The message to send.
        """
        pass

    @abstractmethod
    async def listen(
        self,
        handler: Callable[[ChannelMessage], None],
    ) -> None:
        """Listen for incoming messages.

        Args:
            handler: Callback for incoming messages.
        """
        pass

    @abstractmethod
    async def request_approval(
        self,
        tool_name: str,
        arguments: dict,
    ) -> bool:
        """Request approval from user.

        Args:
            tool_name: The tool being called.
            arguments: The tool arguments.

        Returns:
            True if approved, False otherwise.

        Note:
            This is a no-op base implementation. Channel
            implementations should override for actual approval UI.
        """
        pass
