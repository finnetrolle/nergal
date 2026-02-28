"""Agent system for Nergal.

This module provides the core agent runtime including
tool call loop, exception handling, and agent orchestration.

Exported classes:
    - MaxIterationsExceeded: Raised when tool loop exceeds max iterations
    - AgentRuntime: Main orchestrator for all agent components

Exported functions:
    - run_tool_call_loop: Main agentic loop for executing tools

Exported from submodules:
    - run_tool_call_loop: From loop module
    - MaxIterationsExceeded: From exceptions module
    - AgentRuntime: From runtime module
"""

from nergal.agent.exceptions import MaxIterationsExceeded
from nergal.agent.loop import run_tool_call_loop

__all__ = [
    "MaxIterationsExceeded",
    "AgentRuntime",
    "run_tool_call_loop",
]
