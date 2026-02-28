"""FileReadTool implementation.

This module provides the FileReadTool which allows the agent
to read files from a configured workspace directory.
"""

from __future__ import annotations

import logging
from pathlib import Path

from nergal.tools.base import Tool, ToolResult

logger = logging.getLogger(__name__)


class FileReadTool(Tool):
    """Tool for reading files from the workspace directory.

    This tool allows the agent to read file contents within
    the configured workspace directory. It implements security checks
    to prevent path traversal attacks.

    Attributes:
        workspace_dir: The base directory for file operations.

    Example:
        >>> tool = FileReadTool(workspace_dir="/tmp/nergal")
        >>> result = await tool.execute({"path": "config.json"})
        >>> print(result.output)
    """

    def __init__(self, workspace_dir: str | Path) -> None:
        """Initialize the FileReadTool.

        Args:
            workspace_dir: The base directory for file operations.
                          All file paths are resolved
                          relative to this directory.
        """
        self.workspace_dir = Path(workspace_dir).resolve()

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "file_read"

    @property
    def description(self) -> str:
        """Return the tool description."""
        return "Read the contents of a file from the workspace directory"

    @property
    def parameters_schema(self) -> dict:
        """Return JSON Schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read, relative to workspace directory",
                },
            },
            "required": ["path"],
        }

    async def execute(self, args: dict) -> ToolResult:
        """Execute the file read operation.

        Args:
            args: Dictionary with 'path' key specifying the file to read.

        Returns:
            ToolResult with the file contents or error message.
        """
        file_path = args.get("path")

        if not file_path:
            return ToolResult(
                success=False,
                output="",
                error="Missing required parameter: path",
            )

        # Resolve the path and check security
        try:
            resolved_path = self.workspace_dir / file_path
            resolved_path = resolved_path.resolve()

            # Security check: ensure path is within workspace
            if not resolved_path.is_relative_to(self.workspace_dir):
                logger.warning(f"Attempted to access path outside workspace: {resolved_path}")
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path outside workspace: {file_path}",
                )

            # Check if file exists
            if not resolved_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {file_path}",
                )

            # Check if path is a file (not directory)
            if not resolved_path.is_file():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path is not a file: {file_path}",
                )

            # Read file content
            try:
                content = resolved_path.read_text(encoding="utf-8")
                logger.debug(f"Successfully read file: {file_path}")
                return ToolResult(success=True, output=content)

            except UnicodeDecodeError as e:
                logger.error(f"Failed to decode file {file_path}: {e}")
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to decode file (not UTF-8): {file_path}",
                )

            except PermissionError as e:
                logger.error(f"Permission denied reading file {file_path}: {e}")
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Permission denied: {file_path}",
                )

            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Error reading file: {str(e)}",
                )

        except Exception as e:
            logger.error(f"Unexpected error processing file read: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Unexpected error: {str(e)}",
            )
