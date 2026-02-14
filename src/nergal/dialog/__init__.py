"""Dialog management module for handling user conversations.

This module provides a complete system for managing dialogs with users,
including agent-based message routing, context management, and logging.

Example usage:
    from nergal.dialog import DialogManager
    from nergal.llm import create_llm_provider

    # Create LLM provider
    llm = create_llm_provider("zai", api_key="...", model="...")

    # Create dialog manager
    manager = DialogManager(llm_provider=llm)

    # Process a message
    result = await manager.process_message(
        user_id=12345,
        message="Привет!",
        user_info={"first_name": "John"}
    )
    print(result.response)
"""

from nergal.dialog.agents import (
    AgentRegistry,
    AgentResult,
    AgentType,
    BaseAgent,
    DefaultAgent,
)
from nergal.dialog.context import ContextManager, DialogContext, DialogState, UserInfo
from nergal.dialog.manager import DialogManager, ProcessResult
from nergal.dialog.styles import StyleType, get_style_prompt

__all__ = [
    # Manager
    "DialogManager",
    "ProcessResult",
    # Agents
    "BaseAgent",
    "DefaultAgent",
    "AgentRegistry",
    "AgentResult",
    "AgentType",
    # Context
    "DialogContext",
    "DialogState",
    "UserInfo",
    "ContextManager",
    # Styles
    "StyleType",
    "get_style_prompt",
]
