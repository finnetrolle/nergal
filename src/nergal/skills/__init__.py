"""Skill system for domain-specific agent capabilities.

This package provides the skill loading system for defining
domain-specific capabilities that extend the agent's abilities.

Components:
    - base: Skill dataclass and interfaces
    - loader: Skill loader from files
    - prompt: Skills prompt section for system prompts
"""

from nergal.skills.loader import SkillLoader, load_skills
from nergal.skills.prompt import build_skills_prompt

__all__ = ["SkillLoader", "load_skills", "build_skills_prompt"]
