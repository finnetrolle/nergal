"""Base classes and interfaces for Skill system.

This module provides the core data structures for the skill system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class SkillTool:
    """A tool defined within a skill.

    Skills can define custom tools that extend the agent's
    capabilities beyond the base tools.

    Attributes:
        name: The tool name (unique within the skill).
        description: Human-readable description for the LLM.
        kind: The type of tool (shell, script, etc.).
        command_or_path: The command or script path to execute.
        timeout: Optional timeout for execution.
    """

    name: str
    """The tool name (unique within the skill)."""

    description: str
    """Human-readable description for the LLM."""

    kind: str = "shell"
    """The type of tool (shell, script, etc.)."""

    command_or_path: str = ""
    """The command or script path to execute."""

    timeout: int | None = field(default=None)
    """Optional timeout for execution in seconds."""


@dataclass
class Skill:
    """Domain-specific skill.

    A skill represents a set of related capabilities for
    a specific domain (e.g., deployment, code review).

    Attributes:
        name: Unique skill identifier.
        description: Human-readable description.
        version: Skill version.
        tags: List of tags for categorization.
        tools: List of tools defined in this skill.
        prompts: List of prompt snippets to inject.
        location: Path to the skill directory.
    """

    name: str
    """Unique skill identifier."""

    description: str
    """Human-readable description."""

    version: str = "1.0.0"
    """Skill version."""

    tags: list[str] = field(default_factory=list)
    """List of tags for categorization."""

    tools: list[SkillTool] = field(default_factory=list)
    """List of tools defined in this skill."""

    prompts: list[str] = field(default_factory=list)
    """List of prompt snippets to inject."""

    location: Path | None = field(default=None)
    """Path to the skill directory."""

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"
