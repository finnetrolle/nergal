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


class AgentRuntime:
    """Main agent runtime that orchestrates all components.

    The AgentRuntime integrates:
    - LLM provider for generation
    - Tool system for capabilities
    - Memory system for context
    - Skills for domain-specific prompts
    - Security policy for enforcement

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

        # Get appropriate dispatcher
        self.dispatcher = get_dispatcher(llm_provider)

    async def process_message(
        self,
        user_id: int,
        message: str,
        conversation_history: list[LLMMessage] | None = None,
    ) -> str:
        """Process message with full agent capabilities.

        Args:
            user_id: User identifier.
            message: The message to process.
            conversation_history: Optional conversation history.

        Returns:
            The agent's response.

        Example:
            >>> response = await runtime.process_message(123, "Hello!")
            >>> print(response)
        """
        logger.debug(f"Processing message from user {user_id}: {message[:50]}...")

        # 1. Get relevant memory for context
        try:
            memory_entries = await self.memory.recall(query=message, limit=3)
        except Exception as e:
            logger.warning(f"Failed to retrieve memory: {e}")
            memory_entries = []

        # 2. Build system prompt with memory and skills
        system_prompt = await self._build_system_prompt(memory_entries)

        # 3. Prepare message history
        history = conversation_history or []

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
