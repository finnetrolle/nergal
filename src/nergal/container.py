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
    from nergal.agent.runtime import AgentRuntime
    from nergal.config import Settings
    from nergal.memory.base import Memory
    from nergal.security.policy import SecurityPolicy
    from nergal.skills.base import Skill
    from nergal.skills.loader import SkillLoader
    from nergal.tools.base import Tool
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

    # ============== Security System ==============

    # Security policy - Singleton (enforces rules)
    security_policy = providers.Singleton(
        lambda settings: _create_security_policy(settings),
        settings=settings,
    )

    # ============== Skills System ==============

    # Skills loader - Singleton (loads skill definitions)
    skills_loader = providers.Singleton(
        lambda settings: _create_skills_loader(settings),
        settings=settings,
    )

    # Tools list - Factory (recreates on each call)
    tools = providers.Factory(
        lambda settings, stt, search_provider, security_policy: _create_tools(
            settings, stt, search_provider, security_policy
        ),
        settings=settings,
        stt=stt_provider,
        search_provider=web_search_provider,
        security_policy=security_policy,
    )

    # ============== Agent Runtime ==============

    # Agent runtime - Singleton (new ZeroClaw architecture)
    agent_runtime = providers.Singleton(
        lambda settings, llm, tools, memory, security_policy: _create_agent_runtime(
            settings, llm, tools, memory, security_policy
        ),
        settings=settings,
        llm=llm_provider,
        tools=tools,
        memory=memory,
        security_policy=security_policy,
    )

    # ============== Telegram Handlers ==============

    # Handler service - Singleton (stateless, but keeps reference consistency)
    handler_service = providers.Singleton(
        lambda settings, stt_provider, agent_runtime: _create_handler_service(
            settings, stt_provider, agent_runtime
        ),
        settings=settings,
        stt_provider=stt_provider,
        agent_runtime=agent_runtime,
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
    # Memory will be initialized lazily on first use
    return memory


def _create_security_policy(settings: Settings) -> SecurityPolicy:
    """Create security policy instance."""
    from nergal.security.policy import AutonomyLevel, SecurityPolicy

    # Parse autonomy level
    try:
        autonomy_level = AutonomyLevel(settings.security.autonomy_level)
    except ValueError:
        logger.warning(
            f"Invalid autonomy level: {settings.security.autonomy_level}, using 'limited' instead"
        )
        autonomy_level = AutonomyLevel.LIMITED

    logger.info(
        "Creating security policy (level: %s, workspace: %s)",
        autonomy_level.value,
        settings.security.workspace_dir,
    )

    return SecurityPolicy(
        autonomy_level=autonomy_level,
        workspace_dir=settings.security.workspace_dir,
        allowed_commands=settings.security.allowed_commands,
        workspace_only=settings.security.workspace_only,
        allowed_domains=settings.security.allowed_domains,
    )


def _create_handler_service(
    settings: Settings,
    stt_provider: BaseSTTProvider | None,
    agent_runtime: AgentRuntime,
) -> TelegramHandlerService:
    """Create Telegram handler service instance."""
    from telegram_handlers_lib import create_handler_service

    logger.info("Creating Telegram handler service (using AgentRuntime)")

    return create_handler_service(
        settings=settings,
        stt_provider=stt_provider,
        agent_runtime=agent_runtime,
    )


def _create_skills_loader(settings: Settings) -> SkillLoader:
    """Create skills loader instance."""
    from nergal.skills.loader import SkillLoader

    if not settings.skills.enabled:
        logger.info("Skills system disabled")
        # Return a no-op loader

        class NoOpSkillLoader:
            def load_all(self) -> dict[str, Skill]:
                return {}

        return NoOpSkillLoader()

    logger.info(
        "Creating skills loader (dir: %s)",
        settings.skills.skills_dir,
    )

    return SkillLoader(skills_dir=settings.skills.skills_dir)


def _create_agent_runtime(
    settings: Settings,
    llm_provider: BaseLLMProvider,
    tools: list[Tool],
    memory: Memory,
    security_policy: SecurityPolicy,
) -> AgentRuntime:
    """Create agent runtime instance (ZeroClaw architecture)."""
    from nergal.agent.runtime import AgentRuntime

    logger.info("Creating agent runtime (ZeroClaw architecture)")

    return AgentRuntime(
        llm_provider=llm_provider,
        tools=tools,
        memory=memory,
        security_policy=security_policy,
        max_history=settings.llm.max_history,
    )


def _create_tools(
    settings: Settings,
    stt_provider: BaseSTTProvider | None,
    search_provider: BaseWebSearchProvider | None,
    security_policy: SecurityPolicy,
) -> list[Tool]:
    """Create list of available tools."""
    from nergal.tools import (
        FileReadTool,
        FileWriteTool,
        HttpRequestTool,
        ShellExecuteTool,
        TranscribeTool,
        WebSearchTool,
    )

    tools: list[Tool] = []

    def _add_tool_if_allowed(tool: Tool, tool_name: str, reason: str = "enabled") -> None:
        """Add tool if allowed by security policy."""
        allowed, policy_reason = security_policy.is_tool_allowed(tool_name)
        if allowed:
            tools.append(tool)
            logger.info(f"Adding {tool_name} ({reason})")
        else:
            logger.info(f"{tool_name} disabled by security policy: {policy_reason or 'no reason'}")

    # Web search tool
    if search_provider and settings.web_search.enabled:
        _add_tool_if_allowed(
            WebSearchTool(search_provider=search_provider),
            "web_search",
            "web search enabled",
        )

    # STT tool (transcribe audio)
    if stt_provider and settings.stt.enabled:
        _add_tool_if_allowed(
            TranscribeTool(
                stt_provider=stt_provider,
                default_language=settings.stt.language,
            ),
            "transcribe_audio",
            "STT enabled",
        )

    # File tools
    _add_tool_if_allowed(
        FileReadTool(workspace_dir=security_policy.workspace_dir),
        "file_read",
        "file operations",
    )
    _add_tool_if_allowed(
        FileWriteTool(workspace_dir=security_policy.workspace_dir),
        "file_write",
        "file operations",
    )

    # HTTP request tool
    _add_tool_if_allowed(HttpRequestTool(), "http_request", "HTTP operations")

    # Shell execute tool
    _add_tool_if_allowed(ShellExecuteTool(), "shell_execute", "shell operations")

    logger.info(f"Total tools created: {len(tools)}")
    return tools


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
