"""Database connection management using asyncpg.

This module provides a singleton database connection pool
and connection management utilities.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from asyncpg import Pool, Connection

from nergal.config import DatabaseSettings, get_settings

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Pool | None = None


async def create_pool(settings: DatabaseSettings | None = None) -> Pool:
    """Create a database connection pool.

    Args:
        settings: Database settings. If not provided, uses global settings.

    Returns:
        asyncpg Pool instance.
    """
    global _pool

    if settings is None:
        settings = get_settings().database

    logger.info(f"Creating database connection pool to {settings.host}:{settings.port}/{settings.name}")

    _pool = await asyncpg.create_pool(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        database=settings.name,
        min_size=settings.min_pool_size,
        max_size=settings.max_pool_size,
        command_timeout=settings.connection_timeout,
    )

    logger.info("Database connection pool created successfully")
    return _pool


async def get_pool() -> Pool:
    """Get the database connection pool.

    Creates a new pool if one doesn't exist.

    Returns:
        asyncpg Pool instance.
    """
    global _pool

    if _pool is None:
        _pool = await create_pool()

    return _pool


async def close_pool() -> None:
    """Close the database connection pool."""
    global _pool

    if _pool is not None:
        logger.info("Closing database connection pool")
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


@asynccontextmanager
async def get_connection() -> AsyncGenerator[Connection, None]:
    """Get a database connection from the pool.

    Usage:
        async with get_connection() as conn:
            result = await conn.fetch("SELECT * FROM users")

    Yields:
        asyncpg Connection instance.
    """
    pool = await get_pool()
    async with pool.acquire() as connection:
        yield connection


class DatabaseConnection:
    """Database connection manager class.

    Provides a convenient interface for database operations
    with automatic connection management.
    """

    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        """Initialize database connection manager.

        Args:
            settings: Database settings. If not provided, uses global settings.
        """
        self._settings = settings or get_settings().database
        self._pool: Pool | None = None

    async def connect(self) -> None:
        """Establish database connection pool."""
        if self._pool is None:
            self._pool = await create_pool(self._settings)

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[Connection, None]:
        """Get a database connection.

        Yields:
            asyncpg Connection instance.
        """
        if self._pool is None:
            await self.connect()

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


# Singleton instance
_db_connection: DatabaseConnection | None = None


def get_database() -> DatabaseConnection:
    """Get the database connection singleton.

    Returns:
        DatabaseConnection instance.
    """
    global _db_connection

    if _db_connection is None:
        _db_connection = DatabaseConnection()

    return _db_connection
