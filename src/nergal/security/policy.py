"""Security policy for controlling agent behavior.

This module provides the SecurityPolicy class which enforces
rules and restrictions on agent actions based on autonomy level.
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


class AutonomyLevel(Enum):
    """Agent autonomy levels for tool execution.

    Determines what actions the agent can take without approval:

    READ_ONLY: Agent can only read, no modifications
    LIMITED: Agent can modify with some restrictions
    FULL: Agent has full autonomy (dangerous!)
    """

    READ_ONLY = "read_only"
    """Agent can only read, no modifications allowed."""

    LIMITED = "limited"
    """Agent can modify with some restrictions."""

    FULL = "full"
    """Agent has full autonomy (dangerous in production!)."""


@dataclass
class SecurityPolicy:
    """Security policy for tool execution.

    Enforces rules and restrictions based on autonomy level.
    Provides path validation, command filtering, and tool access control.

    Args:
        autonomy_level: The autonomy level for the agent.
        workspace_dir: Directory where file operations are allowed.
        allowed_commands: Whitelist of allowed shell commands.
        workspace_only: If True, restrict file access to workspace.
        allowed_domains: Whitelist of allowed HTTP domains.

    Example:
        >>> from nergal.security.policy import SecurityPolicy, AutonomyLevel
        >>>
        >>> policy = SecurityPolicy(
        ...     autonomy_level=AutonomyLevel.LIMITED,
        ...     workspace_dir="~/.nergal/workspace",
        ...     allowed_commands=["ls", "cat", "grep"],
        ... )
    """

    autonomy_level: AutonomyLevel
    """The autonomy level for the agent."""

    workspace_dir: Path
    """Directory where file operations are allowed."""

    allowed_commands: list[str]
    """Whitelist of allowed shell commands (empty = no commands)."""

    workspace_only: bool = True
    """If True, restrict file access to workspace directory."""

    allowed_domains: list[str] | None = None
    """Whitelist of allowed HTTP domains (empty = no restriction)."""

    # Tool access control
    forbidden_tools: set[str] | None = None
    """Set of tool names that are always forbidden."""

    def __init__(
        self,
        autonomy_level: AutonomyLevel,
        workspace_dir: Path | str,
        allowed_commands: list[str] | None = None,
        workspace_only: bool = True,
        allowed_domains: list[str] | None = None,
        forbidden_tools: set[str] | None = None,
    ) -> None:
        """Initialize security policy.

        Args:
            autonomy_level: The autonomy level for the agent.
            workspace_dir: Directory where file operations are allowed.
            allowed_commands: Whitelist of allowed shell commands.
            workspace_only: If True, restrict file access to workspace.
            allowed_domains: Whitelist of allowed HTTP domains.
            forbidden_tools: Set of tool names that are always forbidden.
        """
        self.autonomy_level = autonomy_level
        self.workspace_dir = (
            Path(workspace_dir).expanduser()
            if isinstance(workspace_dir, str)
            else workspace_dir
        )
        self.allowed_commands = allowed_commands or []
        self.workspace_only = workspace_only
        self.allowed_domains = allowed_domains
        self.forbidden_tools = forbidden_tools

    def is_tool_allowed(self, tool_name: str) -> tuple[bool, str | None]:
        """Check if a tool can be used.

        Args:
            tool_name: The name of the tool to check.

        Returns:
            Tuple of (allowed, reason). If not allowed, reason explains why.
        """
        # Check forbidden tools
        if self.forbidden_tools and tool_name in self.forbidden_tools:
            return (
                False,
                f"Tool '{tool_name}' is forbidden by security policy",
            )

        # Check autonomy level restrictions
        if self.autonomy_level == AutonomyLevel.READ_ONLY:
            dangerous_tools = {
                "file_write",
                "shell_execute",
                "http_request",
            }
            if tool_name in dangerous_tools:
                return (
                    False,
                    f"Tool '{tool_name}' not allowed in read-only mode",
                )

        return (True, None)

    def is_path_allowed(self, path: Path | str) -> tuple[bool, str | None]:
        """Check if a path is within allowed bounds.

        Args:
            path: The path to check.

        Returns:
            Tuple of (allowed, reason). If not allowed, reason explains why.
        """
        if isinstance(path, str):
            path = Path(path)

        # Resolve to absolute path
        try:
            abs_path = path.resolve()
            workspace_abs = self.workspace_dir.resolve()
        except (OSError, RuntimeError) as e:
            logger.warning(f"Failed to resolve path: {e}")
            return (False, f"Invalid path: {path}")

        # Check workspace restriction
        if self.workspace_only:
            # Check if path is within workspace
            try:
                abs_path.relative_to(workspace_abs)
            except ValueError:
                return (
                    False,
                    f"Path '{path}' is outside workspace directory",
                )

        # Check for directory traversal
        if ".." in str(path):
            return (False, f"Path contains directory traversal: {path}")

        return (True, None)

    def is_command_allowed(self, command: str) -> tuple[bool, str | None]:
        """Check if a command is allowed.

        Args:
            command: The command to check.

        Returns:
            Tuple of (allowed, reason). If not allowed, reason explains why.
        """
        # Extract base command (first word)
        base_command = command.split()[0] if command else ""

        # Check if whitelist is empty (no commands allowed)
        if not self.allowed_commands and base_command:
            return (
                False,
                f"No commands are whitelisted (command: '{command}')",
            )

        # Check against whitelist
        if self.allowed_commands and base_command not in self.allowed_commands:
            # Try pattern matching
            for pattern in self.allowed_commands:
                if fnmatch.fnmatch(base_command, pattern):
                    return (True, None)
            return (
                False,
                f"Command '{base_command}' not in allowed list",
            )

        return (True, None)

    def is_domain_allowed(self, domain: str) -> tuple[bool, str | None]:
        """Check if a domain is allowed for HTTP requests.

        Args:
            domain: The domain to check (e.g., 'example.com').

        Returns:
            Tuple of (allowed, reason). If not allowed, reason explains why.
        """
        # No domain restriction
        if not self.allowed_domains:
            return (True, None)

        # Check against whitelist
        domain_lower = domain.lower()
        for allowed in self.allowed_domains:
            if fnmatch.fnmatch(domain_lower, allowed.lower()):
                return (True, None)

        return (
            False,
            f"Domain '{domain}' not in allowed list",
        )

    def get_autonomy_level(self) -> AutonomyLevel:
        """Get current autonomy level.

        Returns:
            The current autonomy level.
        """
        return self.autonomy_level

    def set_autonomy_level(self, level: AutonomyLevel) -> None:
        """Change the autonomy level.

        Args:
            level: New autonomy level.
        """
        logger.info(f"Autonomy level changed to: {level.value}")
        self.autonomy_level = level
