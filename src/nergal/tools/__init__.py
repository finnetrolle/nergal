"""Tool system for Nergal.

This module provides the core tool system abstractions
and utilities for managing tool execution.

Exported classes:
    - Tool: Abstract base class for all tools
    - ToolResult: Dataclass for tool execution results
    - ToolRegistry: Registry for managing available tools
    - get_registry: Factory function for global registry

Exported from submodules:
    - Tool: From base module
    - ToolResult: From base module
    - ToolRegistry: From registry module
    - get_registry: From registry module
"""

from nergal.tools.base import Tool, ToolResult
from nergal.tools.registry import ToolRegistry, get_registry

__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "get_registry",
]
