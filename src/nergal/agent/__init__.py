"""Agent system for Nergal.

This module provides the core agent runtime including
tool call loop, exception handling, and agent orchestration.

Exported classes:
    - MaxIterationsExceeded: Raised when tool loop exceeds max iterations
    - AgentRuntime: Main orchestrator for all agent components
    - ConversationHistoryManager: Manages per-user conversation history

Exported functions:
    - run_tool_call_loop: Main agentic loop for executing tools

Exported from submodules:
    - run_tool_call_loop: From loop module
    - MaxIterationsExceeded: From exceptions module
    - AgentRuntime: From runtime module
    - ConversationHistoryManager: From runtime module
"""

from nergal.agent.exceptions import MaxIterationsExceeded
from nergal.agent.loop import run_tool_call_loop
from nergal.agent.runtime import AgentRuntime, ConversationHistoryManager

__all__ = [
    "MaxIterationsExceeded",
    "AgentRuntime",
    "ConversationHistoryManager",
    "run_tool_call_loop",
]
