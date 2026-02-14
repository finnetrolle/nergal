"""Dialog management module for handling user conversations.

This module provides a complete system for managing dialogs with users,
including agent-based message routing, context management, and logging.

Example usage:
    from nergal.dialog import DialogManager
    from nergal.llm import create_llm_provider

    # Create LLM provider
    llm = create_llm_provider("zai", api_key="...", model="...")

    # Create dialog manager
    manager = DialogManager(llm_provider=llm)

    # Process a message
    result = await manager.process_message(
        user_id=12345,
        message="Привет!",
        user_info={"first_name": "John"}
    )
    print(result.response)
"""

from nergal.dialog.base import (
    AgentCategory,
    AgentRegistry,
    AgentResult,
    AgentType,
    BaseAgent,
    ExecutionPlan,
    PlanStep,
)
from nergal.dialog.context import ContextManager, DialogContext, DialogState, UserInfo
from nergal.dialog.default_agent import DefaultAgent
from nergal.dialog.dispatcher_agent import DispatcherAgent
from nergal.dialog.manager import DialogManager, PlanExecutionResult, ProcessResult
from nergal.dialog.styles import StyleType, get_style_prompt

# Import specialized agents from agents subpackage
from nergal.dialog.agents import (
    # Information gathering agents
    KnowledgeBaseAgent,
    TechDocsAgent,
    CodeAnalysisAgent,
    MetricsAgent,
    NewsAgent,
    NewsCluster,
    NewsSource,
    # Processing agents
    AnalysisAgent,
    FactCheckAgent,
    ComparisonAgent,
    SummaryAgent,
    ClarificationAgent,
    # Specialized agents
    ExpertiseAgent,
    ExpertiseDomain,
)

__all__ = [
    # Manager
    "DialogManager",
    "ProcessResult",
    "PlanExecutionResult",
    # Core agents
    "BaseAgent",
    "DefaultAgent",
    "DispatcherAgent",
    "AgentRegistry",
    "AgentResult",
    "AgentType",
    "AgentCategory",
    # Plan
    "ExecutionPlan",
    "PlanStep",
    # Context
    "DialogContext",
    "DialogState",
    "UserInfo",
    "ContextManager",
    # Styles
    "StyleType",
    "get_style_prompt",
    # Information gathering agents
    "KnowledgeBaseAgent",
    "TechDocsAgent",
    "CodeAnalysisAgent",
    "MetricsAgent",
    "NewsAgent",
    "NewsCluster",
    "NewsSource",
    # Processing agents
    "AnalysisAgent",
    "FactCheckAgent",
    "ComparisonAgent",
    "SummaryAgent",
    "ClarificationAgent",
    # Specialized agents
    "ExpertiseAgent",
    "ExpertiseDomain",
]
