"""Agent implementations for the dialog system.

This package contains specialized agents for handling different
types of user requests. Each agent is designed for a specific
domain or task.

Base classes and types are imported from base.py.

Available agents:
- KnowledgeBaseAgent: Search corporate knowledge base
- ClarificationAgent: Clarify ambiguous queries
- AnalysisAgent: Analyze and synthesize information
- FactCheckAgent: Verify facts and claims
- TechDocsAgent: Search technical documentation
- ComparisonAgent: Compare alternatives
- SummaryAgent: Summarize and condense information
- CodeAnalysisAgent: Analyze code and repositories
- MetricsAgent: Retrieve metrics and statistics
- ExpertiseAgent: Domain-specific expertise
- NewsAgent: Aggregate and process news from multiple sources
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

# Import specialized agents
from nergal.dialog.agents.analysis_agent import AnalysisAgent
from nergal.dialog.agents.clarification_agent import ClarificationAgent
from nergal.dialog.agents.code_analysis_agent import CodeAnalysisAgent
from nergal.dialog.agents.comparison_agent import ComparisonAgent
from nergal.dialog.agents.expertise_agent import ExpertiseAgent, ExpertiseDomain
from nergal.dialog.agents.fact_check_agent import FactCheckAgent
from nergal.dialog.agents.knowledge_base_agent import KnowledgeBaseAgent
from nergal.dialog.agents.metrics_agent import MetricsAgent
from nergal.dialog.agents.news_agent import NewsAgent, NewsCluster, NewsSource
from nergal.dialog.agents.summary_agent import SummaryAgent
from nergal.dialog.agents.tech_docs_agent import TechDocsAgent

__all__ = [
    # Base classes and types
    "AgentCategory",
    "AgentRegistry",
    "AgentResult",
    "AgentType",
    "BaseAgent",
    "ExecutionPlan",
    "PlanStep",
    
    # Information gathering agents
    "KnowledgeBaseAgent",
    "TechDocsAgent",
    "CodeAnalysisAgent",
    "MetricsAgent",
    "NewsAgent",
    "NewsSource",
    "NewsCluster",
    
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
