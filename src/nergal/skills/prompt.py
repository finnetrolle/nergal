"""Skills prompt section for system prompts.

This module provides functionality to build the skills
section of the system prompt from loaded skills.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nergal.skills.base import Skill

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def build_skills_prompt(
    skills: dict[str, Skill],
    skill_names: list[str] | None = None,
) -> str:
    """Build skills section for system prompt.

    Args:
        skills: Dictionary mapping skill names to Skill objects.
        skill_names: Optional list of skill names to include.
                     If None, includes all skills.

    Returns:
        Formatted skills section for system prompt.

    Example:
        >>> from nergal.skills.prompt import build_skills_prompt
        >>> skills_prompt = build_skills_prompt(loaded_skills)
        >>> system_prompt += f"\\n\\n{skills_prompt}\\n\\n"
    """
    if not skills:
        return ""

    # Determine which skills to include
    if skill_names:
        selected_skills = [skills[name] for name in skill_names if name in skills]
    else:
        selected_skills = list(skills.values())

    if not selected_skills:
        return ""

    lines = ["## Available Skills", ""]

    # Add skill descriptions
    for skill in selected_skills:
        lines.append(f"- **{skill.name}** ({skill.version}): {skill.description}")
        if skill.tags:
            tags_str = ", ".join(skill.tags)
            lines.append(f"  Tags: {tags_str}")

        # Add tools if any
        if skill.tools:
            tools_str = ", ".join([t.name for t in skill.tools])
            lines.append(f"  Tools: {tools_str}")

        # Add prompts if any
        all_prompts = []
        for skill in selected_skills:
            all_prompts.extend(skill.prompts)

        if all_prompts:
            lines.append("")
            lines.append("### Skill Guidelines")
            for i, prompt in enumerate(all_prompts, 1):
                lines.append(f"{i}. {prompt}")

    return "\n".join(lines)
