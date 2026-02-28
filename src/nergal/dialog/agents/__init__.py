"""Agent implementations for the dialog system.

This package contains specialized agents for handling different
types of user requests. Each agent is designed for a specific
domain or task.

Base classes and types are imported from base.py.

Available agents:
- WebSearchAgent: Search the web for information
"""

# Import base classes first (from parent module base.py)
# Import base specialized agent class
from nergal.dialog.agents.base_specialized import BaseSpecializedAgent

# Import specialized agents
from nergal.dialog.agents.web_search_agent import WebSearchAgent
from nergal.dialog.base import (
    AgentCategory,
    AgentRegistry,
    AgentResult,
    AgentType,
    BaseAgent,
    ExecutionPlan,
    PlanStep,
)

__all__ = [
    # Base classes and types
    "AgentCategory",
    "AgentRegistry",
    "AgentResult",
    "AgentType",
    "BaseAgent",
    "BaseSpecializedAgent",
    "ExecutionPlan",
    "PlanStep",

    # Information gathering agents
    "WebSearchAgent",
]
