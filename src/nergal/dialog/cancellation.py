"""Cancellation support for agent execution.

This module provides cancellation tokens and related exceptions
for managing graceful cancellation of agent execution.
"""

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class AgentCancelledError(Exception):
    """Exception raised when an agent operation is cancelled.

    Note: Named AgentCancelledError to avoid shadowing asyncio.CancelledError.
    """

    def __init__(self, message: str = "Operation was cancelled") -> None:
        """Initialize the error.

        Args:
            message: Cancellation message.
        """
        super().__init__(message)
        self.message = message


class AgentTimeoutError(Exception):
    """Exception raised when an agent operation times out.

    Note: Named AgentTimeoutError to avoid shadowing the built-in TimeoutError.
    """

    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: float | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            message: Timeout message.
            timeout_seconds: The timeout duration that was exceeded.
        """
        super().__init__(message)
        self.message = message
        self.timeout_seconds = timeout_seconds


@dataclass
class CancellationToken:
    """Token for propagating cancellation requests.

    This class provides a thread-safe mechanism for requesting and
    checking cancellation of async operations.

    Attributes:
        _cancelled: Internal flag indicating cancellation status.
        _cancel_reason: Optional reason for cancellation.
        _cancelled_at: Timestamp when cancellation was requested.
        _lock: Thread lock for safe concurrent access.
    """

    _cancelled: bool = field(default=False, init=False)
    _cancel_reason: str | None = field(default=None, init=False)
    _cancelled_at: datetime | None = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested.

        Returns:
            True if cancellation was requested, False otherwise.
        """
        with self._lock:
            return self._cancelled

    @property
    def cancel_reason(self) -> str | None:
        """Get the reason for cancellation, if any.

        Returns:
            Cancellation reason or None.
        """
        with self._lock:
            return self._cancel_reason

    @property
    def cancelled_at(self) -> datetime | None:
        """Get the timestamp when cancellation was requested.

        Returns:
            Cancellation timestamp or None.
        """
        with self._lock:
            return self._cancelled_at

    def cancel(self, reason: str | None = None) -> None:
        """Request cancellation.

        Args:
            reason: Optional reason for cancellation.
        """
        with self._lock:
            if not self._cancelled:
                self._cancelled = True
                self._cancel_reason = reason
                self._cancelled_at = datetime.now(UTC)

    def check_cancelled(self) -> None:
        """Check if cancelled and raise AgentCancelledError if so.

        Raises:
            AgentCancelledError: If cancellation was requested.
        """
        with self._lock:
            if self._cancelled:
                message = self._cancel_reason or "Operation was cancelled"
                raise AgentCancelledError(message)

    def reset(self) -> None:
        """Reset the cancellation state.

        This is useful for reusing tokens between operations.
        """
        with self._lock:
            self._cancelled = False
            self._cancel_reason = None
            self._cancelled_at = None

    def __repr__(self) -> str:
        """Get string representation of the token."""
        status = "cancelled" if self._cancelled else "active"
        reason = f", reason={self._cancel_reason!r}" if self._cancel_reason else ""
        return f"CancellationToken({status}{reason})"


class CancellationTokenSource:
    """Source for creating and managing cancellation tokens.

    This class provides a way to create linked cancellation tokens
    and cancel them all at once.

    Example:
        ```python
        source = CancellationTokenSource()
        token = source.token

        # Later, cancel all operations using this source
        source.cancel("User requested")
        ```
    """

    def __init__(self) -> None:
        """Initialize the cancellation token source."""
        self._token = CancellationToken()
        self._linked_tokens: list[CancellationToken] = []

    @property
    def token(self) -> CancellationToken:
        """Get the main cancellation token.

        Returns:
            The primary cancellation token.
        """
        return self._token

    @property
    def is_cancelled(self) -> bool:
        """Check if the source has been cancelled.

        Returns:
            True if cancelled, False otherwise.
        """
        return self._token.is_cancelled

    def cancel(self, reason: str | None = None) -> None:
        """Cancel the source and all linked tokens.

        Args:
            reason: Optional reason for cancellation.
        """
        self._token.cancel(reason)

        # Cancel all linked tokens
        for linked_token in self._linked_tokens:
            linked_token.cancel(reason)

    def link(self, token: CancellationToken) -> None:
        """Link another token to this source.

        When this source is cancelled, the linked token will also
        be cancelled.

        Args:
            token: Token to link to this source.
        """
        self._linked_tokens.append(token)

        # If already cancelled, cancel the linked token immediately
        if self._token.is_cancelled:
            token.cancel(self._token.cancel_reason)

    def reset(self) -> None:
        """Reset the source and all linked tokens."""
        self._token.reset()
        for linked_token in self._linked_tokens:
            linked_token.reset()
        self._linked_tokens.clear()


@dataclass
class CancellationStats:
    """Statistics about cancellation operations.

    Attributes:
        total_cancellations: Total number of cancellation requests.
        timeout_cancellations: Cancellations due to timeout.
        user_cancellations: Cancellations requested by users.
        system_cancellations: System-initiated cancellations.
    """

    total_cancellations: int = 0
    timeout_cancellations: int = 0
    user_cancellations: int = 0
    system_cancellations: int = 0

    def record_timeout(self) -> None:
        """Record a timeout cancellation."""
        self.total_cancellations += 1
        self.timeout_cancellations += 1

    def record_user_cancellation(self) -> None:
        """Record a user-initiated cancellation."""
        self.total_cancellations += 1
        self.user_cancellations += 1

    def record_system_cancellation(self) -> None:
        """Record a system-initiated cancellation."""
        self.total_cancellations += 1
        self.system_cancellations += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of stats.
        """
        return {
            "total_cancellations": self.total_cancellations,
            "timeout_cancellations": self.timeout_cancellations,
            "user_cancellations": self.user_cancellations,
            "system_cancellations": self.system_cancellations,
        }
