"""Base classes and interfaces for Memory system.

This module provides the core abstractions for the memory system,
including the Memory interface, MemoryEntry dataclass, and
MemoryCategory enum.

Example:
    >>> from nergal.memory.base import Memory, MemoryCategory, MemoryEntry
    >>>
    >>> entry = MemoryEntry(
    ...     key="user_pref_123",
    ...     content="User prefers concise responses",
    ...     category=MemoryCategory.USER,
    ... )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MemoryCategory(Enum):
    """Categories for memory entries.

    Memory entries are categorized to enable selective retrieval
    and context building. Different categories serve different purposes:

    CONVERSATION: Messages from user interactions
    KNOWLEDGE: General knowledge and facts
    USER: User-specific information and preferences
    SYSTEM: System-level information and state
    """

    CONVERSATION = "conversation"
    """Messages from conversation history."""

    KNOWLEDGE = "knowledge"
    """General knowledge and facts learned."""

    USER = "user"
    """User-specific information and preferences."""

    SYSTEM = "system"
    """System-level information and state."""


@dataclass
class MemoryEntry:
    """Single memory entry.

    Represents a piece of stored information in the memory system.
    Entries can be retrieved by key, category, or through semantic
    search (if supported by the backend).

    Attributes:
        key: Unique identifier for this entry.
        content: The actual content/text of the memory.
        category: Category classification for filtering.
        score: Relevance score from search (None if not searched).
        created_at: Timestamp when entry was created.
        metadata: Optional additional metadata as dict.

    Examples:
        Basic entry:
        >>> entry = MemoryEntry(
        ...     key="fact_1",
        ...     content="Python was created in 1991",
        ...     category=MemoryCategory.KNOWLEDGE,
        ... )

        Entry with metadata:
        >>> entry = MemoryEntry(
        ...     key="user_pref",
        ...     content="Prefers dark mode",
        ...     category=MemoryCategory.USER,
        ...     metadata={"source": "explicit_statement"},
        ... )
    """

    key: str
    """Unique identifier for this memory entry."""

    content: str
    """The content/text of the memory entry."""

    category: MemoryCategory
    """Category classification for filtering and retrieval."""

    score: float | None = field(default=None)
    """Relevance score from search (None if not from search)."""

    created_at: datetime | None = field(default=None)
    """Timestamp when the entry was created."""

    metadata: dict | None = field(default=None)
    """Optional additional metadata as a dictionary."""


class Memory(ABC):
    """Abstract base class for memory backends.

    Memory backends provide persistent storage and retrieval of
    information for the agent. Implementations can use different
    storage mechanisms (SQLite, PostgreSQL, vector databases, etc.).

    The memory system supports:
    - Storing entries with keys and categories
    - Retrieving entries by key
    - Semantic/keyword search for relevant entries
    - Forgetting (deleting) entries

    Example implementation:
        >>> class SQLiteMemory(Memory):
        ...     async def store(self, key, content, category, metadata=None):
        ...         # Implementation using SQLite
        ...         pass
        ...
        ...     async def recall(self, query, limit=5, category=None):
        ...         # Implementation with FTS5 or vector search
        ...         pass
        ...
        ...     async def forget(self, key):
        ...         # Delete entry by key
        ...         pass
    """

    @abstractmethod
    async def store(
        self,
        key: str,
        content: str,
        category: MemoryCategory,
        metadata: dict | None = None,
    ) -> None:
        """Store a memory entry.

        Args:
            key: Unique identifier for the entry.
            content: The content/text to store.
            category: Category for classification.
            metadata: Optional additional metadata.

        Raises:
            MemoryError: If storage fails.

        Examples:
            >>> await memory.store(
            ...     key="fact_1",
            ...     content="Python is a programming language",
            ...     category=MemoryCategory.KNOWLEDGE,
            ... )
        """
        pass

    @abstractmethod
    async def recall(
        self,
        query: str,
        limit: int = 5,
        category: MemoryCategory | None = None,
    ) -> list[MemoryEntry]:
        """Recall relevant memory entries.

        Performs a search for entries relevant to the query.
        The search method depends on the implementation
        (FTS5, vector search, simple matching, etc.).

        Args:
            query: Search query string.
            limit: Maximum number of entries to return.
            category: Optional category filter.

        Returns:
            List of relevant MemoryEntry objects, sorted by
            relevance (highest first).

        Examples:
            >>> results = await memory.recall(
            ...     query="programming language",
            ...     limit=3,
            ...     category=MemoryCategory.KNOWLEDGE,
            ... )
            >>> for entry in results:
            ...     print(f"{entry.key}: {entry.content[:50]}...")
        """
        pass

    @abstractmethod
    async def forget(self, key: str) -> None:
        """Remove a memory entry.

        Args:
            key: The key of the entry to remove.

        Raises:
            MemoryError: If the entry doesn't exist or deletion fails.

        Examples:
            >>> await memory.forget("fact_1")
        """
        pass

    @abstractmethod
    async def get_by_key(self, key: str) -> MemoryEntry | None:
        """Get a memory entry by its exact key.

        Args:
            key: The exact key to look up.

        Returns:
            The MemoryEntry if found, None otherwise.

        Examples:
            >>> entry = await memory.get_by_key("fact_1")
            >>> if entry:
            ...     print(entry.content)
        """
        pass

    @abstractmethod
    async def clear_category(self, category: MemoryCategory) -> int:
        """Clear all entries in a category.

        Args:
            category: The category to clear.

        Returns:
            Number of entries removed.

        Examples:
            >>> count = await memory.clear_category(MemoryCategory.CONVERSATION)
            >>> print(f"Cleared {count} conversation entries")
        """
        pass
