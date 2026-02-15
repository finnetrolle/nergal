"""Structured logging configuration using structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def add_app_context(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries.

    Args:
        logger: The wrapped logger object.
        method_name: The name of the wrapped method (e.g. 'info', 'debug').
        event_dict: The event dictionary.

    Returns:
        Modified event dictionary.
    """
    # Add service name
    event_dict["service"] = "nergal-bot"
    return event_dict


def drop_color_message_key(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Remove color_message key if present (for JSON output).

    Args:
        logger: The wrapped logger object.
        method_name: The name of the wrapped method.
        event_dict: The event dictionary.

    Returns:
        Modified event dictionary.
    """
    event_dict.pop("color_message", None)
    return event_dict


def get_processors(json_output: bool = True) -> list[Processor]:
    """Get the list of processors for structlog.

    Args:
        json_output: Whether to use JSON output format.

    Returns:
        List of processors.
    """
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
    ]

    if json_output:
        processors.extend([
            drop_color_message_key,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ])
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    return processors


def configure_logging(
    log_level: str = "INFO",
    json_output: bool = True,
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: The logging level to use.
        json_output: Whether to use JSON output format (recommended for production).
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Set log level
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level_value)

    # Configure structlog
    structlog.configure(
        processors=get_processors(json_output=json_output),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Suppress verbose HTTP logs
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Optional logger name. If None, uses the calling module's name.

    Returns:
        A bound structlog logger.
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding temporary context to logs."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize with context key-value pairs.

        Args:
            **kwargs: Key-value pairs to add to log context.
        """
        self._kwargs = kwargs
        self._token: Any = None

    def __enter__(self) -> "LogContext":
        """Enter the context and bind the values."""
        self._token = structlog.contextvars.bind_contextvars(**self._kwargs)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context and unbind the values."""
        if self._token:
            structlog.contextvars.unbind_contextvars(*self._kwargs.keys())


def bind_context(**kwargs: Any) -> None:
    """Bind values to the logging context permanently.

    Args:
        **kwargs: Key-value pairs to add to log context.
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """Remove values from the logging context.

    Args:
        *keys: Keys to remove from log context.
    """
    structlog.contextvars.unbind_contextvars(*keys)
