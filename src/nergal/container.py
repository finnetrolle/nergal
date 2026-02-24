"""Dependency Injection container for the Nergal application.

This module provides a centralized DI container using dependency-injector
to manage all application dependencies and their lifecycle.

The container uses:
- Configuration providers for settings
- Singleton providers for stateful services (database, memory)
- Factory providers for stateless services (LLM, STT, web search)
- Async providers for async initialization

Database Connection Lifecycle:
- The database provider creates a DatabaseConnection instance
- Call init_database() at startup to establish the connection pool
- Call shutdown_database() at shutdown to close connections gracefully

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
    from nergal.llm.base import BaseLLMProvider
    from nergal.stt.base import BaseSTTProvider
    from nergal.web_search.base import BaseWebSearchProvider
    from nergal.dialog.manager import DialogManager
    from nergal.memory.service import MemoryService
    from nergal.database.connection import DatabaseConnection
    from nergal.database.repositories import (
        UserRepository,
        ProfileRepository,
        ConversationRepository,
        WebSearchTelemetryRepository,
        UserIntegrationRepository,
    )
    from nergal.monitoring.metrics import MetricsServer

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
    
    # ============== Database ==============
    
    # Database connection - Singleton
    database = providers.Singleton(
        lambda settings: _create_database(settings),
        settings=settings,
    )
    
    # ============== Repositories ==============
    
    # User repository - Factory (receives db via constructor injection)
    user_repository = providers.Factory(
        lambda db: _create_user_repository(db),
        db=database,
    )
    
    # Profile repository - Factory
    profile_repository = providers.Factory(
        lambda db: _create_profile_repository(db),
        db=database,
    )
    
    # Conversation repository - Factory
    conversation_repository = providers.Factory(
        lambda db: _create_conversation_repository(db),
        db=database,
    )
    
    # Web search telemetry repository - Factory
    web_search_telemetry_repository = providers.Factory(
        lambda db: _create_web_search_telemetry_repository(db),
        db=database,
    )
    
    # User integration repository - Factory
    user_integration_repository = providers.Factory(
        lambda db: _create_user_integration_repository(db),
        db=database,
    )
    
    # ============== Memory Service ==============
    
    # Memory service - Singleton (depends on database)
    memory_service = providers.Singleton(
        lambda db: _create_memory_service(db),
        db=database,
    )
    
    # ============== Dialog Manager ==============
    
    # Dialog manager - Singleton (manages conversation state)
    dialog_manager = providers.Singleton(
        lambda settings, llm, search_provider, memory: _create_dialog_manager(
            settings, llm, search_provider, memory
        ),
        settings=settings,
        llm=llm_provider,
        search_provider=web_search_provider,
        memory=memory_service,
    )
    
    # ============== Monitoring ==============
    
    # Metrics server - Singleton
    metrics_server = providers.Singleton(
        lambda settings: _create_metrics_server(settings),
        settings=settings,
    )


# ============== Factory Functions ==============

def _load_settings() -> "Settings":
    """Load application settings."""
    from nergal.config import get_settings
    return get_settings()


def _create_llm_provider(settings: "Settings") -> "BaseLLMProvider":
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


def _create_stt_provider(settings: "Settings") -> "BaseSTTProvider | None":
    """Create STT provider instance."""
    from nergal.stt import create_stt_provider
    
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


def _create_web_search_provider(settings: "Settings") -> "BaseWebSearchProvider | None":
    """Create web search provider instance."""
    from nergal.web_search.zai_mcp_http import ZaiMcpHttpSearchProvider
    
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


def _create_database(settings: "Settings") -> "DatabaseConnection":
    """Create database connection instance."""
    from nergal.database.connection import DatabaseConnection
    
    logger.info(
        "Creating database connection",
        host=settings.database.host,
        database=settings.database.name,
    )
    
    return DatabaseConnection(settings.database)


# ============== Repository Factory Functions ==============

def _create_user_repository(db: "DatabaseConnection") -> "UserRepository":
    """Create user repository instance with injected database connection."""
    from nergal.database.repositories import UserRepository
    return UserRepository(db=db)


def _create_profile_repository(db: "DatabaseConnection") -> "ProfileRepository":
    """Create profile repository instance with injected database connection."""
    from nergal.database.repositories import ProfileRepository
    return ProfileRepository(db=db)


def _create_conversation_repository(db: "DatabaseConnection") -> "ConversationRepository":
    """Create conversation repository instance with injected database connection."""
    from nergal.database.repositories import ConversationRepository
    return ConversationRepository(db=db)


def _create_web_search_telemetry_repository(db: "DatabaseConnection") -> "WebSearchTelemetryRepository":
    """Create web search telemetry repository instance with injected database connection."""
    from nergal.database.repositories import WebSearchTelemetryRepository
    return WebSearchTelemetryRepository(db=db)


def _create_user_integration_repository(db: "DatabaseConnection") -> "UserIntegrationRepository":
    """Create user integration repository instance with injected database connection."""
    from nergal.database.repositories import UserIntegrationRepository
    return UserIntegrationRepository(db=db)


def _create_memory_service(database: "DatabaseConnection") -> "MemoryService | None":
    """Create memory service instance.

    Args:
        database: DatabaseConnection instance from DI container.
    """
    from nergal.memory.service import MemoryService

    settings = _load_settings()

    if not settings.memory.long_term_enabled:
        logger.info("Memory service disabled")
        return None

    logger.info("Creating memory service")
    return MemoryService(db=database)


def _create_dialog_manager(
    settings: "Settings",
    llm_provider: "BaseLLMProvider",
    search_provider: "BaseWebSearchProvider | None",
    memory_service: "MemoryService | None",
) -> "DialogManager":
    """Create dialog manager instance."""
    from nergal.dialog.manager import DialogManager
    from nergal.dialog.agent_loader import register_configured_agents
    
    logger.info(
        "Creating dialog manager",
        style=settings.style.value,
    )
    
    manager = DialogManager(
        llm_provider=llm_provider,
        style_type=settings.style,
        memory_service=memory_service,
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


def _create_metrics_server(settings: "Settings") -> "MetricsServer | None":
    """Create metrics server instance."""
    from nergal.monitoring import MetricsServer
    
    if not settings.monitoring.enabled:
        logger.info("Metrics server disabled")
        return None
    
    logger.info(
        "Creating metrics server",
        port=settings.monitoring.metrics_port,
    )
    
    return MetricsServer(port=settings.monitoring.metrics_port)


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


# ============== Async Lifecycle Management ==============

async def init_database() -> "DatabaseConnection":
    """Initialize the database connection pool.

    This should be called once at application startup after
    the container is initialized.

    Returns:
        The initialized DatabaseConnection instance.

    Raises:
        RuntimeError: If container is not initialized.
    """
    container = get_container()
    db = container.database()

    if not db.is_connected:
        logger.info("Initializing database connection pool")
        await db.connect()
        logger.info("Database connection pool initialized")

    return db


async def shutdown_database() -> None:
    """Shutdown the database connection pool.

    This should be called at application shutdown to gracefully
    close all database connections.
    """
    global _container

    if _container is None:
        return

    db = _container.database()
    if db is not None and db.is_connected:
        logger.info("Shutting down database connection pool")
        await db.disconnect()
        logger.info("Database connection pool shut down")
