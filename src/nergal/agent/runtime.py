"""Agent runtime for orchestrating all components.

This module provides the main AgentRuntime class that integrates
the tool system, memory, skills, security, and RAG.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nergal.agent.loop import run_tool_call_loop
from nergal.dispatcher.base import get_dispatcher
from nergal.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from nergal.memory.base import Memory
from nergal.security.policy import SecurityPolicy
from nergal.tools.base import Tool

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ConversationHistoryManager:
    """Manages conversation history for multiple users.

    This class maintains per-user conversation histories with automatic
    trimming to prevent memory bloat while maintaining context.

    Args:
        max_history: Maximum number of messages to keep per user.

    Example:
        >>> manager = ConversationHistoryManager(max_history=20)
        >>> manager.add_message(123, MessageRole.USER, "Hello!")
        >>> history = manager.get_history(123)
    """

    def __init__(self, max_history: int = 20) -> None:
        """Initialize conversation history manager.

        Args:
            max_history: Maximum number of messages to keep per user.
        """
        self.max_history = max_history
        self._histories: dict[int, list[LLMMessage]] = {}

    def get_history(self, user_id: int) -> list[LLMMessage]:
        """Get conversation history for a user.

        Args:
            user_id: User identifier.

        Returns:
            Copy of the user's message history.
        """
        return self._histories.get(user_id, []).copy()

    def add_message(self, user_id: int, role: MessageRole, content: str) -> None:
        """Add a message to a user's conversation history.

        Args:
            user_id: User identifier.
            role: Message role (user, assistant, system).
            content: Message content.
        """
        if user_id not in self._histories:
            self._histories[user_id] = []

        message = LLMMessage(role=role, content=content)
        self._histories[user_id].append(message)

        # Trim history if needed
        if len(self._histories[user_id]) > self.max_history:
            self._histories[user_id] = self._histories[user_id][-self.max_history :]

    def add_user_message(self, user_id: int, content: str) -> None:
        """Add a user message to history.

        Args:
            user_id: User identifier.
            content: Message content.
        """
        self.add_message(user_id, MessageRole.USER, content)

    def add_assistant_message(self, user_id: int, content: str) -> None:
        """Add an assistant message to history.

        Args:
            user_id: User identifier.
            content: Message content.
        """
        self.add_message(user_id, MessageRole.ASSISTANT, content)

    def clear_user_history(self, user_id: int) -> bool:
        """Clear conversation history for a user.

        Args:
            user_id: User identifier.

        Returns:
            True if history was cleared, False if user had no history.
        """
        if user_id in self._histories:
            del self._histories[user_id]
            logger.info(f"Cleared conversation history for user {user_id}")
            return True
        return False

    def get_active_users(self) -> list[int]:
        """Get list of users with active conversation history.

        Returns:
            List of user IDs with active conversations.
        """
        return list(self._histories.keys())

    def get_stats(self) -> dict[str, int | float]:
        """Get statistics about conversation histories.

        Returns:
            Dictionary with statistics.
        """
        total_messages = sum(len(h) for h in self._histories.values())
        return {
            "active_users": len(self._histories),
            "total_messages": total_messages,
            "avg_messages_per_user": total_messages / len(self._histories)
            if self._histories
            else 0,
        }


class AgentRuntime:
    """Main agent runtime that orchestrates all components.

    The AgentRuntime integrates:
    - LLM provider for generation
    - Tool system for capabilities
    - Memory system for context
    - Skills for domain-specific prompts
    - Security policy for enforcement
    - Conversation history management

    Args:
        llm_provider: LLM provider.
        tools: List of available tools.
        memory: Memory backend.
        security_policy: Security policy.
        max_history: Maximum history length.

    Example:
        >>> from nergal.agent.runtime import AgentRuntime
        >>>
        >>> runtime = AgentRuntime(
        ...     llm_provider=provider,
        ...     tools=[file_read, memory_store],
        ...     memory=memory,
        ...     security_policy=security_policy,
        ... )
        >>> response = await runtime.process_message("user_id", "Hello!")
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        tools: list[Tool],
        memory: Memory,
        security_policy: SecurityPolicy,
        max_history: int = 20,
    ) -> None:
        """Initialize agent runtime.

        Args:
            llm_provider: LLM provider.
            tools: List of available tools.
            memory: Memory backend.
            security_policy: Security policy.
            max_history: Maximum history length.
        """
        self.llm_provider = llm_provider
        self.tools = tools
        self.memory = memory
        self.security_policy = security_policy
        self.max_history = max_history

        # Conversation history management
        self.history_manager = ConversationHistoryManager(max_history=max_history)

        # Get appropriate dispatcher
        self.dispatcher = get_dispatcher(llm_provider)

    async def process_message(
        self,
        user_id: int,
        message: str,
        conversation_history: list[LLMMessage] | None = None,
    ) -> str:
        """Process message with full agent capabilities.

        Automatically manages conversation history by storing user and
        assistant messages. If conversation_history is provided, it is
        used instead of the internal history manager.

        Args:
            user_id: User identifier.
            message: The message to process.
            conversation_history: Optional conversation history (overrides internal history).

        Returns:
            The agent's response.

        Example:
            >>> response = await runtime.process_message(123, "Hello!")
            >>> print(response)
        """
        logger.debug(f"Processing message from user {user_id}: {message[:50]}...")

        # Get conversation history
        history = conversation_history or self.history_manager.get_history(user_id)

        # 1. Get relevant memory for context
        try:
            memory_entries = await self.memory.recall(query=message, limit=3)
        except Exception as e:
            logger.warning(f"Failed to retrieve memory: {e}")
            memory_entries = []

        # 2. Build system prompt with memory and skills
        system_prompt = await self._build_system_prompt(memory_entries)

        # 3. Prepare message history
        # Add system prompt if provided
        if system_prompt:
            history.insert(0, LLMMessage(role=MessageRole.SYSTEM, content=system_prompt))

        # Add user message
        history.append(LLMMessage(role=MessageRole.USER, content=message))

        # 4. Run tool call loop
        try:
            response = await run_tool_call_loop(
                provider=self.llm_provider,
                tools=self.tools,
                dispatcher=self.dispatcher,
                max_iterations=10,
                initial_messages=history,
                system_prompt=None if system_prompt else None,
            )
        except Exception as e:
            logger.error(f"Tool call loop failed: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

        # 5. Store messages in history (only if using internal history manager)
        if conversation_history is None:
            self.history_manager.add_user_message(user_id, message)
            self.history_manager.add_assistant_message(user_id, response)

        logger.info(f"Agent response for user {user_id}: {response[:100]}...")
        return response

    async def _build_system_prompt(self, memory_entries: list) -> str:
        """Build system prompt with memory context.

        Args:
            memory_entries: Relevant memory entries.

        Returns:
            System prompt string.
        """
        lines = []

        # Add memory context
        if memory_entries:
            lines.append("---")
            lines.append("## Context from Memory")
            for entry in memory_entries:
                lines.append(f"- [{entry.category.value}] {entry.content}")

        # Add instructions
        lines.append("")
        lines.append("## Instructions")
        lines.append("You are an AI assistant with access to various tools.")
        lines.append("Use the tools when they can help fulfill the user's request.")
        lines.append("Be helpful, accurate, and provide clear explanations.")

        return "\n".join(lines)

    async def get_available_tools_info(self) -> str:
        """Get information about available tools.

        Returns:
            Formatted string listing available tools.
        """
        if not self.tools:
            return "No tools available."

        lines = ["## Available Tools", ""]
        for tool in self.tools:
            allowed, reason = self.security_policy.is_tool_allowed(tool.name)
            status = "✓" if allowed else "✗"
            lines.append(f"- **{tool.name}**: {status}")
            if reason:
                lines.append(f"  Reason: {reason}")

        return "\n".join(lines)

    def clear_user_history(self, user_id: int) -> bool:
        """Clear conversation history for a user.

        Args:
            user_id: User identifier.

        Returns:
            True if history was cleared, False if user had no history.
        """
        return self.history_manager.clear_user_history(user_id)

    def get_user_history(self, user_id: int) -> list[LLMMessage]:
        """Get conversation history for a user.

        Args:
            user_id: User identifier.

        Returns:
            Copy of the user's message history.
        """
        return self.history_manager.get_history(user_id)

    def get_active_users(self) -> list[int]:
        """Get list of users with active conversation history.

        Returns:
            List of user IDs with active conversations.
        """
        return self.history_manager.get_active_users()

    def get_conversation_stats(self) -> dict[str, int | float]:
        """Get statistics about conversations.

        Returns:
            Dictionary with conversation statistics.
        """
        stats = self.history_manager.get_stats()
        # Ensure consistent return type
        return {
            "active_users": stats["active_users"],
            "total_messages": stats["total_messages"],
            "avg_messages_per_user": stats["avg_messages_per_user"],
        }
