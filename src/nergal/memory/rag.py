"""RAG (Retrieval-Augmented Generation) context builder.

This module provides functionality for building context from memory
to be included in LLM prompts, enabling the agent to access
relevant stored information.

Example:
    >>> from nergal.memory.rag import RAGContextBuilder
    >>> from nergal.memory.sqlite import SQLiteMemory
    >>>
    >>> memory = SQLiteMemory(":memory:")
    >>> await memory.initialize()
    >>>
    >>> builder = RAGContextBuilder(memory)
    >>> context = builder.build("How do I deploy the app?")
    >>> print(context)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from nergal.memory.base import Memory, MemoryCategory, MemoryEntry

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """Configuration for RAG context building.

    Attributes:
        max_entries: Maximum number of entries to retrieve per category.
        min_score: Minimum relevance score for entries to include.
        categories: Categories to search in. None means all.
        include_metadata: Whether to include metadata in context.
        format_template: Template for formatting individual entries.
        section_header: Header for the context section in the prompt.
    """

    max_entries: int = 5
    """Maximum number of entries to retrieve per category."""

    min_score: float | None = None
    """Minimum relevance score. None means no minimum."""

    categories: list[MemoryCategory] | None = None
    """Categories to search in. None means all categories."""

    include_metadata: bool = False
    """Whether to include metadata in context."""

    format_template: str = "- [{score:.2f}] {content}"
    """Template for formatting individual entries."""

    section_header: str = "---"
    """Header for the context section in the prompt."""


@dataclass
class RAGContext:
    """Built RAG context for use in prompts.

    Attributes:
        text: The formatted context text.
        entries: List of entries included in the context.
        metadata: Metadata about the context (counts, scores, etc.).
    """

    text: str
    """The formatted context text."""

    entries: list[MemoryEntry] = field(default_factory=list)
    """List of entries included in the context."""

    metadata: dict = field(default_factory=dict)
    """Metadata about the context (counts, scores, etc.)."""

    def __str__(self) -> str:
        return self.text

    def __len__(self) -> int:
        return len(self.text)


class RAGContextBuilder:
    """Builder for creating RAG contexts from memory.

    The RAG context builder retrieves relevant information from
    memory and formats it for inclusion in LLM prompts. This enables
    the agent to leverage previously stored knowledge and context.

    Args:
        memory: The Memory backend to use for retrieval.
        config: Optional RAGConfig for customizing behavior.

    Example:
        >>> memory = SQLiteMemory(":memory:")
        >>> await memory.initialize()
        >>>
        >>> builder = RAGContextBuilder(memory)
        >>> context = builder.build("How do I deploy?")
        >>> prompt = f"Context:\\n{context.text}\\n\\nQuestion: {query}"
    """

    def __init__(
        self,
        memory: Memory,
        config: RAGConfig | None = None,
    ) -> None:
        """Initialize the RAG context builder.

        Args:
            memory: The Memory backend to use.
            config: Optional configuration.
        """
        self.memory = memory
        self.config = config or RAGConfig()

    def build(
        self,
        query: str,
        categories: list[MemoryCategory] | None = None,
        max_entries: int | None = None,
    ) -> RAGContext:
        """Build RAG context for a query.

        Retrieves relevant entries from memory and formats them
        for inclusion in an LLM prompt.

        Args:
            query: The query to search for.
            categories: Optional override for categories to search.
            max_entries: Optional override for max entries.

        Returns:
            RAGContext with formatted text and metadata.

        Examples:
            >>> context = builder.build("How do I deploy?")
            >>> print(context.text)

            Search specific categories only:
            >>> context = builder.build(
            ...     "What are user preferences?",
            ...     categories=[MemoryCategory.USER],
            ... )
        """
        # Determine categories to search
        search_categories = categories or self.config.categories

        # Determine max entries
        limit = max_entries or self.config.max_entries

        entries = []
        metadata = {
            "query": query,
            "categories_searched": (
                [c.value for c in search_categories] if search_categories else ["all"]
            ),
            "total_entries": 0,
            "avg_score": 0.0,
        }

        # Retrieve entries from each category
        if search_categories:
            # Search specific categories
            for category in search_categories:
                try:
                    category_entries = await self._retrieve_for_category(
                        query, category, limit
                    )
                    entries.extend(category_entries)
                except Exception as e:
                    logger.warning(f"Failed to retrieve from {category.value}: {e}")
        else:
            # Search all categories
            for category in MemoryCategory:
                try:
                    category_entries = await self._retrieve_for_category(
                        query, category, limit
                    )
                    entries.extend(category_entries)
                except Exception as e:
                    logger.warning(f"Failed to retrieve from {category.value}: {e}")

        # Filter by minimum score
        if self.config.min_score is not None:
            entries = [e for e in entries if (e.score or 0) >= self.config.min_score]

        # Sort by score (descending)
        entries.sort(key=lambda e: e.score or 0, reverse=True)

        # Limit to max_entries total
        entries = entries[:limit]

        # Update metadata
        metadata["total_entries"] = len(entries)
        if entries:
            avg_score = sum(e.score or 0 for e in entries) / len(entries)
            metadata["avg_score"] = avg_score

        # Format context
        context_text = self._format_context(entries)

        return RAGContext(
            text=context_text,
            entries=entries,
            metadata=metadata,
        )

    async def _retrieve_for_category(
        self,
        query: str,
        category: MemoryCategory,
        limit: int,
    ) -> list[MemoryEntry]:
        """Retrieve entries for a specific category.

        Args:
            query: Search query.
            category: Category to search.
            limit: Max entries to retrieve.

        Returns:
            List of MemoryEntry objects.
        """
        return await self.memory.recall(
            query=query,
            limit=limit,
            category=category,
        )

    def _format_context(self, entries: list[MemoryEntry]) -> str:
        """Format entries into context text.

        Args:
            entries: List of entries to format.

        Returns:
            Formatted context string.
        """
        if not entries:
            return ""

        lines = [self.config.section_header]

        for entry in entries:
            score = entry.score or 0.0

            if self.config.include_metadata:
                lines.append(
                    f"[{entry.category.value}] {self.config.format_template.format(
                        score=score,
                        content=entry.content,
                        key=entry.key,
                        metadata=entry.metadata or {},
                    )}"
                )
            else:
                lines.append(
                    self.config.format_template.format(
                        score=score,
                        content=entry.content,
                        key=entry.key,
                        metadata=entry.metadata or {},
                    )
                )

        return "\n".join(lines)

    def set_config(self, config: RAGConfig) -> None:
        """Update the configuration.

        Args:
            config: New configuration.
        """
        self.config = config


def build_context(
    memory: Memory,
    query: str,
    max_entries: int = 5,
    min_score: float | None = None,
    categories: list[MemoryCategory] | None = None,
) -> str:
    """Convenience function to build RAG context.

    Args:
        memory: The Memory backend.
        query: The query to search for.
        max_entries: Maximum entries to retrieve.
        min_score: Minimum relevance score.
        categories: Categories to search.

    Returns:
        Formatted context string.

    Example:
        >>> context = build_context(
        ...     memory=memory,
        ...     query="How do I deploy?",
        ...     max_entries=5,
        ... )
        >>> prompt = f"Context:\\n{context}\\n\\n{user_query}"
    """
    config = RAGConfig(
        max_entries=max_entries,
        min_score=min_score,
        categories=categories,
    )
    builder = RAGContextBuilder(memory, config)
    context = builder.build(query)
    return context.text
