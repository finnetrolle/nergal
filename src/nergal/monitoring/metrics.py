"""Prometheus metrics for monitoring the bot."""

import asyncio
import functools
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from threading import Thread
from typing import Any, Callable, ParamSpec, TypeVar

import psutil
from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

# =============================================================================
# Message Metrics
# =============================================================================

bot_messages_total = Counter(
    "bot_messages_total",
    "Total number of messages processed",
    ["status", "agent_type"],
)

bot_message_duration_seconds = Histogram(
    "bot_message_duration_seconds",
    "Time spent processing messages",
    ["agent_type"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

bot_errors_total = Counter(
    "bot_errors_total",
    "Total number of errors",
    ["error_type", "component"],
)

bot_active_users = Gauge(
    "bot_active_users",
    "Number of unique users in the last hour",
)

# =============================================================================
# LLM Metrics
# =============================================================================

bot_llm_requests_total = Counter(
    "bot_llm_requests_total",
    "Total number of LLM API requests",
    ["provider", "model", "status"],
)

bot_llm_request_duration_seconds = Histogram(
    "bot_llm_request_duration_seconds",
    "Time spent on LLM API requests",
    ["provider", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0],
)

bot_llm_tokens_total = Counter(
    "bot_llm_tokens_total",
    "Total number of tokens processed",
    ["provider", "model", "type"],  # type: prompt, completion
)

# =============================================================================
# Web Search Metrics
# =============================================================================

bot_web_search_requests_total = Counter(
    "bot_web_search_requests_total",
    "Total number of web search requests",
    ["status"],
)

bot_web_search_duration_seconds = Histogram(
    "bot_web_search_duration_seconds",
    "Time spent on web search requests",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0],
)

# Enhanced web search metrics
bot_web_search_retries_total = Counter(
    "bot_web_search_retries_total",
    "Total number of search retry attempts",
    ["reason"],  # Error category that triggered retry
)

bot_web_search_circuit_breaker_state = Gauge(
    "bot_web_search_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
)

bot_web_search_query_generation_duration_seconds = Histogram(
    "bot_web_search_query_generation_duration_seconds",
    "Time spent generating search queries",
    ["method"],  # llm or fallback
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

bot_web_search_synthesis_duration_seconds = Histogram(
    "bot_web_search_synthesis_duration_seconds",
    "Time spent synthesizing search results into response",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
)

bot_web_search_results_per_query = Histogram(
    "bot_web_search_results_per_query",
    "Number of results returned per search query",
    buckets=[0, 1, 2, 3, 5, 10, 20, 50],
)

bot_web_search_queries_per_request = Histogram(
    "bot_web_search_queries_per_request",
    "Number of search queries generated per user request",
    buckets=[1, 2, 3, 4, 5],
)

bot_web_search_errors_by_category = Counter(
    "bot_web_search_errors_by_category_total",
    "Web search errors categorized by type",
    ["category"],  # transient, auth, quota, service_error, etc.
)

# =============================================================================
# STT Metrics
# =============================================================================

bot_stt_requests_total = Counter(
    "bot_stt_requests_total",
    "Total number of STT (speech-to-text) requests",
    ["provider", "status"],
)

bot_stt_duration_seconds = Histogram(
    "bot_stt_duration_seconds",
    "Time spent on STT processing",
    ["provider"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

bot_stt_audio_duration_seconds = Histogram(
    "bot_stt_audio_duration_seconds",
    "Duration of processed audio in seconds",
    ["provider"],
    buckets=[5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 90.0, 120.0],
)

# =============================================================================
# System Metrics
# =============================================================================

system_cpu_percent = Gauge(
    "system_cpu_percent",
    "System CPU usage percentage",
)

system_memory_percent = Gauge(
    "system_memory_percent",
    "System memory usage percentage",
)

system_disk_percent = Gauge(
    "system_disk_percent",
    "System disk usage percentage",
    ["path"],
)

# =============================================================================
# Active Users Tracking
# =============================================================================

_user_activity: dict[int, float] = defaultdict(float)


def track_user_activity(user_id: int) -> None:
    """Track user activity for active users gauge."""
    _user_activity[user_id] = time.time()
    _update_active_users_gauge()


def _update_active_users_gauge() -> None:
    """Update the active users gauge based on recent activity."""
    current_time = time.time()
    one_hour_ago = current_time - 3600

    # Count users active in the last hour
    active_count = sum(1 for last_seen in _user_activity.values() if last_seen > one_hour_ago)
    bot_active_users.set(active_count)

    # Clean up old entries periodically
    if len(_user_activity) > 10000:
        for uid in list(_user_activity.keys()):
            if _user_activity[uid] < one_hour_ago:
                del _user_activity[uid]


# =============================================================================
# Decorators and Context Managers
# =============================================================================

P = ParamSpec("P")
R = TypeVar("R")


def track_message(agent_type: str = "default") -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to track message processing metrics.

    Args:
        agent_type: The type of agent processing the message.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)  # type: ignore
                return result
            except Exception as e:
                status = "error"
                track_error(type(e).__name__, "message_handler")
                raise
            finally:
                duration = time.time() - start_time
                bot_messages_total.labels(status=status, agent_type=agent_type).inc()
                bot_message_duration_seconds.labels(agent_type=agent_type).observe(duration)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                track_error(type(e).__name__, "message_handler")
                raise
            finally:
                duration = time.time() - start_time
                bot_messages_total.labels(status=status, agent_type=agent_type).inc()
                bot_message_duration_seconds.labels(agent_type=agent_type).observe(duration)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper

    return decorator


@asynccontextmanager
async def track_llm_request(provider: str, model: str):
    """Context manager to track LLM request metrics.

    Args:
        provider: The LLM provider name.
        model: The model identifier.

    Yields:
        None.
    """
    start_time = time.time()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        bot_llm_requests_total.labels(provider=provider, model=model, status=status).inc()
        bot_llm_request_duration_seconds.labels(provider=provider, model=model).observe(duration)


@asynccontextmanager
async def track_web_search():
    """Context manager to track web search metrics.

    Yields:
        None.
    """
    start_time = time.time()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        bot_web_search_requests_total.labels(status=status).inc()
        bot_web_search_duration_seconds.observe(duration)


@asynccontextmanager
async def track_stt_request(provider: str, audio_duration: float | None = None):
    """Context manager to track STT request metrics.

    Args:
        provider: The STT provider name.
        audio_duration: Optional audio duration in seconds.

    Yields:
        None.
    """
    start_time = time.time()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        bot_stt_requests_total.labels(provider=provider, status=status).inc()
        bot_stt_duration_seconds.labels(provider=provider).observe(duration)
        if audio_duration is not None:
            bot_stt_audio_duration_seconds.labels(provider=provider).observe(audio_duration)


def track_error(error_type: str, component: str) -> None:
    """Track an error in metrics.

    Args:
        error_type: The type/class name of the error.
        component: The component where the error occurred.
    """
    bot_errors_total.labels(error_type=error_type, component=component).inc()


def track_tokens(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    """Track token usage.

    Args:
        provider: The LLM provider name.
        model: The model identifier.
        prompt_tokens: Number of prompt tokens.
        completion_tokens: Number of completion tokens.
    """
    bot_llm_tokens_total.labels(provider=provider, model=model, type="prompt").inc(prompt_tokens)
    bot_llm_tokens_total.labels(provider=provider, model=model, type="completion").inc(completion_tokens)


def update_system_metrics() -> None:
    """Update system resource metrics."""
    try:
        system_cpu_percent.set(psutil.cpu_percent(interval=0.1))
        system_memory_percent.set(psutil.virtual_memory().percent)

        # Track disk usage for root partition
        root_usage = psutil.disk_usage("/")
        system_disk_percent.labels(path="/").set(root_usage.percent)
    except Exception as e:
        logger.warning(f"Failed to update system metrics: {e}")


class MetricsServer:
    """Server for exposing Prometheus metrics."""

    def __init__(self, port: int = 8000) -> None:
        """Initialize the metrics server.

        Args:
            port: The port to expose metrics on.
        """
        self.port = port
        self._running = False
        self._thread: Thread | None = None
        self._system_metrics_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start the metrics server in a background thread."""
        if self._running:
            logger.warning("Metrics server is already running")
            return

        def run_server() -> None:
            try:
                start_http_server(self.port)
                logger.info(f"Metrics server started on port {self.port}")
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")

        self._thread = Thread(target=run_server, daemon=True)
        self._thread.start()
        self._running = True

        # Start system metrics update task
        self._start_system_metrics_updater()

    def _start_system_metrics_updater(self) -> None:
        """Start periodic system metrics updates."""

        async def update_loop() -> None:
            while self._running:
                update_system_metrics()
                await asyncio.sleep(15)  # Update every 15 seconds

        try:
            loop = asyncio.get_event_loop()
            self._system_metrics_task = loop.create_task(update_loop())
        except RuntimeError:
            # No event loop running, will be started later
            pass

    def stop(self) -> None:
        """Stop the metrics server."""
        self._running = False
        if self._system_metrics_task:
            self._system_metrics_task.cancel()
        logger.info("Metrics server stopped")
