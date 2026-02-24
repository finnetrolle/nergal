"""Database connection management using asyncpg.

This module provides a database connection pool class that integrates
with the DI container. Global state has been removed in favor of
proper dependency injection.

Usage:
    # Through DI container (recommended)
    from nergal.container import get_container
    db = get_container().database()
    await db.connect()

    # Direct instantiation
    from nergal.database.connection import DatabaseConnection
    from nergal.config import get_settings
    db = DatabaseConnection(get_settings().database)
    await db.connect()
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from asyncpg import Pool, Connection

from nergal.config import DatabaseSettings, get_settings

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection manager class.

    Provides a convenient interface for database operations
    with automatic connection management.

    This class manages its own connection pool and requires
    explicit connect/disconnect calls for lifecycle management.
    """

    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        """Initialize database connection manager.

        Args:
            settings: Database settings. If not provided, uses global settings.
        """
        self._settings = settings or get_settings().database
        self._pool: Pool | None = None

    async def connect(self) -> None:
        """Establish database connection pool.

        Creates the connection pool if not already created.
        Safe to call multiple times - will only create pool once.
        """
        if self._pool is not None:
            logger.debug("Database pool already connected")
            return

        logger.info(
            f"Creating database connection pool to {self._settings.host}:{self._settings.port}/{self._settings.name}"
        )

        self._pool = await asyncpg.create_pool(
            host=self._settings.host,
            port=self._settings.port,
            user=self._settings.user,
            password=self._settings.password,
            database=self._settings.name,
            min_size=self._settings.min_pool_size,
            max_size=self._settings.max_pool_size,
            command_timeout=self._settings.connection_timeout,
        )

        logger.info("Database connection pool created successfully")

    async def disconnect(self) -> None:
        """Close database connection pool.

        Safe to call multiple times - will handle already closed pool.
        """
        if self._pool is None:
            logger.debug("Database pool already disconnected")
            return

        logger.info("Closing database connection pool")
        await self._pool.close()
        self._pool = None
        logger.info("Database connection pool closed")

    @property
    def is_connected(self) -> bool:
        """Check if the connection pool is active.

        Returns:
            True if pool exists and is not closed.
        """
        return self._pool is not None and not self._pool._closed

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[Connection, None]:
        """Get a database connection.

        Automatically connects if pool is not initialized.

        Yields:
            asyncpg Connection instance.

        Raises:
            RuntimeError: If database connection fails.
        """
        if self._pool is None:
            await self.connect()

        if self._pool is None:
            raise RuntimeError("Failed to establish database connection")

        async with self._pool.acquire() as conn:
            yield conn

    async def execute(self, query: str, *args) -> str:
        """Execute a query and return status.

        Args:
            query: SQL query.
            *args: Query parameters.

        Returns:
            Query status string.
        """
        async with self.connection() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        """Execute a query and return all rows.

        Args:
            query: SQL query.
            *args: Query parameters.

        Returns:
            List of database records.
        """
        async with self.connection() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        """Execute a query and return a single row.

        Args:
            query: SQL query.
            *args: Query parameters.

        Returns:
            Single database record or None.
        """
        async with self.connection() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args) -> any:
        """Execute a query and return a single value.

        Args:
            query: SQL query.
            *args: Query parameters.

        Returns:
            Single value from the query.
        """
        async with self.connection() as conn:
            return await conn.fetchval(query, *args)

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Connection, None]:
        """Get a database connection with transaction management.

        Usage:
            async with db.transaction() as conn:
                await conn.execute("INSERT INTO ...")
                await conn.execute("UPDATE ...")

        Yields:
            asyncpg Connection instance with active transaction.
        """
        if self._pool is None:
            await self.connect()

        if self._pool is None:
            raise RuntimeError("Failed to establish database connection")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield conn


# ============== Legacy Compatibility Functions ==============
# These functions are deprecated and will be removed in a future version.
# Use DI container's database() provider instead.

_deprecated_db: DatabaseConnection | None = None


async def create_pool(settings: DatabaseSettings | None = None) -> Pool:
    """Create a database connection pool.

    .. deprecated::
        Use DatabaseConnection.connect() via DI container instead.

    Args:
        settings: Database settings. If not provided, uses global settings.

    Returns:
        asyncpg Pool instance.
    """
    global _deprecated_db

    logger.warning(
        "create_pool() is deprecated. Use DI container's database() provider instead."
    )

    if _deprecated_db is None:
        _deprecated_db = DatabaseConnection(settings)

    await _deprecated_db.connect()
    return _deprecated_db._pool  # type: ignore


async def get_pool() -> Pool:
    """Get the database connection pool.

    .. deprecated::
        Use DI container's database() provider instead.

    Returns:
        asyncpg Pool instance.
    """
    global _deprecated_db

    logger.warning(
        "get_pool() is deprecated. Use DI container's database() provider instead."
    )

    if _deprecated_db is None:
        await create_pool()

    return _deprecated_db._pool  # type: ignore


async def close_pool() -> None:
    """Close the database connection pool.

    .. deprecated::
        Use DI container's database() provider instead.
    """
    global _deprecated_db

    logger.warning(
        "close_pool() is deprecated. Use DI container's database() provider instead."
    )

    if _deprecated_db is not None:
        await _deprecated_db.disconnect()
        _deprecated_db = None


@asynccontextmanager
async def get_connection() -> AsyncGenerator[Connection, None]:
    """Get a database connection from the pool.

    .. deprecated::
        Use DI container's database() provider instead.

    Yields:
        asyncpg Connection instance.
    """
    logger.warning(
        "get_connection() is deprecated. Use DI container's database() provider instead."
    )

    db = get_database()
    async with db.connection() as conn:
        yield conn


def get_database() -> DatabaseConnection:
    """Get the database connection singleton.

    .. deprecated::
        Use DI container's database() provider instead.

    Returns:
        DatabaseConnection instance.
    """
    global _deprecated_db

    logger.warning(
        "get_database() is deprecated. Use DI container's database() provider instead."
    )

    if _deprecated_db is None:
        _deprecated_db = DatabaseConnection()

    return _deprecated_db
