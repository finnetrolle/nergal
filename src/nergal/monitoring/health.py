"""Health check module for monitoring bot status."""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with component health data.
        """
        return {
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }


class HealthChecker:
    """Health checker for the bot application."""

    def __init__(self) -> None:
        """Initialize the health checker."""
        self._components: dict[str, ComponentHealth] = {}
        self._startup_time: float | None = None

    def set_startup_time(self, startup_time: float) -> None:
        """Set the application startup time.

        Args:
            startup_time: Unix timestamp of startup.
        """
        self._startup_time = startup_time

    def update_component(self, component: ComponentHealth) -> None:
        """Update the health status of a component.

        Args:
            component: The component health status.
        """
        self._components[component.name] = component
        logger.debug(f"Health updated for {component.name}: {component.status.value}")

    def mark_healthy(self, name: str, message: str = "", details: dict[str, Any] | None = None) -> None:
        """Mark a component as healthy.

        Args:
            name: Component name.
            message: Optional status message.
            details: Optional additional details.
        """
        self.update_component(ComponentHealth(
            name=name,
            status=HealthStatus.HEALTHY,
            message=message,
            details=details or {},
        ))

    def mark_degraded(self, name: str, message: str = "", details: dict[str, Any] | None = None) -> None:
        """Mark a component as degraded (partially working).

        Args:
            name: Component name.
            message: Status message explaining the degradation.
            details: Optional additional details.
        """
        self.update_component(ComponentHealth(
            name=name,
            status=HealthStatus.DEGRADED,
            message=message,
            details=details or {},
        ))

    def mark_unhealthy(self, name: str, message: str = "", details: dict[str, Any] | None = None) -> None:
        """Mark a component as unhealthy.

        Args:
            name: Component name.
            message: Status message explaining the issue.
            details: Optional additional details.
        """
        self.update_component(ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=message,
            details=details or {},
        ))

    def get_overall_status(self) -> HealthStatus:
        """Get the overall health status.

        Returns:
            The worst status among all components.
        """
        if not self._components:
            return HealthStatus.HEALTHY

        has_degraded = False
        for component in self._components.values():
            if component.status == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY
            if component.status == HealthStatus.DEGRADED:
                has_degraded = True

        if has_degraded:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        """Convert health status to dictionary.

        Returns:
            Dictionary with full health status.
        """
        components = {name: comp.to_dict() for name, comp in self._components.items()}

        result: dict[str, Any] = {
            "status": self.get_overall_status().value,
            "components": components,
        }

        if self._startup_time:
            import time
            result["uptime_seconds"] = time.time() - self._startup_time

        return result


# Global health checker instance
_health_checker: HealthChecker | None = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance.

    Returns:
        The global HealthChecker instance.
    """
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


async def check_llm_health(llm_provider: Any) -> ComponentHealth:
    """Check LLM provider health.

    Args:
        llm_provider: The LLM provider instance.

    Returns:
        ComponentHealth for the LLM provider.
    """
    try:
        # Try a simple completion to check if the provider is working
        # This is a lightweight check - just verify the client is configured
        if hasattr(llm_provider, "_client"):
            return ComponentHealth(
                name="llm",
                status=HealthStatus.HEALTHY,
                message=f"LLM provider {llm_provider.provider_name} is configured",
                details={"provider": llm_provider.provider_name},
            )
        return ComponentHealth(
            name="llm",
            status=HealthStatus.HEALTHY,
            message=f"LLM provider {llm_provider.provider_name} ready",
            details={"provider": llm_provider.provider_name},
        )
    except Exception as e:
        return ComponentHealth(
            name="llm",
            status=HealthStatus.UNHEALTHY,
            message=f"LLM provider error: {str(e)}",
            details={"error": str(e)},
        )


async def check_telegram_health(bot_application: Any) -> ComponentHealth:
    """Check Telegram bot health.

    Args:
        bot_application: The Telegram bot application.

    Returns:
        ComponentHealth for the Telegram bot.
    """
    try:
        if hasattr(bot_application, "_dialog_manager") and bot_application._dialog_manager:
            return ComponentHealth(
                name="telegram",
                status=HealthStatus.HEALTHY,
                message="Telegram bot is running",
            )
        return ComponentHealth(
            name="telegram",
            status=HealthStatus.DEGRADED,
            message="Telegram bot initializing",
        )
    except Exception as e:
        return ComponentHealth(
            name="telegram",
            status=HealthStatus.UNHEALTHY,
            message=f"Telegram bot error: {str(e)}",
            details={"error": str(e)},
        )


async def check_web_search_health(web_search_provider: Any | None) -> ComponentHealth:
    """Check web search provider health.

    Includes circuit breaker status and recent success rate.

    Args:
        web_search_provider: The web search provider instance or None.

    Returns:
        ComponentHealth for the web search provider.
    """
    if web_search_provider is None:
        return ComponentHealth(
            name="web_search",
            status=HealthStatus.HEALTHY,
            message="Web search is disabled",
            details={"enabled": False},
        )

    try:
        details: dict[str, Any] = {"enabled": True}

        # Check circuit breaker status
        if hasattr(web_search_provider, "_circuit_breaker"):
            cb = web_search_provider._circuit_breaker
            cb_state = cb.state.value  # type: ignore
            details["circuit_breaker_state"] = cb_state

            if cb_state == "open":
                return ComponentHealth(
                    name="web_search",
                    status=HealthStatus.UNHEALTHY,
                    message="Web search circuit breaker is open - too many recent failures",
                    details=details,
                )
            elif cb_state == "half_open":
                return ComponentHealth(
                    name="web_search",
                    status=HealthStatus.DEGRADED,
                    message="Web search is recovering from failures",
                    details=details,
                )

        # Check provider name
        if hasattr(web_search_provider, "provider_name"):
            details["provider"] = web_search_provider.provider_name

        # Try to get recent telemetry for success rate
        try:
            from nergal.database.repositories import WebSearchTelemetryRepository

            repo = WebSearchTelemetryRepository()
            # This is a quick check - we don't want to block
            import asyncio

            recent = asyncio.get_event_loop().run_until_complete(repo.get_recent(limit=20))
            if recent:
                successes = sum(1 for r in recent if r.is_success())
                success_rate = successes / len(recent)
                details["recent_success_rate"] = round(success_rate, 2)

                if success_rate < 0.5:
                    return ComponentHealth(
                        name="web_search",
                        status=HealthStatus.DEGRADED,
                        message=f"Web search success rate is low ({success_rate:.0%})",
                        details=details,
                    )
        except Exception:
            # Telemetry check failed, don't fail the health check
            pass

        return ComponentHealth(
            name="web_search",
            status=HealthStatus.HEALTHY,
            message="Web search provider ready",
            details=details,
        )
    except Exception as e:
        return ComponentHealth(
            name="web_search",
            status=HealthStatus.DEGRADED,
            message=f"Web search provider error: {str(e)}",
            details={"error": str(e), "enabled": True},
        )


async def check_web_search_health_detailed(
    web_search_provider: Any | None,
    include_telemetry: bool = True,
) -> dict[str, Any]:
    """Get detailed web search health information.

    This provides more detailed health information for admin endpoints.

    Args:
        web_search_provider: The web search provider instance or None.
        include_telemetry: Whether to include telemetry statistics.

    Returns:
        Dictionary with detailed health information.
    """
    if web_search_provider is None:
        return {
            "enabled": False,
            "status": "disabled",
            "message": "Web search is not configured",
        }

    result: dict[str, Any] = {
        "enabled": True,
        "provider": getattr(web_search_provider, "provider_name", "unknown"),
    }

    # Circuit breaker info
    if hasattr(web_search_provider, "_circuit_breaker"):
        cb = web_search_provider._circuit_breaker
        result["circuit_breaker"] = {
            "state": cb.state.value,  # type: ignore
            "failure_count": cb._failure_count,
            "failure_threshold": cb.failure_threshold,
            "recovery_timeout_seconds": cb.recovery_timeout_seconds,
        }

    # Retry config
    if hasattr(web_search_provider, "_retry_config"):
        rc = web_search_provider._retry_config
        result["retry_config"] = {
            "max_retries": rc.max_retries,
            "base_delay_ms": rc.base_delay_ms,
            "max_delay_ms": rc.max_delay_ms,
        }

    # Telemetry stats
    if include_telemetry:
        try:
            from nergal.database.repositories import WebSearchTelemetryRepository

            repo = WebSearchTelemetryRepository()
            recent = await repo.get_recent(limit=100)

            if recent:
                successes = [r for r in recent if r.is_success()]
                failures = [r for r in recent if r.is_error()]

                result["telemetry"] = {
                    "recent_searches": len(recent),
                    "success_count": len(successes),
                    "failure_count": len(failures),
                    "success_rate": round(len(successes) / len(recent), 2) if recent else 0,
                    "avg_response_time_ms": (
                        sum(r.api_response_time_ms or 0 for r in successes) / len(successes)
                        if successes
                        else None
                    ),
                }

                # Error breakdown
                error_categories: dict[str, int] = {}
                for r in failures:
                    if r.error_category:
                        error_categories[r.error_category] = error_categories.get(r.error_category, 0) + 1
                if error_categories:
                    result["telemetry"]["error_categories"] = error_categories

        except Exception as e:
            result["telemetry_error"] = str(e)

    # Determine overall status
    cb_state = result.get("circuit_breaker", {}).get("state", "closed")
    if cb_state == "open":
        result["status"] = "unhealthy"
        result["message"] = "Circuit breaker is open"
    elif cb_state == "half_open":
        result["status"] = "degraded"
        result["message"] = "Circuit breaker is half-open (recovering)"
    else:
        success_rate = result.get("telemetry", {}).get("success_rate", 1.0)
        if success_rate < 0.5:
            result["status"] = "degraded"
            result["message"] = f"Low success rate ({success_rate:.0%})"
        else:
            result["status"] = "healthy"
            result["message"] = "Web search is operating normally"

    return result


async def check_stt_health(stt_provider: Any | None) -> ComponentHealth:
    """Check STT provider health.

    Args:
        stt_provider: The STT provider instance or None.

    Returns:
        ComponentHealth for the STT provider.
    """
    if stt_provider is None:
        return ComponentHealth(
            name="stt",
            status=HealthStatus.HEALTHY,
            message="STT is disabled",
            details={"enabled": False},
        )

    try:
        return ComponentHealth(
            name="stt",
            status=HealthStatus.HEALTHY,
            message=f"STT provider ready ({stt_provider.provider_name})",
            details={"enabled": True, "provider": stt_provider.provider_name},
        )
    except Exception as e:
        return ComponentHealth(
            name="stt",
            status=HealthStatus.DEGRADED,
            message=f"STT provider error: {str(e)}",
            details={"error": str(e), "enabled": True},
        )


async def run_health_checks(
    llm_provider: Any,
    bot_application: Any,
    web_search_provider: Any | None,
    stt_provider: Any | None,
) -> dict[str, Any]:
    """Run all health checks and update the health checker.

    Args:
        llm_provider: The LLM provider instance.
        bot_application: The Telegram bot application.
        web_search_provider: The web search provider or None.
        stt_provider: The STT provider or None.

    Returns:
        Dictionary with full health status.
    """
    checker = get_health_checker()

    # Run all health checks concurrently
    llm_health, telegram_health, web_search_health, stt_health = await asyncio.gather(
        check_llm_health(llm_provider),
        check_telegram_health(bot_application),
        check_web_search_health(web_search_provider),
        check_stt_health(stt_provider),
    )

    # Update the checker
    checker.update_component(llm_health)
    checker.update_component(telegram_health)
    checker.update_component(web_search_health)
    checker.update_component(stt_health)

    return checker.to_dict()
