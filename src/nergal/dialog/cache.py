"""Agent result caching module.

This module provides caching functionality for agent results to avoid
redundant processing of similar requests and improve response times.

The cache uses an LRU (Least Recently Used) eviction policy with TTL
(Time To Live) support for automatic expiration of cached entries.
"""

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from nergal.dialog.base import AgentResult, AgentType


@dataclass
class CacheEntry:
    """A single cache entry containing the cached result and metadata.

    Attributes:
        result: The cached AgentResult.
        created_at: Timestamp when the entry was created.
        expires_at: Timestamp when the entry expires.
        hits: Number of times this entry has been accessed.
    """

    result: AgentResult
    created_at: float
    expires_at: float
    hits: int = 0


@dataclass
class CacheStats:
    """Cache statistics for monitoring.

    Attributes:
        hits: Number of cache hits.
        misses: Number of cache misses.
        evictions: Number of entries evicted due to LRU or TTL.
        size: Current number of entries in cache.
        max_size: Maximum cache capacity.
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate the cache hit rate.

        Returns:
            Hit rate as a float between 0.0 and 1.0.
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


class AgentResultCache:
    """Thread-safe LRU cache for agent results with TTL support.

    This cache stores AgentResult objects keyed by agent type and message hash.
    It supports automatic expiration via TTL and LRU eviction when the cache
    reaches its maximum size.

    Attributes:
        enabled: Whether caching is enabled.
        ttl_seconds: Time-to-live for cache entries in seconds.
        max_size: Maximum number of entries in the cache.

    Example:
        >>> cache = AgentResultCache(enabled=True, ttl_seconds=300, max_size=1000)
        >>> cache.set(AgentType.WEB_SEARCH, "What is Python?", result)
        >>> cached = cache.get(AgentType.WEB_SEARCH, "What is Python?")
        >>> if cached:
        ...     print(cached.response)
    """

    def __init__(
        self,
        enabled: bool = True,
        ttl_seconds: int = 300,
        max_size: int = 1000,
    ) -> None:
        """Initialize the cache.

        Args:
            enabled: Whether caching is enabled. When disabled, all operations
                are no-ops.
            ttl_seconds: Time-to-live for cache entries in seconds.
                Default is 300 (5 minutes).
            max_size: Maximum number of entries in the cache.
                Default is 1000.
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()
        self._stats = CacheStats(max_size=max_size)
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size

    def _generate_key(self, agent_type: AgentType, message: str, **kwargs: Any) -> str:
        """Generate a cache key from agent type, message, and optional context.

        The key is a combination of the agent type and a hash of the message
        and any additional context that affects the result.

        Args:
            agent_type: The type of agent.
            message: The user message.
            **kwargs: Additional context that affects the cached result.

        Returns:
            A string key for the cache entry.
        """
        # Normalize the message by stripping whitespace and lowercasing
        normalized_message = message.strip().lower()

        # Create a hash of the message and any additional context
        hash_input = normalized_message
        if kwargs:
            # Sort kwargs to ensure consistent ordering
            sorted_kwargs = sorted(kwargs.items())
            hash_input += str(sorted_kwargs)

        message_hash = hashlib.sha256(hash_input.encode(), usedforsecurity=False).hexdigest()

        return f"{agent_type.value}:{message_hash}"

    def get(
        self, agent_type: AgentType, message: str, **kwargs: Any
    ) -> AgentResult | None:
        """Retrieve a cached result if available and not expired.

        Args:
            agent_type: The type of agent.
            message: The user message.
            **kwargs: Additional context that was used to generate the key.

        Returns:
            The cached AgentResult if found and valid, None otherwise.
        """
        if not self.enabled:
            return None

        key = self._generate_key(agent_type, message, **kwargs)

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            # Check if entry has expired
            current_time = time.time()
            if current_time > entry.expires_at:
                # Remove expired entry
                del self._cache[key]
                self._stats.evictions += 1
                self._stats.misses += 1
                self._update_size()
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats.hits += 1

            return entry.result

    def set(
        self,
        agent_type: AgentType,
        message: str,
        result: AgentResult,
        **kwargs: Any,
    ) -> None:
        """Store a result in the cache.

        Args:
            agent_type: The type of agent.
            message: The user message.
            result: The AgentResult to cache.
            **kwargs: Additional context to include in the cache key.
        """
        if not self.enabled:
            return

        key = self._generate_key(agent_type, message, **kwargs)
        current_time = time.time()

        with self._lock:
            # Remove oldest entries if cache is full
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats.evictions += 1

            # Create new entry
            entry = CacheEntry(
                result=result,
                created_at=current_time,
                expires_at=current_time + self.ttl_seconds,
            )

            # If key already exists, remove it first (to update position)
            if key in self._cache:
                del self._cache[key]

            self._cache[key] = entry
            self._update_size()

    def invalidate(
        self, agent_type: AgentType, message: str, **kwargs: Any
    ) -> bool:
        """Invalidate (remove) a specific cache entry.

        Args:
            agent_type: The type of agent.
            message: The user message.
            **kwargs: Additional context used to generate the key.

        Returns:
            True if an entry was removed, False if not found.
        """
        if not self.enabled:
            return False

        key = self._generate_key(agent_type, message, **kwargs)

        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._update_size()
                return True
            return False

    def invalidate_agent(self, agent_type: AgentType) -> int:
        """Invalidate all cache entries for a specific agent type.

        Args:
            agent_type: The type of agent to invalidate.

        Returns:
            Number of entries removed.
        """
        if not self.enabled:
            return 0

        prefix = f"{agent_type.value}:"
        removed = 0

        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
                removed += 1
            self._update_size()

        return removed

    def clear(self) -> int:
        """Clear all entries from the cache.

        Returns:
            Number of entries that were cleared.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._update_size()
            return count

    def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache.

        This method can be called periodically to clean up expired entries
        without waiting for them to be accessed.

        Returns:
            Number of expired entries removed.
        """
        if not self.enabled:
            return 0

        current_time = time.time()
        removed = 0

        with self._lock:
            keys_to_remove = [
                key
                for key, entry in self._cache.items()
                if current_time > entry.expires_at
            ]
            for key in keys_to_remove:
                del self._cache[key]
                self._stats.evictions += 1
                removed += 1
            self._update_size()

        return removed

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            A CacheStats object with current statistics.
        """
        with self._lock:
            # Return a copy to avoid external modification
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=len(self._cache),
                max_size=self._stats.max_size,
            )

    def _update_size(self) -> None:
        """Update the size statistic."""
        self._stats.size = len(self._cache)

    @property
    def size(self) -> int:
        """Get the current number of entries in the cache."""
        with self._lock:
            return len(self._cache)
