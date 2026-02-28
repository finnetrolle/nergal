"""SQLite backend for Memory system with FTS5 full-text search.

This module provides a SQLite-based implementation of the Memory
interface, using FTS5 (Full-Text Search) for efficient text retrieval.

Features:
    - Persistent storage in SQLite database
    - FTS5 full-text search for semantic/keyword matching
    - BM25 ranking for relevance scoring
    - Optional category filtering
    - Async operations using aiosqlite

Example:
    >>> from nergal.memory.sqlite import SQLiteMemory
    >>> from nergal.memory.base import MemoryCategory
    >>>
    >>> memory = SQLiteMemory(":memory:")
    >>> await memory.initialize()
    >>>
    >>> await memory.store(
    ...     key="fact_1",
    ...     content="Python is a programming language",
    ...     category=MemoryCategory.KNOWLEDGE,
    ... )
    >>>
    >>> results = await memory.recall("programming", limit=5)
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import aiosqlite

from nergal.memory.base import Memory, MemoryCategory, MemoryEntry
from nergal.memory.exceptions import MemoryError

logger = logging.getLogger(__name__)


class SQLiteMemory(Memory):
    """SQLite backend for Memory with FTS5 full-text search.

    This implementation uses SQLite's FTS5 extension for efficient
    full-text search. It stores memory entries in a main table and
    maintains a separate FTS5 virtual table for search indexing.

    The database schema includes:
    - memory_entries: Main table for storing entries
    - memory_entries_fts: FTS5 virtual table for search

    Args:
        db_path: Path to SQLite database file. Use ":memory:" for in-memory.
        table_prefix: Prefix for table names (allows multiple instances in same DB).

    Example:
        >>> memory = SQLiteMemory("~/.nergal/memory.db")
        >>> await memory.initialize()
        >>> await memory.store("key1", "content", MemoryCategory.KNOWLEDGE)
    """

    def __init__(
        self,
        db_path: str | Path,
        table_prefix: str = "",
    ) -> None:
        """Initialize SQLite memory backend.

        Args:
            db_path: Path to SQLite database file. Use ":memory:" for in-memory.
            table_prefix: Prefix for table names.
        """
        self.db_path = Path(db_path).expanduser() if isinstance(db_path, str) else db_path
        self.table_prefix = table_prefix
        self._initialized = False

    @property
    def _entries_table(self) -> str:
        """Get the entries table name."""
        prefix = f"{self.table_prefix}memory_entries"
        return prefix if self.table_prefix else "memory_entries"

    @property
    def _fts_table(self) -> str:
        """Get the FTS table name."""
        prefix = f"{self.table_prefix}memory_entries_fts"
        return prefix if self.table_prefix else "memory_entries_fts"

    async def initialize(self) -> None:
        """Initialize the database schema.

        Creates the necessary tables if they don't exist.
        """
        if self._initialized:
            return

        # Ensure parent directory exists
        if self.db_path != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            # Enable FTS5
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")

            # Create main entries table
            await db.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._entries_table} (
                    key TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            # Create FTS5 virtual table for search
            await db.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {self._fts_table}
                USING fts5(content, category, key, tokenize='porter unicode61')
            """)

            # Create indexes
            await db.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self._entries_table}_category
                ON {self._entries_table}(category)
            """)

            # Create triggers to keep FTS in sync with main table
            await self._create_triggers(db)

            await db.commit()

        self._initialized = True
        logger.info(f"SQLiteMemory initialized at {self.db_path}")

    async def _create_triggers(self, db: aiosqlite.Connection) -> None:
        """Create triggers to keep FTS table in sync.

        Args:
            db: Database connection.
        """
        # Insert trigger
        await db.execute(f"""
            CREATE TRIGGER IF NOT EXISTS {self._entries_table}_ai AFTER INSERT
            ON {self._entries_table} BEGIN
                INSERT INTO {self._fts_table}(rowid, content, category, key)
                VALUES (new.rowid, new.content, new.category, new.key);
            END
        """)

        # Delete trigger
        await db.execute(f"""
            CREATE TRIGGER IF NOT EXISTS {self._entries_table}_ad AFTER DELETE
            ON {self._entries_table} BEGIN
                INSERT INTO {self._fts_table}({self._fts_table}, rowid, content, category, key)
                VALUES ('delete', old.rowid, old.content, old.category, old.key);
            END
        """)

        # Update trigger
        await db.execute(f"""
            CREATE TRIGGER IF NOT EXISTS {self._entries_table}_au AFTER UPDATE
            ON {self._entries_table} BEGIN
                INSERT INTO {self._fts_table}({self._fts_table}, rowid, content, category, key)
                VALUES ('delete', old.rowid, old.content, old.category, old.key);
                INSERT INTO {self._fts_table}(rowid, content, category, key)
                VALUES (new.rowid, new.content, new.category, new.key);
            END
        """)

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
        """
        await self._ensure_initialized()

        created_at = datetime.utcnow().isoformat()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    f"""
                    INSERT OR REPLACE INTO {self._entries_table}
                    (key, content, category, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (key, content, category.value, created_at, _serialize_metadata(metadata)),
                )
                await db.commit()
                logger.debug(f"Stored memory entry: {key}")
        except sqlite3.Error as e:
            logger.error(f"Failed to store memory entry: {e}")
            raise MemoryError(f"Failed to store entry: {e}") from e

    async def recall(
        self,
        query: str,
        limit: int = 5,
        category: MemoryCategory | None = None,
    ) -> list[MemoryEntry]:
        """Recall relevant memory entries using FTS5 search.

        Args:
            query: Search query string.
            limit: Maximum number of entries to return.
            category: Optional category filter.

        Returns:
            List of relevant MemoryEntry objects, sorted by relevance.
        """
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                # FTS5 search with BM25 ranking
                # Use MATCH for full-text search
                base_query = f"""
                    SELECT
                        e.key, e.content, e.category, e.created_at, e.metadata,
                        bm25({self._fts_table}) as score
                    FROM {self._fts_table} fts
                    JOIN {self._entries_table} e ON e.rowid = fts.rowid
                    WHERE {self._fts_table} MATCH ?
                """

                params = [query]

                # Add category filter if specified
                if category:
                    base_query += " AND e.category = ?"
                    params.append(category.value)

                # Order by BM25 score and limit results
                base_query += " ORDER BY score LIMIT ?"
                params.append(limit)

                cursor = await db.execute(base_query, params)
                rows = await cursor.fetchall()

                return [
                    MemoryEntry(
                        key=row[0],
                        content=row[1],
                        category=MemoryCategory(row[2]),
                        score=row[5],
                        created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                        metadata=_deserialize_metadata(row[4]),
                    )
                    for row in rows
                ]
        except sqlite3.Error as e:
            logger.error(f"Failed to recall memory: {e}")
            raise MemoryError(f"Failed to recall entries: {e}") from e

    async def forget(self, key: str) -> None:
        """Remove a memory entry by key.

        Args:
            key: The key of the entry to remove.

        Raises:
            MemoryError: If deletion fails.
        """
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    f"DELETE FROM {self._entries_table} WHERE key = ?",
                    (key,),
                )
                if cursor.rowcount == 0:
                    raise MemoryError(f"Entry not found: {key}")
                await db.commit()
                logger.debug(f"Forgot memory entry: {key}")
        except sqlite3.Error as e:
            logger.error(f"Failed to forget memory: {e}")
            raise MemoryError(f"Failed to delete entry: {e}") from e

    async def get_by_key(self, key: str) -> MemoryEntry | None:
        """Get a memory entry by its exact key.

        Args:
            key: The exact key to look up.

        Returns:
            The MemoryEntry if found, None otherwise.
        """
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    f"""
                    SELECT key, content, category, created_at, metadata
                    FROM {self._entries_table}
                    WHERE key = ?
                    """,
                    (key,),
                )
                row = await cursor.fetchone()

                if row is None:
                    return None

                return MemoryEntry(
                    key=row[0],
                    content=row[1],
                    category=MemoryCategory(row[2]),
                    score=None,
                    created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                    metadata=_deserialize_metadata(row[4]),
                )
        except sqlite3.Error as e:
            logger.error(f"Failed to get entry by key: {e}")
            raise MemoryError(f"Failed to get entry: {e}") from e

    async def clear_category(self, category: MemoryCategory) -> int:
        """Clear all entries in a category.

        Args:
            category: The category to clear.

        Returns:
            Number of entries removed.
        """
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    f"DELETE FROM {self._entries_table} WHERE category = ?",
                    (category.value,),
                )
                deleted_count = cursor.rowcount
                await db.commit()
                logger.info(f"Cleared {deleted_count} entries from {category.value}")
                return deleted_count
        except sqlite3.Error as e:
            logger.error(f"Failed to clear category: {e}")
            raise MemoryError(f"Failed to clear category: {e}") from e

    async def _ensure_initialized(self) -> None:
        """Ensure the database is initialized."""
        if not self._initialized:
            await self.initialize()


def _serialize_metadata(metadata: dict | None) -> str | None:
    """Serialize metadata to JSON string.

    Args:
        metadata: Metadata dictionary.

    Returns:
        JSON string or None.
    """
    if metadata is None:
        return None
    import json

    return json.dumps(metadata)


def _deserialize_metadata(data: str | None) -> dict | None:
    """Deserialize metadata from JSON string.

    Args:
        data: JSON string.

    Returns:
        Metadata dictionary or None.
    """
    if data is None:
        return None
    import json

    try:
        return json.loads(data)
    except json.JSONDecodeError:
        logger.warning(f"Failed to deserialize metadata: {data}")
        return None
