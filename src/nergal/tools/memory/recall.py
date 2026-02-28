"""Memory recall tool for retrieving information from memory.

This tool allows the agent to retrieve relevant information from
the memory system.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nergal.memory.base import Memory, MemoryCategory
from nergal.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


class MemoryRecallTool(Tool):
    """Tool for recalling information from memory.

    This tool allows the agent to retrieve relevant information
    from the memory system based on a query.

    Args:
        memory: The Memory backend to use.

    Example:
        >>> from nergal.tools.memory import MemoryRecallTool
        >>>
        >>> tool = MemoryRecallTool(memory)
        >>> result = await tool.execute({
        ...     "query": "programming language",
        ...     "limit": 5,
        ... })
    """

    def __init__(
        self,
        memory: Memory,
    ) -> None:
        """Initialize the memory recall tool.

        Args:
            memory: The Memory backend to use.
        """
        self.memory = memory

    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "memory_recall"

    @property
    def description(self) -> str:
        """Human-readable description for the LLM."""
        return (
            "Retrieve relevant information from persistent memory. "
            "Use this to look up facts, user preferences, or "
            "other previously stored information."
        )

    @property
    def parameters_schema(self) -> dict:
        """JSON Schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for retrieving relevant memories.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of entries to return.",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                },
                "category": {
                    "type": "string",
                    "enum": ["conversation", "knowledge", "user", "system"],
                    "description": (
                        "Optional category filter. If not specified, "
                        "searches all categories."
                    ),
                },
            },
            "required": ["query"],
        }

    async def execute(self, args: dict) -> ToolResult:
        """Execute the tool with given arguments.

        Args:
            args: Dictionary of arguments from the LLM tool call.

        Returns:
            ToolResult containing retrieved entries or error.
        """
        query = args.get("query")
        limit = args.get("limit", 5)
        category_str = args.get("category")

        # Validate required arguments
        if not query:
            return ToolResult(
                success=False,
                output="",
                error="Missing required argument: query",
            )

        # Parse category if provided
        category = None
        if category_str:
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

        # Retrieve from memory
        try:
            entries = await self.memory.recall(
                query=query,
                limit=limit,
                category=category,
            )

            if not entries:
                return ToolResult(
                    success=True,
                    output="No relevant memories found for this query.",
                )

            # Format results
            output_lines = [f"Found {len(entries)} relevant memories:"]
            for entry in entries:
                score_str = f" (score: {entry.score:.2f})" if entry.score else ""
                output_lines.append(
                    f"- [{entry.category.value}] {entry.content}{score_str}"
                )

            logger.info(f"Recalled {len(entries)} memory entries for query: {query}")
            return ToolResult(
                success=True,
                output="\n".join(output_lines),
            )
        except Exception as e:
            logger.error(f"Failed to recall memory: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to recall memories: {str(e)}",
            )
