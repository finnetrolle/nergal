"""Skill loader for loading skills from files.

This module provides functionality to load skills from
SKILL.md files in the skills directory.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from nergal.skills.base import Skill, SkillTool

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SkillLoader:
    """Loader for skills from SKILL.md files.

    Skills are stored as SKILL.md files with YAML manifests
    in the skills directory structure:

    ~/.nergal/skills/
    ├── deployment/
    │   └── SKILL.md
    ├── code_review/
    │   └── SKILL.md
    └── ...

    Args:
        skills_dir: Directory containing skill definitions.

    Example:
        >>> from nergal.skills.loader import SkillLoader
        >>>
        >>> loader = SkillLoader("~/.nergal/skills")
        >>> skills = loader.load_all()
    """

    def __init__(
        self,
        skills_dir: str | Path,
    ) -> None:
        """Initialize skill loader.

        Args:
            skills_dir: Directory containing skill definitions.
        """
        self.skills_dir = (
            Path(skills_dir).expanduser() if isinstance(skills_dir, str) else skills_dir
        )

    def load_all(self) -> dict[str, Skill]:
        """Load all skills from the skills directory.

        Returns:
            Dictionary mapping skill names to Skill objects.
        """
        skills = {}

        if not self.skills_dir.exists():
            logger.warning(f"Skills directory does not exist: {self.skills_dir}")
            return skills

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                logger.debug(f"No SKILL.md found in {skill_dir.name}")
                continue

            try:
                skill = self._load_skill(skill_dir, skill_file)
                if skill:
                    skills[skill.name] = skill
                    logger.info(f"Loaded skill: {skill.name}")
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_dir.name}: {e}")

        return skills

    def _load_skill(
        self,
        skill_dir: Path,
        skill_file: Path,
    ) -> Skill | None:
        """Load a skill from SKILL.md file.

        Args:
            skill_dir: The skill directory.
            skill_file: The SKILL.md file.

        Returns:
            Skill object or None if failed.
        """
        content = skill_file.read_text(encoding="utf-8")

        # Parse YAML sections
        # The file format is: ---
        # metadata
        # ---
        # content
        # ---
        sections = content.split("---")

        if len(sections) < 3:
            logger.warning(f"Invalid SKILL.md format in {skill_dir.name}")
            return None

        # Parse metadata section (YAML)
        try:
            metadata = yaml.safe_load(sections[1])
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse skill metadata: {e}")
            return None

        skill_info = metadata.get("skill", {})
        name = skill_info.get("name", skill_dir.name)
        description = skill_info.get("description", "")
        version = skill_info.get("version", "1.0.0")
        tags = skill_info.get("tags", [])

        # Parse tools section (YAML)
        tools_def = metadata.get("tools", [])
        tools = [
            SkillTool(
                name=tool_def.get("name", ""),
                description=tool_def.get("description", ""),
                kind=tool_def.get("kind", "shell"),
                command_or_path=tool_def.get("command", tool_def.get("path", "")),
                timeout=tool_def.get("timeout"),
            )
            for tool_def in tools_def
        ]

        # Parse prompts section
        prompts_def = metadata.get("prompts", [])
        prompts = [str(p) for p in prompts_def]

        return Skill(
            name=name,
            description=description,
            version=version,
            tags=tags,
            tools=tools,
            prompts=prompts,
            location=skill_dir,
        )


def load_skills(skills_dir: str | Path) -> dict[str, Skill]:
    """Convenience function to load all skills.

    Args:
        skills_dir: Directory containing skill definitions.

    Returns:
        Dictionary mapping skill names to Skill objects.

    Example:
        >>> from nergal.skills.loader import load_skills
        >>> skills = load_skills("~/.nergal/skills")
    """
    loader = SkillLoader(skills_dir)
    return loader.load_all()
