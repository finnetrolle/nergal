"""Tool system for Nergal.

This module provides the core tool system abstractions
and utilities for managing tool execution.

Exported classes:
    - Tool: Abstract base class for all tools
    - ToolResult: Dataclass for tool execution results
    - ToolRegistry: Registry for managing available tools
    - get_registry: Factory function for global registry
"""

from nergal.tools.base import Tool, ToolResult
from nergal.tools.exceptions import (
    SecurityPolicyViolationError,
    ToolError,
    ToolExecutionError,
    ToolTimeoutError,
    ToolValidationError,
)
from nergal.tools.files.read import FileReadTool
from nergal.tools.files.write import FileWriteTool
from nergal.tools.http.request import HttpRequestTool
from nergal.tools.registry import ToolRegistry, get_registry
from nergal.tools.search.web import WebSearchTool
from nergal.tools.shell.execute import ShellExecuteTool
from nergal.tools.stt.transcribe import TranscribeTool

__all__ = [
    # Core
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "get_registry",
    # Exceptions
    "ToolError",
    "ToolExecutionError",
    "ToolTimeoutError",
    "ToolValidationError",
    "SecurityPolicyViolationError",
    # Tools
    "HttpRequestTool",
    "FileReadTool",
    "FileWriteTool",
    "ShellExecuteTool",
    "WebSearchTool",
    "TranscribeTool",
]
