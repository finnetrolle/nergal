"""Dependency Injection container for the Nergal application.

This module provides a centralized DI container using dependency-injector
to manage all application dependencies and their lifecycle.

The container uses:
- Configuration providers for settings
- Singleton providers for stateful services (memory, cache)
- Factory providers for stateless services (LLM, STT, web search)
- Async providers for async initialization

Repository Pattern:
- All repositories are provided as Factory providers
- Repositories receive database connection via constructor injection
- Use container.user_repository(), container.profile_repository(), etc.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dependency_injector import containers, providers

if TYPE_CHECKING:
    from nergal.config import Settings
    from nergal.dialog.cache import AgentResultCache
    from nergal.dialog.manager import DialogManager
    from nergal.llm.base import BaseLLMProvider
    from stt_lib import BaseSTTProvider
    from web_search_lib.base import BaseSearchProvider as BaseWebSearchProvider

logger = logging.getLogger(__name__)


class Container(containers.DeclarativeContainer):
    """Main DI container for the Nergal application.

    Wiring configuration allows automatic injection in handlers.
    """

    # Configuration holder
    config = providers.Configuration()

    # Settings provider - loaded once at startup
    settings = providers.Singleton(
        lambda: _load_settings(),
    )

    # ============== Core Services ==============

    # LLM Provider - Factory (can be recreated if needed)
    llm_provider = providers.Factory(
        lambda settings: _create_llm_provider(settings),
        settings=settings,
    )

    # STT Provider - Singleton (expensive to create)
    stt_provider = providers.Singleton(
        lambda settings: _create_stt_provider(settings),
        settings=settings,
    )

    # Web Search Provider - Singleton (maintains connection)
    web_search_provider = providers.Singleton(
        lambda settings: _create_web_search_provider(settings),
        settings=settings,
    )

    # ============== Agent Result Cache ==============

    # Agent result cache - Singleton
    agent_cache = providers.Singleton(
        lambda settings: _create_agent_cache(settings),
        settings=settings,
    )

    # ============== Dialog Manager ==============

    # Dialog manager - Singleton (manages conversation state)
    dialog_manager = providers.Singleton(
        lambda settings, llm, search_provider, cache: _create_dialog_manager(
            settings, llm, search_provider, cache
        ),
        settings=settings,
        llm=llm_provider,
        search_provider=web_search_provider,
        cache=agent_cache,
    )


# ============== Factory Functions ==============

def _load_settings() -> Settings:
    """Load application settings."""
    from nergal.config import get_settings
    return get_settings()


def _create_llm_provider(settings: Settings) -> BaseLLMProvider:
    """Create LLM provider instance."""
    from nergal.llm import create_llm_provider

    logger.info(
        "Creating LLM provider",
        provider=settings.llm.provider,
        model=settings.llm.model,
    )

    return create_llm_provider(
        provider_type=settings.llm.provider,
        api_key=settings.llm.api_key,
        model=settings.llm.model,
        base_url=settings.llm.base_url,
        temperature=settings.llm.temperature,
        max_tokens=settings.llm.max_tokens,
        timeout=settings.llm.timeout,
    )


def _create_stt_provider(settings: Settings) -> BaseSTTProvider | None:
    """Create STT provider instance."""
    from stt_lib import create_stt_provider

    if not settings.stt.enabled:
        logger.info("STT provider disabled")
        return None

    logger.info(
        "Creating STT provider",
        provider=settings.stt.provider,
        model=settings.stt.model,
    )

    return create_stt_provider(
        provider_type=settings.stt.provider,
        model=settings.stt.model,
        device=settings.stt.device,
        compute_type=settings.stt.compute_type,
        api_key=settings.stt.api_key or None,
        timeout=settings.stt.timeout,
    )


def _create_web_search_provider(settings: Settings) -> BaseWebSearchProvider | None:
    """Create web search provider instance."""
    from web_search_lib.providers import ZaiMcpHttpSearchProvider

    if not settings.web_search.enabled:
        logger.info("Web search provider disabled")
        return None

    api_key = settings.web_search.api_key or settings.llm.api_key

    logger.info(
        "Creating web search provider",
        mcp_url=settings.web_search.mcp_url,
    )

    return ZaiMcpHttpSearchProvider(
        api_key=api_key,
        mcp_url=settings.web_search.mcp_url,
        timeout=settings.web_search.timeout,
    )


def _create_agent_cache(settings: Settings) -> AgentResultCache | None:
    """Create agent result cache instance."""
    from nergal.dialog.cache import AgentResultCache

    logger.info(
        "Creating agent result cache",
        enabled=settings.cache.enabled,
        ttl_seconds=settings.cache.ttl_seconds,
        max_size=settings.cache.max_size,
    )

    return AgentResultCache(
        enabled=settings.cache.enabled,
        ttl_seconds=settings.cache.ttl_seconds,
        max_size=settings.cache.max_size,
    )


def _create_dialog_manager(
    settings: Settings,
    llm_provider: BaseLLMProvider,
    search_provider: BaseWebSearchProvider | None,
    cache: AgentResultCache | None,
) -> DialogManager:
    """Create dialog manager instance."""
    from nergal.dialog.agent_loader import register_configured_agents
    from nergal.dialog.manager import DialogManager

    logger.info(
        "Creating dialog manager",
        style=settings.style.value,
    )

    manager = DialogManager(
        llm_provider=llm_provider,
        style_type=settings.style,
        cache=cache,
    )

    # Register agents based on configuration
    registered = register_configured_agents(
        registry=manager.agent_registry,
        settings=settings,
        llm_provider=llm_provider,
        search_provider=search_provider,
    )

    if registered:
        logger.info("Registered agents", agents=registered)

    return manager


# ============== Container Instance ==============

# Global container instance
_container: Container | None = None


def get_container() -> Container:
    """Get or create the global DI container instance."""
    global _container

    if _container is None:
        _container = Container()
        logger.info("DI container initialized")

    return _container


def init_container() -> Container:
    """Initialize the DI container.

    This should be called once at application startup.
    """
    global _container

    if _container is not None:
        logger.warning("DI container already initialized")
        return _container

    _container = Container()
    logger.info("DI container initialized")
    return _container


def override_container(container: Container) -> None:
    """Override the global container (useful for testing)."""
    global _container
    _container = container


def reset_container() -> None:
    """Reset the global container (useful for testing)."""
    global _container
    _container = None
