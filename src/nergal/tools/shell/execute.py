"""Shell command execution tool.

This module provides the ShellExecuteTool which allows the agent
to execute shell commands in a controlled manner with timeouts
and output limits.

Example:
    >>> from nergal.tools.shell.execute import ShellExecuteTool
    >>>
    >>> tool = ShellExecuteTool(
    ...     allowed_commands=["ls", "cat", "echo"],
    ...     timeout=30.0,
    ...     max_output_size=10000
    ... )
    >>>
    >>> result = await tool.execute({
    ...     "command": "ls -la /tmp"
    ... })
"""

from __future__ import annotations

import asyncio
import shlex
from typing import TYPE_CHECKING

from nergal.tools.base import Tool, ToolResult
from nergal.tools.exceptions import (
    SecurityPolicyViolationError,
    ToolExecutionError,
    ToolTimeoutError,
    ToolValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class ShellExecuteTool(Tool):
    """Tool for executing shell commands.

    This tool provides controlled execution of shell commands with:
    - Configurable command whitelist
    - Timeout enforcement
    - Output size limiting
    - Security policy integration

    Attributes:
        allowed_commands: List of allowed command base names (e.g., ["ls", "cat"]).
                          Empty list means all commands are allowed.
        timeout: Maximum execution time in seconds.
        max_output_size: Maximum size of combined stdout/stderr in bytes.
        working_dir: Working directory for command execution.

    Examples:
        Basic usage with command whitelist:
        >>> tool = ShellExecuteTool(allowed_commands=["ls", "cat"])

        With custom timeout and output limit:
        >>> tool = ShellExecuteTool(
        ...     allowed_commands=["docker"],
        ...     timeout=60.0,
        ...     max_output_size=50000
        ... )

        With working directory:
        >>> tool = ShellExecuteTool(
        ...     allowed_commands=["make"],
        ...     working_dir="/path/to/project"
        ... )
    """

    def __init__(
        self,
        allowed_commands: Sequence[str] | None = None,
        timeout: float = 30.0,
        max_output_size: int = 10000,
        working_dir: str | None = None,
    ) -> None:
        """Initialize the shell execute tool.

        Args:
            allowed_commands: List of allowed command base names.
                            Empty list means all commands are allowed.
            timeout: Maximum execution time in seconds. Default: 30.0.
            max_output_size: Maximum size of output in bytes. Default: 10000.
            working_dir: Working directory for command execution.

        Raises:
            ValueError: If timeout or max_output_size is not positive.
        """
        if timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {timeout}")

        if max_output_size <= 0:
            raise ValueError(f"Max output size must be positive, got {max_output_size}")

        self._allowed_commands = list(allowed_commands) if allowed_commands else []
        self._timeout = timeout
        self._max_output_size = max_output_size
        self._working_dir = working_dir

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "shell_execute"

    @property
    def description(self) -> str:
        """Return the tool description."""
        description = (
            "Execute a shell command and return the output. "
            "The command will be executed with a timeout. "
            "Output size is limited."
        )

        if self._allowed_commands:
            description += f" Allowed commands: {', '.join(self._allowed_commands)}."

        return description

    @property
    def parameters_schema(self) -> dict:
        """Return the JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "The shell command to execute. "
                        "Be careful with commands that modify system state."
                    ),
                },
            },
            "required": ["command"],
        }

    async def execute(self, args: dict) -> ToolResult:
        """Execute a shell command.

        Args:
            args: Dictionary containing:
                - command: The shell command to execute (required)

        Returns:
            ToolResult containing:
                - success: True if command succeeded
                - output: Combined stdout and stderr
                - error: Error message if execution failed
                - metadata: Return code and execution time

        Raises:
            ToolValidationError: If command argument is invalid.
            ToolTimeoutError: If command execution times out.
            ToolExecutionError: If command execution fails.
            SecurityPolicyViolationError: If command is not in allowed list.
        """
        # Validate arguments
        command = args.get("command")
        if not isinstance(command, str):
            raise ToolValidationError(
                tool_name=self.name,
                field="command",
                message="Command must be a non-empty string",
            )

        command = command.strip()
        if not command:
            raise ToolValidationError(
                tool_name=self.name,
                field="command",
                message="Command cannot be empty or whitespace",
            )

        # Check command whitelist
        if self._allowed_commands:
            try:
                # Parse the command to get the base command name
                parts = shlex.split(command)
                if not parts:
                    raise ToolValidationError(
                        tool_name=self.name,
                        field="command",
                        message="Could not parse command",
                    )

                base_command = parts[0]
                if base_command not in self._allowed_commands:
                    raise SecurityPolicyViolationError(
                        tool_name=self.name,
                        reason=(
                            f"Command '{base_command}' is not in the allowed commands list. "
                            f"Allowed commands: {', '.join(self._allowed_commands)}"
                        ),
                    )
            except ValueError as e:
                raise ToolValidationError(
                    tool_name=self.name,
                    field="command",
                    message=f"Invalid command format: {e}",
                ) from e

        # Execute command
        import time

        start_time = time.time()

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._working_dir,
            )

            # Wait for process with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout,
            )

        except asyncio.TimeoutError as e:
            # Kill the process if it timed out
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass

            raise ToolTimeoutError(
                tool_name=self.name,
                timeout=self._timeout,
            ) from e

        except Exception as e:
            raise ToolExecutionError(
                tool_name=self.name,
                message=f"Failed to execute command: {e}",
            ) from e

        # Decode output
        try:
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")
        except UnicodeDecodeError as e:
            raise ToolExecutionError(
                tool_name=self.name,
                message=f"Failed to decode command output: {e}",
            ) from e

        # Enforce output size limit
        total_size = len(stdout_text) + len(stderr_text)
        if total_size > self._max_output_size:
            stdout_text = stdout_text[: self._max_output_size // 2]
            stderr_text = stderr_text[: self._max_output_size // 2]
            stderr_text += f"\n[Output truncated to {self._max_output_size} bytes]"

        execution_time = time.time() - start_time

        # Build output
        output_parts = []
        if stdout_text:
            output_parts.append(f"STDOUT:\n{stdout_text}")
        if stderr_text:
            output_parts.append(f"STDERR:\n{stderr_text}")

        combined_output = "\n\n".join(output_parts) if output_parts else ""

        # Check return code
        return_code = process.returncode or 0

        if return_code != 0:
            error = f"Command failed with exit code {return_code}"
            if stderr_text:
                error += f": {stderr_text[:200]}"
            return ToolResult(
                success=False,
                output=combined_output,
                error=error,
                metadata={
                    "return_code": return_code,
                    "execution_time": execution_time,
                },
            )

        return ToolResult(
            success=True,
            output=combined_output,
            metadata={
                "return_code": return_code,
                "execution_time": execution_time,
                "output_size": total_size,
            },
        )
