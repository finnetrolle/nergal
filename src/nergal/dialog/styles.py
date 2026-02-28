"""Response style definitions for the dialog system.

This module provides different response styles that can be applied to
customize the bot's personality and communication style.
"""

from enum import Enum


class StyleType(str, Enum):
    """Available response styles."""

    DEFAULT = "default"


# Default style - neutral, helpful assistant
DEFAULT_STYLE_PROMPT = """Ты полезный ассистент. Отвечай на русском языке, кратко и по делу. Если не знаешь ответа, честно признайся в этом."""


# Mapping of style types to their prompts
STYLE_PROMPTS: dict[StyleType, str] = {
    StyleType.DEFAULT: DEFAULT_STYLE_PROMPT,
}


def get_style_prompt(style_type: StyleType) -> str:
    """Get the system prompt for a given style type.

    Args:
        style_type: The type of style to get the prompt for.

    Returns:
        The system prompt string for the specified style.
    """
    return STYLE_PROMPTS.get(style_type, DEFAULT_STYLE_PROMPT)
