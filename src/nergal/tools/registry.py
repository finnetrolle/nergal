"""Tool registry for managing available tools.

This module provides the ToolRegistry class which manages
the collection of available tools in the system.

Example:
    >>> from nergal.tools.registry import ToolRegistry
    >>> from my_tools import FileReadTool
    >>>
    >>> registry = ToolRegistry()
    >>> registry.register(FileReadTool())
    >>>
    >>> tool = registry.get_tool("file_read")
    >>> if tool:
    ...     result = await tool.execute({"path": "/tmp/file.txt"})
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nergal.tools.base import Tool


class ToolRegistry:
    """Registry for managing available tools.

    The ToolRegistry maintains a collection of tools and provides
    methods to register, unregister, and retrieve tools.

    Tools are indexed by their name property, which must be unique.

    Attributes:
        _tools: Internal dictionary mapping tool names to tool instances.

    Examples:
        >>> registry = ToolRegistry()
        >>> registry.register(MyTool())
        >>> registry.get_tool("my_tool")  # Returns MyTool instance
        >>> registry.list_tools()  # Returns list of all tools
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool in the registry.

        If a tool with the same name already exists,
        it will be overwritten with the new tool.

        Args:
            tool: The tool instance to register.

        Examples:
            >>> registry = ToolRegistry()
            >>> registry.register(FileReadTool())
        """
        if not tool.name:
            raise ValueError("Tool name cannot be empty")

        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool from the registry.

        If the tool doesn't exist, this method does nothing.

        Args:
            name: The name of the tool to unregister.

        Examples:
            >>> registry.unregister("file_read")
        """
        self._tools.pop(name, None)

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            The tool instance if found, None otherwise.

        Examples:
            >>> tool = registry.get_tool("file_read")
            >>> if tool:
            ...     print(f"Found tool: {tool.name}")
        """
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """Get a list of all registered tools.

        Returns a copy of the internal tools list to prevent
        external modifications.

        Returns:
            List of all registered tool instances.

        Examples:
            >>> for tool in registry.list_tools():
            ...     print(f"- {tool.name}: {tool.description}")
        """
        return list(self._tools.values())

    def get_tool_names(self) -> list[str]:
        """Get a list of all registered tool names.

        Returns:
            List of tool name strings.

        Examples:
            >>> names = registry.get_tool_names()
            >>> # ["file_read", "file_write", "shell_execute"]
        """
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: The name of the tool to check.

        Returns:
            True if the tool is registered, False otherwise.

        Examples:
            >>> if registry.has_tool("file_read"):
            ...     print("File reading is available")
        """
        return name in self._tools

    def count(self) -> int:
        """Get the number of registered tools.

        Returns:
            Number of tools in the registry.

        Examples:
            >>> print(f"Available tools: {registry.count()}")
        """
        return len(self._tools)

    def clear(self) -> None:
        """Clear all tools from the registry.

        Examples:
            >>> registry.clear()
        """
        self._tools.clear()


def get_registry() -> ToolRegistry:
    """Get or create the global tool registry.

    This provides a singleton pattern for accessing the
    tool registry throughout the application.

    Returns:
        The global ToolRegistry instance.

    Examples:
        >>> from nergal.tools.registry import get_registry
        >>> registry = get_registry()
        >>> registry.get_tool("file_read")
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = ToolRegistry()

    return _global_registry


# Global registry instance
_global_registry: ToolRegistry | None = None
