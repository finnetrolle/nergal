"""Reliability components for web search providers.

This module provides retry logic, circuit breaker pattern, and error classification
to improve the reliability of web search operations.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from nergal.web_search.base import SearchError

logger = logging.getLogger(__name__)


class SearchErrorCategory(Enum):
    """Classification of search errors for handling decisions."""

    TRANSIENT = "transient"  # Network issues, timeouts - should retry
    AUTHENTICATION = "auth"  # API key issues - alert immediately, no retry
    QUOTA = "quota"  # Rate limits - back off, retry with delay
    INVALID_REQUEST = "bad_request"  # Bad query - don't retry
    SERVICE_ERROR = "service"  # 5xx errors - retry with backoff
    INVALID_RESPONSE = "response"  # Parse errors - log for debugging
    UNKNOWN = "unknown"  # Unclassified errors


@dataclass
class ClassifiedError:
    """Result of error classification with handling guidance."""

    category: SearchErrorCategory
    original_error: Exception
    should_retry: bool
    alert_severity: str  # "critical", "warning", "info"
    suggested_action: str
    retry_delay_ms: int | None = None


def classify_search_error(error: Exception) -> ClassifiedError:
    """Classify a search error to determine handling strategy.

    Args:
        error: The exception that occurred during search.

    Returns:
        ClassifiedError with handling guidance.
    """
    error_name = type(error).__name__
    error_str = str(error).lower()

    # Authentication errors (401, 403)
    if "401" in error_str or "403" in error_str or "unauthorized" in error_str:
        return ClassifiedError(
            category=SearchErrorCategory.AUTHENTICATION,
            original_error=error,
            should_retry=False,
            alert_severity="critical",
            suggested_action="Check API key configuration",
        )

    # Rate limiting (429)
    if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
        return ClassifiedError(
            category=SearchErrorCategory.QUOTA,
            original_error=error,
            should_retry=True,
            alert_severity="warning",
            suggested_action="Implement backoff or upgrade API plan",
            retry_delay_ms=5000,  # Wait longer for rate limits
        )

    # Service errors (500, 502, 503, 504)
    if any(code in error_str for code in ["500", "502", "503", "504"]) or \
       "service unavailable" in error_str or "internal server error" in error_str:
        return ClassifiedError(
            category=SearchErrorCategory.SERVICE_ERROR,
            original_error=error,
            should_retry=True,
            alert_severity="warning",
            suggested_action="Provider service issue, will auto-retry",
        )

    # Timeout errors
    if "timeout" in error_name.lower() or "timeout" in error_str:
        return ClassifiedError(
            category=SearchErrorCategory.TRANSIENT,
            original_error=error,
            should_retry=True,
            alert_severity="info",
            suggested_action="Network timeout, will retry",
        )

    # Connection errors
    if "connection" in error_name.lower() or "connection" in error_str or \
       "network" in error_str:
        return ClassifiedError(
            category=SearchErrorCategory.TRANSIENT,
            original_error=error,
            should_retry=True,
            alert_severity="info",
            suggested_action="Network issue, will retry",
        )

    # Invalid request (400)
    if "400" in error_str or "bad request" in error_str or "invalid" in error_str:
        return ClassifiedError(
            category=SearchErrorCategory.INVALID_REQUEST,
            original_error=error,
            should_retry=False,
            alert_severity="warning",
            suggested_action="Invalid search request, check query format",
        )

    # Parse/response errors
    if "json" in error_str or "parse" in error_str or "decode" in error_str:
        return ClassifiedError(
            category=SearchErrorCategory.INVALID_RESPONSE,
            original_error=error,
            should_retry=False,
            alert_severity="warning",
            suggested_action="Failed to parse API response",
        )

    # Default to unknown
    return ClassifiedError(
        category=SearchErrorCategory.UNKNOWN,
        original_error=error,
        should_retry=False,
        alert_severity="warning",
        suggested_action="Investigate error details",
    )


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failing, reject all requests
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.

    Implements the circuit breaker pattern:
    - CLOSED: Normal operation, track failures
    - OPEN: After threshold failures, reject all requests
    - HALF_OPEN: After timeout, allow test requests

    Attributes:
        failure_threshold: Number of failures before opening circuit.
        recovery_timeout_seconds: Time to wait before attempting recovery.
        success_threshold: Successes needed in half-open to close circuit.
    """

    failure_threshold: int = 5
    recovery_timeout_seconds: int = 30
    success_threshold: int = 3

    _state: CircuitState = field(default=CircuitState.CLOSED, repr=False)
    _failure_count: int = field(default=0, repr=False)
    _success_count: int = field(default=0, repr=False)
    _last_failure_time: datetime | None = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state

    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            self._failure_count = 0

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._reset()
                    logger.info("Circuit breaker closed after successful recovery")

    def record_failure(self) -> None:
        """Record a failed request."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            self._success_count = 0  # Reset success count on failure

            if self._state == CircuitState.HALF_OPEN:
                # Failure during recovery, back to open
                self._state = CircuitState.OPEN
                logger.warning("Circuit breaker reopened during recovery")
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker opened after {self._failure_count} failures"
                )

    def should_allow_request(self) -> bool:
        """Check if a request should be allowed.

        Returns:
            True if request should proceed, False if circuit is open.
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._last_failure_time:
                    elapsed = datetime.now() - self._last_failure_time
                    if elapsed > timedelta(seconds=self.recovery_timeout_seconds):
                        self._state = CircuitState.HALF_OPEN
                        self._success_count = 0
                        logger.info("Circuit breaker entering half-open state")
                        return True
                return False

            # HALF_OPEN allows limited requests
            return True

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._reset()
            logger.info("Circuit breaker manually reset")

    def _reset(self) -> None:
        """Internal reset without lock (caller must hold lock)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None

    def get_state_value(self) -> int:
        """Get numeric state value for Prometheus metric.

        Returns:
            0 for CLOSED, 1 for HALF_OPEN, 2 for OPEN.
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return 0
            elif self._state == CircuitState.HALF_OPEN:
                return 1
            else:
                return 2


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts.
        base_delay_ms: Initial delay between retries in milliseconds.
        max_delay_ms: Maximum delay between retries in milliseconds.
        jitter_ms: Random jitter to add to delays (prevides thundering herd).
        retryable_categories: Error categories that should trigger retry.
    """

    max_retries: int = 3
    base_delay_ms: int = 500
    max_delay_ms: int = 10000
    jitter_ms: int = 100
    retryable_categories: set[SearchErrorCategory] = field(
        default_factory=lambda: {
            SearchErrorCategory.TRANSIENT,
            SearchErrorCategory.SERVICE_ERROR,
            SearchErrorCategory.QUOTA,
        }
    )


@dataclass
class RetryStats:
    """Statistics from retry attempts."""

    attempts: int = 0
    total_delay_ms: int = 0
    retry_reasons: list[str] = field(default_factory=list)
    final_success: bool = False


async def execute_with_retry(
    operation: Any,  # Callable[[], Awaitable[T]]
    config: RetryConfig,
    circuit_breaker: CircuitBreaker | None = None,
    operation_name: str = "operation",
) -> tuple[Any, RetryStats]:  # tuple[T, RetryStats]
    """Execute an async operation with retry logic.

    Args:
        operation: Async callable to execute.
        config: Retry configuration.
        circuit_breaker: Optional circuit breaker to check.
        operation_name: Name for logging.

    Returns:
        Tuple of (result, retry_stats).

    Raises:
        Exception: The last exception if all retries fail.
        SearchError: If circuit breaker is open.
    """
    stats = RetryStats()
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.should_allow_request():
            raise SearchError(
                f"Circuit breaker is open for {operation_name}",
                provider=operation_name,
            )

        stats.attempts = attempt + 1

        try:
            result = await operation()
            stats.final_success = True

            if circuit_breaker:
                circuit_breaker.record_success()

            if attempt > 0:
                logger.info(
                    f"{operation_name} succeeded after {attempt} retries"
                )

            return result, stats

        except Exception as e:
            last_error = e

            # Classify the error
            classified = classify_search_error(e)
            stats.retry_reasons.append(classified.category.value)

            # Log the error
            log_level = logging.WARNING if attempt < config.max_retries else logging.ERROR
            logger.log(
                log_level,
                f"{operation_name} attempt {attempt + 1} failed: "
                f"{type(e).__name__}: {e}",
            )

            # Check if we should retry
            if attempt >= config.max_retries:
                logger.error(
                    f"{operation_name} failed after {config.max_retries + 1} attempts"
                )
                break

            if classified.category not in config.retryable_categories:
                logger.error(
                    f"{operation_name} failed with non-retryable error: "
                    f"{classified.category.value}"
                )
                break

            # Record failure in circuit breaker
            if circuit_breaker:
                circuit_breaker.record_failure()

            # Calculate delay with exponential backoff and jitter
            import random
            base_delay = min(
                config.base_delay_ms * (2 ** attempt),
                config.max_delay_ms,
            )
            jitter = random.randint(0, config.jitter_ms)
            delay_ms = base_delay + jitter

            # Use classified error's suggested delay if higher (e.g., for rate limits)
            if classified.retry_delay_ms and classified.retry_delay_ms > delay_ms:
                delay_ms = classified.retry_delay_ms

            stats.total_delay_ms += delay_ms

            logger.info(
                f"{operation_name} retrying in {delay_ms}ms "
                f"(attempt {attempt + 2}/{config.max_retries + 1})"
            )

            await asyncio.sleep(delay_ms / 1000)

    # All retries exhausted or non-retryable error
    if circuit_breaker:
        circuit_breaker.record_failure()

    raise last_error
