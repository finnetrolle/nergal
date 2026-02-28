"""Memory store tool for storing information in memory.

This tool allows the agent to store information in the memory system
for later retrieval.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nergal.memory.base import Memory, MemoryCategory
from nergal.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


class MemoryStoreTool(Tool):
    """Tool for storing information in memory.

    This tool allows the agent to persist information in the
    memory system for later retrieval and context building.

    Args:
        memory: The Memory backend to use.
        category_provider: Optional function to determine category.

    Example:
        >>> from nergal.tools.memory import MemoryStoreTool
        >>>
        >>> tool = MemoryStoreTool(memory)
        >>> result = await tool.execute({
        ...     "key": "fact_1",
        ...     "content": "Python was created in 1991",
        ...     "category": "knowledge",
        ... })
    """

    def __init__(
        self,
        memory: Memory,
        category_provider: Callable[[dict], MemoryCategory] | None = None,
    ) -> None:
        """Initialize the memory store tool.

        Args:
            memory: The Memory backend to use.
            category_provider: Optional function to determine category
                              from arguments.
        """
        self.memory = memory
        self.category_provider = category_provider

    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "memory_store"

    @property
    def description(self) -> str:
        """Human-readable description for the LLM."""
        return (
            "Store information in persistent memory for later retrieval. "
            "Use this to save important facts, user preferences, or "
            "knowledge that should be remembered across conversations."
        )

    @property
    def parameters_schema(self) -> dict:
        """JSON Schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": (
                        "Unique identifier for this memory entry. "
                        "Use descriptive keys like 'user_pref_language' or "
                        "'fact_python_origin'."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "The content to store. Keep it concise but complete.",
                },
                "category": {
                    "type": "string",
                    "enum": ["conversation", "knowledge", "user", "system"],
                    "description": "Category for the memory entry.",
                    "default": "knowledge",
                },
            },
            "required": ["key", "content"],
        }

    async def execute(self, args: dict) -> ToolResult:
        """Execute the tool with given arguments.

        Args:
            args: Dictionary of arguments from the LLM tool call.

        Returns:
            ToolResult indicating success or failure.
        """
        key = args.get("key")
        content = args.get("content")
        category_str = args.get("category", "knowledge")

        # Validate required arguments
        if not key:
            return ToolResult(
                success=False,
                output="",
                error="Missing required argument: key",
            )

        if not content:
            return ToolResult(
                success=False,
                output="",
                error="Missing required argument: content",
            )

        # Parse category
        try:
            category = MemoryCategory(category_str)
        except ValueError:
            return ToolResult(
                success=False,
                output="",
                error=(
                    f"Invalid category: {category_str}. "
                    "Valid options: conversation, knowledge, user, system"
                ),
            )

        # Store in memory
        try:
            await self.memory.store(
                key=key,
                content=content,
                category=category,
            )
            logger.info(f"Stored memory entry: {key} ({category.value})")
            return ToolResult(
                success=True,
                output=f"Successfully stored memory entry: {key}",
            )
        except Exception as e:
            logger.error(f"Failed to store memory entry: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to store memory: {str(e)}",
            )
