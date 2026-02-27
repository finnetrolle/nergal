"""Tests for web_search reliability components."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nergal.web_search.reliability import (
    SearchErrorCategory,
    ClassifiedError,
    classify_search_error,
    RetryConfig,
    RetryStats,
    CircuitBreaker,
    CircuitState,
    execute_with_retry,
)
from nergal.exceptions import SearchError


class TestSearchErrorCategory:
    """Tests for SearchErrorCategory enum."""

    def test_all_categories_defined(self) -> None:
        """Test that all error categories are defined."""
        assert SearchErrorCategory.TRANSIENT.value == "transient"
        assert SearchErrorCategory.AUTHENTICATION.value == "auth"
        assert SearchErrorCategory.QUOTA.value == "quota"
        assert SearchErrorCategory.INVALID_REQUEST.value == "bad_request"
        assert SearchErrorCategory.SERVICE_ERROR.value == "service"
        assert SearchErrorCategory.INVALID_RESPONSE.value == "response"
        assert SearchErrorCategory.UNKNOWN.value == "unknown"


class TestClassifySearchError:
    """Tests for error classification."""

    def test_classify_401_error(self) -> None:
        """Test classification of 401 authentication errors."""
        error = Exception("401 Unauthorized")
        classified = classify_search_error(error)
        assert classified.category == SearchErrorCategory.AUTHENTICATION
        assert classified.should_retry is False
        assert classified.alert_severity == "critical"

    def test_classify_403_error(self) -> None:
        """Test classification of 403 forbidden errors."""
        error = Exception("403 Forbidden")
        classified = classify_search_error(error)
        assert classified.category == SearchErrorCategory.AUTHENTICATION
        assert classified.should_retry is False

    def test_classify_429_rate_limit(self) -> None:
        """Test classification of 429 rate limit errors."""
        error = Exception("429 Too Many Requests")
        classified = classify_search_error(error)
        assert classified.category == SearchErrorCategory.QUOTA
        assert classified.should_retry is True
        assert classified.retry_delay_ms == 5000

    def test_classify_rate_limit_text(self) -> None:
        """Test classification of rate limit by text."""
        error = Exception("Rate limit exceeded")
        classified = classify_search_error(error)
        assert classified.category == SearchErrorCategory.QUOTA
        assert classified.should_retry is True

    def test_classify_500_error(self) -> None:
        """Test classification of 500 server errors."""
        error = Exception("500 Internal Server Error")
        classified = classify_search_error(error)
        assert classified.category == SearchErrorCategory.SERVICE_ERROR
        assert classified.should_retry is True

    def test_classify_503_error(self) -> None:
        """Test classification of 503 service unavailable."""
        error = Exception("503 Service Unavailable")
        classified = classify_search_error(error)
        assert classified.category == SearchErrorCategory.SERVICE_ERROR
        assert classified.should_retry is True

    def test_classify_timeout_error(self) -> None:
        """Test classification of timeout errors."""
        error = TimeoutError("Connection timed out")
        classified = classify_search_error(error)
        assert classified.category == SearchErrorCategory.TRANSIENT
        assert classified.should_retry is True
        assert classified.alert_severity == "info"

    def test_classify_connection_error(self) -> None:
        """Test classification of connection errors."""
        error = ConnectionError("Failed to connect")
        classified = classify_search_error(error)
        assert classified.category == SearchErrorCategory.TRANSIENT
        assert classified.should_retry is True

    def test_classify_unknown_error(self) -> None:
        """Test classification of unknown errors."""
        error = ValueError("Some unknown error")
        classified = classify_search_error(error)
        assert classified.category == SearchErrorCategory.UNKNOWN
        assert classified.should_retry is False


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_config(self) -> None:
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay_ms == 500
        assert config.max_delay_ms == 10000
        assert config.jitter_ms == 100

    def test_custom_config(self) -> None:
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay_ms=1000,
            max_delay_ms=30000,
            jitter_ms=200,
        )
        assert config.max_retries == 5
        assert config.base_delay_ms == 1000
        assert config.max_delay_ms == 30000
        assert config.jitter_ms == 200


class TestRetryStats:
    """Tests for RetryStats."""

    def test_initial_stats(self) -> None:
        """Test initial retry stats."""
        stats = RetryStats()
        assert stats.attempts == 0
        assert stats.total_delay_ms == 0
        assert stats.retry_reasons == []
        assert stats.final_success is False


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state(self) -> None:
        """Test initial circuit breaker state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_record_success(self) -> None:
        """Test recording success."""
        cb = CircuitBreaker()
        cb.record_failure()  # Add a failure first
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_record_failure_opens_circuit(self) -> None:
        """Test that failures open the circuit."""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_should_allow_request_closed(self) -> None:
        """Test should_allow_request when circuit is closed."""
        cb = CircuitBreaker()
        assert cb.should_allow_request() is True

    def test_should_allow_request_open(self) -> None:
        """Test should_allow_request when circuit is open."""
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.should_allow_request() is False

    def test_half_open_after_timeout(self) -> None:
        """Test transition to half-open after timeout."""
        import time
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=0.1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # Wait for recovery timeout
        time.sleep(0.15)
        assert cb.should_allow_request() is True
        assert cb.state == CircuitState.HALF_OPEN


class TestExecuteWithRetry:
    """Tests for execute_with_retry function."""

    @pytest.mark.asyncio
    async def test_success_first_try(self) -> None:
        """Test successful execution on first try."""
        call_count = 0

        async def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        config = RetryConfig()
        result, stats = await execute_with_retry(
            success_func,
            config=config,
        )
        assert result == "success"
        assert call_count == 1
        assert stats.final_success is True

    @pytest.mark.asyncio
    async def test_retry_then_success(self) -> None:
        """Test retry followed by success."""
        call_count = 0

        async def retry_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        config = RetryConfig(max_retries=3, base_delay_ms=10)
        result, stats = await execute_with_retry(
            retry_func,
            config=config,
        )
        assert result == "success"
        assert call_count == 3
        assert stats.final_success is True

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self) -> None:
        """Test failure after max retries."""

        async def always_fail() -> str:
            raise ConnectionError("Always fails")

        config = RetryConfig(max_retries=2, base_delay_ms=10)
        with pytest.raises(ConnectionError):
            await execute_with_retry(
                always_fail,
                config=config,
            )

    @pytest.mark.asyncio
    async def test_non_retryable_error(self) -> None:
        """Test that non-retryable errors fail immediately."""

        async def auth_fail() -> str:
            raise Exception("401 Unauthorized")

        config = RetryConfig()
        with pytest.raises(Exception, match="401"):
            await execute_with_retry(
                auth_fail,
                config=config,
            )
