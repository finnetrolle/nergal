"""Agent system for Nergal.

This module provides the core agent runtime including
tool call loop and exception handling.

Exported classes:
    - MaxIterationsExceeded: Raised when tool loop exceeds max iterations

Exported functions:
    - run_tool_call_loop: Main agentic loop for executing tools

Exported from submodules:
    - run_tool_call_loop: From loop module
    - MaxIterationsExceeded: From exceptions module
"""

from nergal.agent.exceptions import MaxIterationsExceeded
from nergal.agent.loop import run_tool_call_loop

__all__ = [
    "MaxIterationsExceeded",
    "run_tool_call_loop",
]
