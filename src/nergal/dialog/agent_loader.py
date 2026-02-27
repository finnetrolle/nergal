"""Agent registration and loading utilities.

This module provides a decorator-based registry for creating and registering agents.
Agents can register themselves using the @AgentFactory.register decorator.

Example:
    ```python
    @AgentFactory.register(AgentType.WEB_SEARCH)
    def create_web_search_agent(llm_provider, **kwargs):
        return WebSearchAgent(llm_provider, kwargs.get('style_type', StyleType.DEFAULT))
    ```
"""

import logging
from typing import TYPE_CHECKING, Callable

from nergal.config import Settings
from nergal.dialog.base import AgentType, BaseAgent
from nergal.dialog.styles import StyleType

if TYPE_CHECKING:
    from nergal.llm.base import BaseLLMProvider
    from nergal.web_search.base import BaseWebSearchProvider
    from nergal.dialog.base import AgentRegistry

logger = logging.getLogger(__name__)


class AgentFactory:
    """Registry for agent factories using decorator pattern.

    This class provides a centralized way to register and create agents.
    Agents register themselves using the @AgentFactory.register decorator.

    Attributes:
        _factories: Dictionary mapping AgentType to factory functions.
        _dependencies: Dictionary mapping AgentType to required dependencies.
    """

    _factories: dict[AgentType, Callable] = {}
    _dependencies: dict[AgentType, list[str]] = {}

    @classmethod
    def register(
        cls,
        agent_type: AgentType,
        requires_search: bool = False,
        requires_todoist: bool = False,
    ) -> Callable:
        """Decorator to register an agent factory.

        Args:
            agent_type: The type of agent this factory creates.
            requires_search: Whether this agent requires a search provider.
            requires_todoist: Whether this agent requires Todoist integration.

        Returns:
            Decorator function.

        Example:
            ```python
            @AgentFactory.register(AgentType.WEB_SEARCH, requires_search=True)
            def create_web_search_agent(llm_provider, search_provider, **kwargs):
                return WebSearchAgent(llm_provider, search_provider)
            ```
        """

        def decorator(factory_func: Callable) -> Callable:
            cls._factories[agent_type] = factory_func
            cls._dependencies[agent_type] = []
            if requires_search:
                cls._dependencies[agent_type].append("search")
            if requires_todoist:
                cls._dependencies[agent_type].append("todoist")
            logger.debug(f"Registered agent factory: {agent_type.value}")
            return factory_func

        return decorator

    @classmethod
    def create(
        cls,
        agent_type: AgentType,
        llm_provider: "BaseLLMProvider",
        search_provider: "BaseWebSearchProvider | None" = None,
        todoist_client: "TodoistClient | None" = None,
        **kwargs,
    ) -> BaseAgent | None:
        """Create an agent instance by type.

        Args:
            agent_type: Type of agent to create.
            llm_provider: LLM provider instance.
            search_provider: Optional web search provider.
            todoist_client: Optional Todoist client.
            **kwargs: Additional arguments passed to the factory.

        Returns:
            Agent instance or None if factory not found.
        """
        factory = cls._factories.get(agent_type)
        if factory is None:
            logger.warning(f"No factory registered for agent type: {agent_type.value}")
            return None

        # Check dependencies
        deps = cls._dependencies.get(agent_type, [])
        if "search" in deps and search_provider is None:
            logger.warning(
                f"Agent {agent_type.value} requires search_provider but none provided"
            )
            return None
        if "todoist" in deps and todoist_client is None:
            logger.warning(
                f"Agent {agent_type.value} requires todoist_client but none provided"
            )
            return None

        # Call factory with appropriate arguments
        return factory(
            llm_provider=llm_provider,
            search_provider=search_provider,
            todoist_client=todoist_client,
            **kwargs,
        )

    @classmethod
    def get_registered_types(cls) -> list[AgentType]:
        """Get list of all registered agent types.

        Returns:
            List of registered AgentType values.
        """
        return list(cls._factories.keys())

    @classmethod
    def has_factory(cls, agent_type: AgentType) -> bool:
        """Check if a factory is registered for an agent type.

        Args:
            agent_type: Agent type to check.

        Returns:
            True if factory exists, False otherwise.
        """
        return agent_type in cls._factories

    @classmethod
    def clear(cls) -> None:
        """Clear all registered factories.

        Useful for testing.
        """
        cls._factories.clear()
        cls._dependencies.clear()


# =============================================================================
# Agent Factory Registrations
# =============================================================================


@AgentFactory.register(AgentType.WEB_SEARCH, requires_search=True)
def _create_web_search_agent(
    llm_provider: "BaseLLMProvider",
    search_provider: "BaseWebSearchProvider",
    **kwargs,
) -> BaseAgent:
    """Create a WebSearchAgent instance."""
    from nergal.dialog.agents.web_search_agent import WebSearchAgent

    return WebSearchAgent(
        llm_provider=llm_provider,
        search_provider=search_provider,
        style_type=kwargs.get("style_type", StyleType.DEFAULT),
        max_search_results=kwargs.get("max_search_results", 5),
    )


@AgentFactory.register(AgentType.TODOIST, requires_todoist=True)
def _create_todoist_agent(
    llm_provider: "BaseLLMProvider",
    todoist_client: "TodoistClient | None" = None,
    **kwargs,
) -> BaseAgent:
    """Create a TodoistAgent instance."""
    from nergal.dialog.agents.todoist_agent import TodoistAgent
    from nergal.integrations.todoist import TodoistClient

    # Create client if not provided
    client = todoist_client
    if client is None:
        client = TodoistClient()

    return TodoistAgent(
        llm_provider=llm_provider,
        todoist_client=client,
        style_type=kwargs.get("style_type", StyleType.DEFAULT),
    )


@AgentFactory.register(AgentType.NEWS)
def _create_news_agent(
    llm_provider: "BaseLLMProvider",
    **kwargs,
) -> BaseAgent:
    """Create a NewsAgent instance."""
    from nergal.dialog.agents.news_agent import NewsAgent

    return NewsAgent(
        llm_provider=llm_provider,
        style_type=kwargs.get("style_type", StyleType.DEFAULT),
    )


@AgentFactory.register(AgentType.CODE_ANALYSIS)
def _create_code_analysis_agent(
    llm_provider: "BaseLLMProvider",
    **kwargs,
) -> BaseAgent:
    """Create a CodeAnalysisAgent instance."""
    from nergal.dialog.agents.code_analysis_agent import CodeAnalysisAgent

    return CodeAnalysisAgent(
        llm_provider=llm_provider,
        style_type=kwargs.get("style_type", StyleType.DEFAULT),
    )


@AgentFactory.register(AgentType.METRICS)
def _create_metrics_agent(
    llm_provider: "BaseLLMProvider",
    **kwargs,
) -> BaseAgent:
    """Create a MetricsAgent instance."""
    from nergal.dialog.agents.metrics_agent import MetricsAgent

    return MetricsAgent(
        llm_provider=llm_provider,
        style_type=kwargs.get("style_type", StyleType.DEFAULT),
    )


@AgentFactory.register(AgentType.HEALTH)
def _create_health_agent(
    llm_provider: "BaseLLMProvider",
    **kwargs,
) -> BaseAgent:
    """Create a HealthAgent instance."""
    from nergal.dialog.agents.health_agent import HealthAgent

    return HealthAgent(
        llm_provider=llm_provider,
        style_type=kwargs.get("style_type", StyleType.DEFAULT),
    )


@AgentFactory.register(AgentType.REMINDER)
def _create_reminder_agent(
    llm_provider: "BaseLLMProvider",
    **kwargs,
) -> BaseAgent:
    """Create a ReminderAgent instance."""
    from nergal.dialog.agents.reminder_agent import ReminderAgent

    return ReminderAgent(
        llm_provider=llm_provider,
        style_type=kwargs.get("style_type", StyleType.DEFAULT),
    )


# =============================================================================
# Configuration-based Registration
# =============================================================================


# Mapping from config settings to agent types
AGENT_CONFIG_MAP: dict[str, AgentType] = {
    "web_search_enabled": AgentType.WEB_SEARCH,
    "news_enabled": AgentType.NEWS,
    "code_analysis_enabled": AgentType.CODE_ANALYSIS,
    "metrics_enabled": AgentType.METRICS,
    "todoist_enabled": AgentType.TODOIST,
    "health_enabled": AgentType.HEALTH,
    "reminder_enabled": AgentType.REMINDER,
}


def register_configured_agents(
    registry: "AgentRegistry",
    settings: Settings,
    llm_provider: "BaseLLMProvider",
    search_provider: "BaseWebSearchProvider | None" = None,
    todoist_client: "TodoistClient | None" = None,
) -> list[str]:
    """Register agents based on configuration settings.

    This function creates and registers agents according to the
    enabled flags in the AgentSettings configuration.

    Args:
        registry: Agent registry to register agents with.
        settings: Application settings.
        llm_provider: LLM provider instance.
        search_provider: Optional web search provider instance.
        todoist_client: Optional Todoist client instance.

    Returns:
        List of registered agent names.
    """
    registered = []
    agent_settings = settings.agents
    style_type = settings.style

    # Iterate through config mapping and register enabled agents
    for config_key, agent_type in AGENT_CONFIG_MAP.items():
        # Check if this agent type is enabled in config
        enabled = getattr(agent_settings, config_key, False)
        if not enabled:
            continue

        # Check if factory exists
        if not AgentFactory.has_factory(agent_type):
            logger.warning(f"No factory for {agent_type.value}, skipping")
            continue

        # Check dependencies
        deps = AgentFactory._dependencies.get(agent_type, [])
        if "search" in deps and search_provider is None:
            logger.debug(f"Skipping {agent_type.value} - requires search_provider")
            continue
        if "todoist" in deps and todoist_client is None:
            logger.debug(f"Skipping {agent_type.value} - requires todoist_client")
            continue

        # Create and register agent
        try:
            agent = AgentFactory.create(
                agent_type=agent_type,
                llm_provider=llm_provider,
                search_provider=search_provider,
                todoist_client=todoist_client,
                style_type=style_type,
                max_results=settings.web_search.max_results if agent_type == AgentType.WEB_SEARCH else None,
            )

            if agent is not None:
                registry.register(agent)
                registered.append(agent.agent_type.value)
                logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register {agent_type.value}: {e}")

    return registered


# =============================================================================
# Legacy Compatibility Functions
# =============================================================================


# These functions are kept for backward compatibility
# They delegate to the new AgentFactory system


def create_web_search_agent(
    llm_provider: "BaseLLMProvider",
    search_provider: "BaseWebSearchProvider",
    style_type: StyleType,
    max_results: int = 5,
) -> BaseAgent:
    """Create a WebSearchAgent instance.

    Args:
        llm_provider: LLM provider instance.
        search_provider: Web search provider instance.
        style_type: Response style type.
        max_results: Maximum search results.

    Returns:
        WebSearchAgent instance.
    """
    return AgentFactory.create(
        AgentType.WEB_SEARCH,
        llm_provider=llm_provider,
        search_provider=search_provider,
        style_type=style_type,
        max_results=max_results,
    )


def create_news_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a NewsAgent instance."""
    return AgentFactory.create(
        AgentType.NEWS,
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_code_analysis_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a CodeAnalysisAgent instance."""
    return AgentFactory.create(
        AgentType.CODE_ANALYSIS,
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_metrics_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a MetricsAgent instance."""
    return AgentFactory.create(
        AgentType.METRICS,
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_todoist_agent(
    llm_provider: "BaseLLMProvider",
    todoist_client: "TodoistClient | None" = None,
    style_type: StyleType = StyleType.DEFAULT,
) -> BaseAgent:
    """Create a TodoistAgent instance."""
    return AgentFactory.create(
        AgentType.TODOIST,
        llm_provider=llm_provider,
        todoist_client=todoist_client,
        style_type=style_type,
    )
