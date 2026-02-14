"""Dialog context management module.

This module provides classes for managing conversation context,
including message history and user state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nergal.llm import LLMMessage, MessageRole


@dataclass
class UserInfo:
    """Information about a user."""

    user_id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or f"User {self.user_id}"

    @property
    def display_name(self) -> str:
        """Get a display name for the user."""
        if self.username:
            return f"@{self.username}"
        return self.full_name


@dataclass
class DialogState:
    """State of a dialog session."""

    session_id: str
    user_info: UserInfo
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    current_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class DialogContext:
    """Manages the context of a conversation with a user.

    This class maintains message history, user information, and
    any additional state needed for the conversation.
    """

    def __init__(
        self,
        user_info: UserInfo,
        session_id: str | None = None,
        max_history: int = 20,
    ) -> None:
        """Initialize the dialog context.

        Args:
            user_info: Information about the user.
            session_id: Optional session identifier. If not provided,
                       one will be generated.
            max_history: Maximum number of messages to keep in history.
        """
        self.user_info = user_info
        self.session_id = session_id or f"{user_info.user_id}_{datetime.utcnow().timestamp()}"
        self.max_history = max_history
        self._history: list[LLMMessage] = []
        self._state = DialogState(
            session_id=self.session_id,
            user_info=user_info,
        )

    @property
    def state(self) -> DialogState:
        """Get the current dialog state."""
        return self._state

    @property
    def history(self) -> list[LLMMessage]:
        """Get the message history."""
        return self._history.copy()

    def add_message(self, role: MessageRole, content: str) -> None:
        """Add a message to the history.

        Args:
            role: Role of the message sender.
            content: Content of the message.
        """
        message = LLMMessage(role=role, content=content)
        self._history.append(message)

        # Trim history if needed
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

        self._state.message_count += 1
        self._state.touch()

    def add_user_message(self, content: str) -> None:
        """Add a user message to the history.

        Args:
            content: Content of the user's message.
        """
        self.add_message(MessageRole.USER, content)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the history.

        Args:
            content: Content of the assistant's response.
        """
        self.add_message(MessageRole.ASSISTANT, content)

    def clear_history(self) -> None:
        """Clear the message history."""
        self._history.clear()
        self._state.message_count = 0
        self._state.touch()

    def set_current_agent(self, agent_type: str) -> None:
        """Set the current agent handling the dialog.

        Args:
            agent_type: Type of the current agent.
        """
        self._state.current_agent = agent_type
        self._state.touch()

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value.

        Args:
            key: Metadata key.
            value: Metadata value.
        """
        self._state.metadata[key] = value
        self._state.touch()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value.

        Args:
            key: Metadata key.
            default: Default value if key not found.

        Returns:
            The metadata value or default.
        """
        return self._state.metadata.get(key, default)

    def get_context_for_agent(self) -> dict[str, Any]:
        """Get context data for agent processing.

        Returns:
            Dictionary with context information.
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_info.user_id,
            "user_name": self.user_info.full_name,
            "message_count": self._state.message_count,
            "current_agent": self._state.current_agent,
            "metadata": self._state.metadata.copy(),
        }

    def get_history_for_llm(self, include_system: bool = False) -> list[LLMMessage]:
        """Get history formatted for LLM request.

        Args:
            include_system: Whether to include system messages.

        Returns:
            List of LLMMessage objects.
        """
        if include_system:
            return self._history.copy()
        return [msg for msg in self._history if msg.role != MessageRole.SYSTEM]


class ContextManager:
    """Manages multiple dialog contexts.

    This class provides a central point for creating, storing, and
    retrieving dialog contexts for different users.
    """

    def __init__(self, max_contexts: int = 1000, context_ttl: int = 3600) -> None:
        """Initialize the context manager.

        Args:
            max_contexts: Maximum number of contexts to store.
            context_ttl: Time-to-live for contexts in seconds.
        """
        self._contexts: dict[int, DialogContext] = {}
        self.max_contexts = max_contexts
        self.context_ttl = context_ttl

    def get_or_create(
        self,
        user_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        language_code: str | None = None,
    ) -> DialogContext:
        """Get an existing context or create a new one.

        Args:
            user_id: Telegram user ID.
            first_name: User's first name.
            last_name: User's last name.
            username: User's username.
            language_code: User's language code.

        Returns:
            DialogContext for the user.
        """
        if user_id in self._contexts:
            return self._contexts[user_id]

        user_info = UserInfo(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
        )
        context = DialogContext(user_info=user_info)
        self._contexts[user_id] = context

        # Clean up old contexts if needed
        self._cleanup_if_needed()

        return context

    def get(self, user_id: int) -> DialogContext | None:
        """Get a context by user ID.

        Args:
            user_id: Telegram user ID.

        Returns:
            DialogContext or None if not found.
        """
        return self._contexts.get(user_id)

    def remove(self, user_id: int) -> bool:
        """Remove a context by user ID.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if context was removed, False if not found.
        """
        if user_id in self._contexts:
            del self._contexts[user_id]
            return True
        return False

    def clear_all(self) -> None:
        """Clear all stored contexts."""
        self._contexts.clear()

    def _cleanup_if_needed(self) -> None:
        """Remove old contexts if the limit is exceeded."""
        if len(self._contexts) <= self.max_contexts:
            return

        # Sort by updated_at and remove oldest
        sorted_contexts = sorted(
            self._contexts.items(),
            key=lambda x: x[1].state.updated_at,
            reverse=True,
        )

        # Keep only the most recent contexts
        self._contexts = dict(sorted_contexts[: self.max_contexts])

    @property
    def context_count(self) -> int:
        """Get the number of stored contexts."""
        return len(self._contexts)
