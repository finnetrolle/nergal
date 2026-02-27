"""Agent implementations for the dialog system.

This package contains specialized agents for handling different
types of user requests. Each agent is designed for a specific
domain or task.

Base classes and types are imported from base.py.

Available agents:
- WebSearchAgent: Search the web for information
- AnalysisAgent: Analyze and synthesize information
- TechDocsAgent: Search technical documentation
- SummaryAgent: Summarize and condense information
- CodeAnalysisAgent: Analyze code and repositories
- MetricsAgent: Retrieve metrics and statistics
- NewsAgent: Aggregate and process news from multiple sources
- TodoistAgent: Manage tasks in Todoist
"""

# Import base classes first (from parent module base.py)
from nergal.dialog.base import (
    AgentCategory,
    AgentRegistry,
    AgentResult,
    AgentType,
    BaseAgent,
    ExecutionPlan,
    PlanStep,
)

# Import base specialized agent class
from nergal.dialog.agents.base_specialized import (
    BaseSpecializedAgent,
    ContextAwareAgent,
)

# Import specialized agents
from nergal.dialog.agents.analysis_agent import AnalysisAgent
from nergal.dialog.agents.code_analysis_agent import CodeAnalysisAgent
from nergal.dialog.agents.metrics_agent import MetricsAgent
from nergal.dialog.agents.news_agent import NewsAgent, NewsCluster, NewsSource
from nergal.dialog.agents.summary_agent import SummaryAgent
from nergal.dialog.agents.tech_docs_agent import TechDocsAgent
from nergal.dialog.agents.todoist_agent import TodoistAgent
from nergal.dialog.agents.web_search_agent import WebSearchAgent

__all__ = [
    # Base classes and types
    "AgentCategory",
    "AgentRegistry",
    "AgentResult",
    "AgentType",
    "BaseAgent",
    "BaseSpecializedAgent",
    "ContextAwareAgent",
    "ExecutionPlan",
    "PlanStep",
    
    # Information gathering agents
    "WebSearchAgent",
    "TechDocsAgent",
    "CodeAnalysisAgent",
    "MetricsAgent",
    "NewsAgent",
    "NewsSource",
    "NewsCluster",
    
    # Processing agents
    "AnalysisAgent",
    "SummaryAgent",

    # Specialized agents
    "TodoistAgent",
]
