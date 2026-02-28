"""FileWriteTool implementation.

This module provides the FileWriteTool which allows the agent
to write files to a configured workspace directory.
"""

from __future__ import annotations

import logging
from pathlib import Path

from nergal.tools.base import Tool, ToolResult

logger = logging.getLogger(__name__)


class FileWriteTool(Tool):
    """Tool for writing files to the workspace directory.

    This tool allows the agent to write files within
    the configured workspace directory. It implements security checks
    to prevent path traversal attacks.

    Attributes:
        workspace_dir: The base directory for file operations.

    Example:
        >>> tool = FileWriteTool(workspace_dir="/tmp/nergal")
        >>> result = await tool.execute({
        ...     "path": "output.txt",
        ...     "content": "Hello, World!"
        ... })
        >>> print(result.output)
    """

    def __init__(self, workspace_dir: str | Path) -> None:
        """Initialize FileWriteTool.

        Args:
            workspace_dir: The base directory for file operations.
                          All file paths are resolved
                          relative to this directory.
        """
        self.workspace_dir = Path(workspace_dir).resolve()

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "file_write"

    @property
    def description(self) -> str:
        """Return the tool description."""
        return "Write content to a file in the workspace directory"

    @property
    def parameters_schema(self) -> dict:
        """Return JSON Schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write (relative to workspace)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
                "create": {
                    "type": "boolean",
                    "description": "If True, create parent directories. If False, fail if file exists.",
                    "default": False,
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, args: dict) -> ToolResult:
        """Execute file write operation.

        Args:
            args: Dictionary with 'path', 'content', and optional 'create' keys.

        Returns:
            ToolResult with success status and file path or error message.
        """
        file_path = args.get("path")
        content = args.get("content")
        create = args.get("create", False)

        if not file_path:
            return ToolResult(
                success=False,
                output="",
                error="Missing required parameter: path",
            )

        if content is None:
            return ToolResult(
                success=False,
                output="",
                error="Missing required parameter: content",
            )

        # Resolve path and check security
        try:
            resolved_path = self.workspace_dir / file_path
            resolved_path = resolved_path.resolve()

            # Security check: ensure path is within workspace
            if not resolved_path.is_relative_to(self.workspace_dir):
                logger.warning(
                    f"Attempted to write outside workspace: {resolved_path}"
                )
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path outside workspace: {file_path}",
                )

            # Create parent directories if they don't exist
            parent = resolved_path.parent
            if parent != self.workspace_dir and not parent.exists():
                logger.info(f"Creating directory: {parent}")
                parent.mkdir(parents=True)

            # Check if file exists when create=True (don't overwrite)
            file_exists = resolved_path.exists()
            if file_exists and create:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File already exists: {file_path}",
                )

            # Write content (text mode by default, binary mode if content is bytes)
            if isinstance(content, bytes):
                resolved_path.write_bytes(content)
            else:
                resolved_path.write_text(content)
            logger.info(f"Successfully wrote file: {resolved_path}")
            return ToolResult(
                success=True,
                output=f"Written to: {file_path}",
            )

        except PermissionError as e:
            logger.error(f"Permission denied writing file {resolved_path}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied: {file_path}",
            )

        except OSError as e:
            logger.error(f"OS error writing file {resolved_path}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"OS error: {str(e)}",
            )

        except Exception as e:
            logger.error(f"Unexpected error writing file {resolved_path}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Unexpected error: {str(e)}",
            )
