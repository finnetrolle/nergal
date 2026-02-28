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
    from llm_lib import BaseLLMProvider
    from nergal.config import Settings
    from nergal.dialog.manager import DialogManager
    from nergal.memory.base import Memory
    from stt_lib import BaseSTTProvider
    from telegram_handlers_lib.base import TelegramHandlerService
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

    # ============== Memory System ==============

    # Memory backend - Singleton (persistent connection)
    memory = providers.Singleton(
        lambda settings: _create_memory(settings),
        settings=settings,
    )

    # ============== Dialog Manager ==============

    # Dialog manager - Singleton (manages conversation state)
    dialog_manager = providers.Singleton(
        lambda settings, llm, search_provider: _create_dialog_manager(
            settings, llm, search_provider
        ),
        settings=settings,
        llm=llm_provider,
        search_provider=web_search_provider,
    )

    # ============== Telegram Handlers ==============

    # Handler service - Singleton (stateless, but keeps reference consistency)
    handler_service = providers.Singleton(
        lambda settings, dialog_manager, stt_provider: _create_handler_service(
            settings, dialog_manager, stt_provider
        ),
        settings=settings,
        dialog_manager=dialog_manager,
        stt_provider=stt_provider,
    )


# ============== Factory Functions ==============

def _load_settings() -> Settings:
    """Load application settings."""
    from nergal.config import get_settings
    return get_settings()


def _create_llm_provider(settings: Settings) -> BaseLLMProvider:
    """Create LLM provider instance."""
    from llm_lib import create_llm_provider

    logger.info(
        "Creating LLM provider: %s (model: %s)",
        settings.llm.provider,
        settings.llm.model,
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
        "Creating STT provider: %s (model: %s)",
        settings.stt.provider,
        settings.stt.model,
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
        "Creating web search provider (MCP URL: %s)",
        settings.web_search.mcp_url,
    )

    return ZaiMcpHttpSearchProvider(
        api_key=api_key,
        mcp_url=settings.web_search.mcp_url,
        timeout=settings.web_search.timeout,
    )


def _create_dialog_manager(
    settings: Settings,
    llm_provider: BaseLLMProvider,
    search_provider: BaseWebSearchProvider | None,
) -> DialogManager:
    """Create dialog manager instance."""
    from nergal.dialog.manager import DialogManager

    logger.info(
        "Creating dialog manager (style: %s)",
        settings.style.value,
    )

    manager = DialogManager(
        llm_provider=llm_provider,
        style_type=settings.style,
        web_search_provider=search_provider,
    )

    return manager


def _create_memory(settings: Settings) -> Memory:
    """Create memory backend instance."""
    from nergal.memory.sqlite import SQLiteMemory

    if not settings.memory.enabled:
        logger.info("Memory system disabled")
        # Return a no-op memory
        from nergal.memory.base import Memory

        class NoOpMemory(Memory):
            async def store(self, key: str, content: str, category, metadata=None) -> None:
                pass

            async def recall(self, query: str, limit: int = 5, category=None) -> list:
                return []

            async def forget(self, key: str) -> None:
                pass

            async def get_by_key(self, key: str):
                return None

            async def clear_category(self, category) -> int:
                return 0

        return NoOpMemory()

    logger.info(
        "Creating memory backend (path: %s)",
        settings.memory.db_path,
    )

    memory = SQLiteMemory(db_path=settings.memory.db_path)
    # Initialize the database
    import asyncio
    asyncio.create_task(memory.initialize())
    return memory


def _create_handler_service(
    settings: Settings,
    dialog_manager: DialogManager,
    stt_provider: BaseSTTProvider | None,
) -> TelegramHandlerService:
    """Create Telegram handler service instance."""
    from telegram_handlers_lib import create_handler_service

    logger.info("Creating Telegram handler service")

    return create_handler_service(
        dialog_manager=dialog_manager,
        settings=settings,
        stt_provider=stt_provider,
    )


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
