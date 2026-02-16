"""Agent registration and loading utilities.

This module provides functions to dynamically register agents
based on configuration settings.
"""

import logging
from typing import TYPE_CHECKING

from nergal.config import Settings
from nergal.dialog.base import BaseAgent
from nergal.dialog.styles import StyleType

if TYPE_CHECKING:
    from nergal.llm.base import BaseLLMProvider
    from nergal.web_search.base import BaseWebSearchProvider
    from nergal.dialog.base import AgentRegistry

logger = logging.getLogger(__name__)


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
    from nergal.dialog.agents.web_search_agent import WebSearchAgent
    
    return WebSearchAgent(
        llm_provider=llm_provider,
        search_provider=search_provider,
        style_type=style_type,
        max_search_results=max_results,
    )


def create_news_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a NewsAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        NewsAgent instance.
    """
    from nergal.dialog.agents.news_agent import NewsAgent
    
    return NewsAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_analysis_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create an AnalysisAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        AnalysisAgent instance.
    """
    from nergal.dialog.agents.analysis_agent import AnalysisAgent
    
    return AnalysisAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_fact_check_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a FactCheckAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        FactCheckAgent instance.
    """
    from nergal.dialog.agents.fact_check_agent import FactCheckAgent
    
    return FactCheckAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_comparison_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a ComparisonAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        ComparisonAgent instance.
    """
    from nergal.dialog.agents.comparison_agent import ComparisonAgent
    
    return ComparisonAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_summary_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a SummaryAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        SummaryAgent instance.
    """
    from nergal.dialog.agents.summary_agent import SummaryAgent
    
    return SummaryAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_code_analysis_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a CodeAnalysisAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        CodeAnalysisAgent instance.
    """
    from nergal.dialog.agents.code_analysis_agent import CodeAnalysisAgent
    
    return CodeAnalysisAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_metrics_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a MetricsAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        MetricsAgent instance.
    """
    from nergal.dialog.agents.metrics_agent import MetricsAgent
    
    return MetricsAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_expertise_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create an ExpertiseAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        ExpertiseAgent instance.
    """
    from nergal.dialog.agents.expertise_agent import ExpertiseAgent
    
    return ExpertiseAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_clarification_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a ClarificationAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        ClarificationAgent instance.
    """
    from nergal.dialog.agents.clarification_agent import ClarificationAgent
    
    return ClarificationAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_knowledge_base_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a KnowledgeBaseAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        KnowledgeBaseAgent instance.
    """
    from nergal.dialog.agents.knowledge_base_agent import KnowledgeBaseAgent
    
    return KnowledgeBaseAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def create_tech_docs_agent(
    llm_provider: "BaseLLMProvider",
    style_type: StyleType,
) -> BaseAgent:
    """Create a TechDocsAgent instance.
    
    Args:
        llm_provider: LLM provider instance.
        style_type: Response style type.
        
    Returns:
        TechDocsAgent instance.
    """
    from nergal.dialog.agents.tech_docs_agent import TechDocsAgent
    
    return TechDocsAgent(
        llm_provider=llm_provider,
        style_type=style_type,
    )


def register_configured_agents(
    registry: "AgentRegistry",
    settings: Settings,
    llm_provider: "BaseLLMProvider",
    search_provider: "BaseWebSearchProvider | None" = None,
) -> list[str]:
    """Register agents based on configuration settings.
    
    This function creates and registers agents according to the
    enabled flags in the AgentSettings configuration.
    
    Args:
        registry: Agent registry to register agents with.
        settings: Application settings.
        llm_provider: LLM provider instance.
        search_provider: Optional web search provider instance.
        
    Returns:
        List of registered agent names.
    """
    registered = []
    agent_settings = settings.agents
    style_type = settings.style
    
    # WebSearchAgent - requires search_provider
    if agent_settings.web_search_enabled and search_provider:
        try:
            agent = create_web_search_agent(
                llm_provider=llm_provider,
                search_provider=search_provider,
                style_type=style_type,
                max_results=settings.web_search.max_results,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register WebSearchAgent: {e}")
    
    # NewsAgent
    if agent_settings.news_enabled:
        try:
            agent = create_news_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register NewsAgent: {e}")
    
    # AnalysisAgent
    if agent_settings.analysis_enabled:
        try:
            agent = create_analysis_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register AnalysisAgent: {e}")
    
    # FactCheckAgent
    if agent_settings.fact_check_enabled:
        try:
            agent = create_fact_check_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register FactCheckAgent: {e}")
    
    # ComparisonAgent
    if agent_settings.comparison_enabled:
        try:
            agent = create_comparison_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register ComparisonAgent: {e}")
    
    # SummaryAgent
    if agent_settings.summary_enabled:
        try:
            agent = create_summary_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register SummaryAgent: {e}")
    
    # CodeAnalysisAgent
    if agent_settings.code_analysis_enabled:
        try:
            agent = create_code_analysis_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register CodeAnalysisAgent: {e}")
    
    # MetricsAgent
    if agent_settings.metrics_enabled:
        try:
            agent = create_metrics_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register MetricsAgent: {e}")
    
    # ExpertiseAgent
    if agent_settings.expertise_enabled:
        try:
            agent = create_expertise_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register ExpertiseAgent: {e}")
    
    # ClarificationAgent
    if agent_settings.clarification_enabled:
        try:
            agent = create_clarification_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register ClarificationAgent: {e}")
    
    # KnowledgeBaseAgent
    if agent_settings.knowledge_base_enabled:
        try:
            agent = create_knowledge_base_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register KnowledgeBaseAgent: {e}")
    
    # TechDocsAgent
    if agent_settings.tech_docs_enabled:
        try:
            agent = create_tech_docs_agent(
                llm_provider=llm_provider,
                style_type=style_type,
            )
            registry.register(agent)
            registered.append(agent.agent_type.value)
            logger.info(f"Registered agent: {agent.agent_type.value}")
        except Exception as e:
            logger.error(f"Failed to register TechDocsAgent: {e}")
    
    return registered
