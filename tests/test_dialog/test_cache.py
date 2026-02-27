"""Tests for agent result caching module."""

import time

import pytest

from nergal.dialog.base import AgentResult, AgentType
from nergal.dialog.cache import AgentResultCache, CacheEntry, CacheStats


@pytest.fixture
def cache() -> AgentResultCache:
    """Create a cache instance for testing."""
    return AgentResultCache(
        enabled=True,
        ttl_seconds=2,  # Short TTL for testing
        max_size=5,  # Small size for testing LRU
    )


@pytest.fixture
def sample_result() -> AgentResult:
    """Create a sample agent result for testing."""
    return AgentResult(
        response="Test response",
        agent_type=AgentType.DEFAULT,
        confidence=0.9,
        metadata={"key": "value"},
    )


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_creation(self) -> None:
        """Test creating a cache entry."""
        result = AgentResult(
            response="test",
            agent_type=AgentType.DEFAULT,
        )
        current_time = time.time()
        entry = CacheEntry(
            result=result,
            created_at=current_time,
            expires_at=current_time + 300,
        )

        assert entry.result == result
        assert entry.created_at == current_time
        assert entry.hits == 0

    def test_cache_entry_hits_increment(self) -> None:
        """Test incrementing hits on cache entry."""
        result = AgentResult(
            response="test",
            agent_type=AgentType.DEFAULT,
        )
        entry = CacheEntry(
            result=result,
            created_at=time.time(),
            expires_at=time.time() + 300,
        )

        entry.hits += 1
        assert entry.hits == 1


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_cache_stats_defaults(self) -> None:
        """Test default cache stats values."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.size == 0
        assert stats.max_size == 0

    @pytest.mark.parametrize("hits,misses,expected_hit_rate", [
        (0, 0, 0.0),
        (10, 0, 1.0),
        (0, 10, 0.0),
        (7, 3, 0.7),
    ])
    def test_hit_rate(self, hits, misses, expected_hit_rate) -> None:
        """Test hit rate calculation (parametrized)."""
        stats = CacheStats(hits=hits, misses=misses)

        assert stats.hit_rate == expected_hit_rate


class TestAgentResultCache:
    """Tests for AgentResultCache class."""

    def test_cache_disabled(self, sample_result: AgentResult) -> None:
        """Test that disabled cache returns None on get."""
        cache = AgentResultCache(enabled=False)

        # Set should be no-op
        cache.set(AgentType.DEFAULT, "test message", sample_result)

        # Get should return None
        result = cache.get(AgentType.DEFAULT, "test message")
        assert result is None

        # Stats should still be zero
        stats = cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0

    def test_cache_set_and_get(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test basic set and get operations."""
        cache.set(AgentType.DEFAULT, "test message", sample_result)

        result = cache.get(AgentType.DEFAULT, "test message")

        assert result is not None
        assert result.response == sample_result.response
        assert result.agent_type == sample_result.agent_type

    def test_cache_hit_increments_stats(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test that cache hit increments hit counter."""
        cache.set(AgentType.DEFAULT, "test message", sample_result)

        cache.get(AgentType.DEFAULT, "test message")
        stats = cache.get_stats()

        assert stats.hits == 1
        assert stats.misses == 0

    def test_cache_miss_increments_stats(self, cache: AgentResultCache) -> None:
        """Test that cache miss increments miss counter."""
        cache.get(AgentType.DEFAULT, "non-existent")

        stats = cache.get_stats()

        assert stats.hits == 0
        assert stats.misses == 1

    def test_cache_key_normalization(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test that cache keys are normalized (case, whitespace)."""
        cache.set(AgentType.DEFAULT, "Test Message", sample_result)

        # Should find with different case
        result = cache.get(AgentType.DEFAULT, "test message")
        assert result is not None

        # Should find with extra whitespace
        result = cache.get(AgentType.DEFAULT, "  Test Message  ")
        assert result is not None

    def test_cache_different_agents(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test that different agent types have separate cache entries."""
        web_result = AgentResult(
            response="Web response",
            agent_type=AgentType.WEB_SEARCH,
        )

        cache.set(AgentType.DEFAULT, "test message", sample_result)
        cache.set(AgentType.WEB_SEARCH, "test message", web_result)

        default_result = cache.get(AgentType.DEFAULT, "test message")
        web_result = cache.get(AgentType.WEB_SEARCH, "test message")

        assert default_result is not None
        assert web_result is not None
        assert default_result.agent_type == AgentType.DEFAULT
        assert web_result.agent_type == AgentType.WEB_SEARCH

    def test_cache_ttl_expiry(
        self, sample_result: AgentResult
    ) -> None:
        """Test that cache entries expire after TTL."""
        cache = AgentResultCache(enabled=True, ttl_seconds=1, max_size=10)

        cache.set(AgentType.DEFAULT, "test message", sample_result)

        # Should be present immediately
        result = cache.get(AgentType.DEFAULT, "test message")
        assert result is not None

        # Wait for TTL to expire
        time.sleep(1.5)

        # Should be expired now
        result = cache.get(AgentType.DEFAULT, "test message")
        assert result is None

        # Miss should be counted
        stats = cache.get_stats()
        assert stats.misses == 1
        assert stats.evictions == 1

    def test_cache_lru_eviction(self) -> None:
        """Test LRU eviction when cache is full."""
        cache = AgentResultCache(enabled=True, ttl_seconds=300, max_size=3)

        # Add 3 entries
        for i in range(3):
            result = AgentResult(
                response=f"Response {i}",
                agent_type=AgentType.DEFAULT,
            )
            cache.set(AgentType.DEFAULT, f"message {i}", result)

        # Access first entry to make it recently used
        cache.get(AgentType.DEFAULT, "message 0")

        # Add 4th entry - should evict message 1 (LRU)
        new_result = AgentResult(
            response="New response",
            agent_type=AgentType.DEFAULT,
        )
        cache.set(AgentType.DEFAULT, "message 3", new_result)

        # message 0 should still exist (recently accessed)
        result = cache.get(AgentType.DEFAULT, "message 0")
        assert result is not None

        # message 1 should be evicted
        result = cache.get(AgentType.DEFAULT, "message 1")
        assert result is None

        # Check eviction count
        stats = cache.get_stats()
        assert stats.evictions == 1

    def test_cache_invalidate_specific(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test invalidating a specific cache entry."""
        cache.set(AgentType.DEFAULT, "message 1", sample_result)
        cache.set(AgentType.DEFAULT, "message 2", sample_result)

        # Invalidate first message
        invalidated = cache.invalidate(AgentType.DEFAULT, "message 1")
        assert invalidated is True

        # First message should be gone
        result = cache.get(AgentType.DEFAULT, "message 1")
        assert result is None

        # Second message should still exist
        result = cache.get(AgentType.DEFAULT, "message 2")
        assert result is not None

    def test_cache_invalidate_non_existent(self, cache: AgentResultCache) -> None:
        """Test invalidating a non-existent entry."""
        invalidated = cache.invalidate(AgentType.DEFAULT, "non-existent")
        assert invalidated is False

    def test_cache_invalidate_agent(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test invalidating all entries for a specific agent type."""
        web_result = AgentResult(
            response="Web response",
            agent_type=AgentType.WEB_SEARCH,
        )

        # Add entries for multiple agents
        cache.set(AgentType.DEFAULT, "message 1", sample_result)
        cache.set(AgentType.DEFAULT, "message 2", sample_result)
        cache.set(AgentType.WEB_SEARCH, "message 1", web_result)

        # Invalidate all DEFAULT entries
        removed = cache.invalidate_agent(AgentType.DEFAULT)
        assert removed == 2

        # DEFAULT entries should be gone
        result = cache.get(AgentType.DEFAULT, "message 1")
        assert result is None
        result = cache.get(AgentType.DEFAULT, "message 2")
        assert result is None

        # WEB_SEARCH entry should still exist
        result = cache.get(AgentType.WEB_SEARCH, "message 1")
        assert result is not None

    def test_cache_clear(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test clearing all cache entries."""
        cache.set(AgentType.DEFAULT, "message 1", sample_result)
        cache.set(AgentType.DEFAULT, "message 2", sample_result)

        cleared = cache.clear()
        assert cleared == 2

        # All entries should be gone
        assert cache.size == 0
        result = cache.get(AgentType.DEFAULT, "message 1")
        assert result is None

    def test_cache_cleanup_expired(self) -> None:
        """Test cleanup of expired entries."""
        cache = AgentResultCache(enabled=True, ttl_seconds=1, max_size=10)

        result = AgentResult(
            response="Test",
            agent_type=AgentType.DEFAULT,
        )

        # Add entries
        cache.set(AgentType.DEFAULT, "message 1", result)
        cache.set(AgentType.DEFAULT, "message 2", result)

        # Wait for expiry
        time.sleep(1.5)

        # Add a fresh entry
        cache.set(AgentType.DEFAULT, "message 3", result)

        # Cleanup expired
        removed = cache.cleanup_expired()
        assert removed == 2

        # Only fresh entry should remain
        assert cache.size == 1

    def test_cache_with_context_kwargs(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test that cache key includes context kwargs."""
        # Set with context
        cache.set(
            AgentType.DEFAULT,
            "test message",
            sample_result,
            user_id=123,
            language="en",
        )

        # Get without context - should not find
        result = cache.get(AgentType.DEFAULT, "test message")
        assert result is None

        # Get with same context - should find
        result = cache.get(
            AgentType.DEFAULT,
            "test message",
            user_id=123,
            language="en",
        )
        assert result is not None

    def test_cache_update_existing_entry(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test updating an existing cache entry."""
        cache.set(AgentType.DEFAULT, "test message", sample_result)

        # Update with new result
        new_result = AgentResult(
            response="Updated response",
            agent_type=AgentType.DEFAULT,
            confidence=0.5,
        )
        cache.set(AgentType.DEFAULT, "test message", new_result)

        # Should get updated result
        result = cache.get(AgentType.DEFAULT, "test message")
        assert result is not None
        assert result.response == "Updated response"
        assert result.confidence == 0.5

        # Size should still be 1
        assert cache.size == 1

    def test_cache_size_property(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test the size property."""
        assert cache.size == 0

        cache.set(AgentType.DEFAULT, "message 1", sample_result)
        assert cache.size == 1

        cache.set(AgentType.DEFAULT, "message 2", sample_result)
        assert cache.size == 2

        cache.clear()
        assert cache.size == 0

    def test_cache_stats_reflects_current_state(
        self, cache: AgentResultCache, sample_result: AgentResult
    ) -> None:
        """Test that stats accurately reflect cache state."""
        # Initial state
        stats = cache.get_stats()
        assert stats.size == 0
        assert stats.max_size == 5

        # Add entries and access
        cache.set(AgentType.DEFAULT, "message 1", sample_result)
        cache.set(AgentType.DEFAULT, "message 2", sample_result)
        cache.get(AgentType.DEFAULT, "message 1")  # hit
        cache.get(AgentType.DEFAULT, "non-existent")  # miss

        stats = cache.get_stats()
        assert stats.size == 2
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == 0.5

    def test_cache_disabled_operations(
        self, sample_result: AgentResult
    ) -> None:
        """Test that disabled cache handles all operations gracefully."""
        cache = AgentResultCache(enabled=False)

        # All operations should be no-ops or return None/0
        cache.set(AgentType.DEFAULT, "test", sample_result)
        assert cache.get(AgentType.DEFAULT, "test") is None
        assert cache.invalidate(AgentType.DEFAULT, "test") is False
        assert cache.invalidate_agent(AgentType.DEFAULT) == 0
        assert cache.cleanup_expired() == 0

        # Clear still works
        assert cache.clear() == 0


class TestAgentResultCacheThreadSafety:
    """Tests for thread safety of AgentResultCache."""

    def test_concurrent_access(self, sample_result: AgentResult) -> None:
        """Test concurrent read/write operations."""
        import concurrent.futures

        cache = AgentResultCache(enabled=True, ttl_seconds=300, max_size=100)

        def write_entries(start: int) -> int:
            for i in range(start, start + 10):
                result = AgentResult(
                    response=f"Response {i}",
                    agent_type=AgentType.DEFAULT,
                )
                cache.set(AgentType.DEFAULT, f"message {i}", result)
            return 10

        def read_entries(start: int) -> int:
            hits = 0
            for i in range(start, start + 10):
                result = cache.get(AgentType.DEFAULT, f"message {i}")
                if result is not None:
                    hits += 1
            return hits

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Submit write tasks
            write_futures = [executor.submit(write_entries, i * 10) for i in range(2)]
            # Submit read tasks
            read_futures = [executor.submit(read_entries, i * 10) for i in range(2)]

            # Wait for completion
            for future in concurrent.futures.as_completed(write_futures):
                assert future.result() == 10

            # Reads may have varying hit counts due to timing
            for future in concurrent.futures.as_completed(read_futures):
                future.result()  # Just ensure no exceptions

        # Cache should be in a consistent state
        assert cache.size <= 100  # max_size
