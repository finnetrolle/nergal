"""Dialog manager for handling user conversations.

This module provides the main DialogManager class that coordinates
between agents, manages context, and handles logging.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from nergal.dialog.agents import AgentRegistry, AgentResult, AgentType, BaseAgent, DefaultAgent
from nergal.dialog.context import ContextManager, DialogContext, UserInfo
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """Result of processing a user message."""

    response: str
    agent_type: AgentType
    confidence: float
    session_id: str
    processing_time_ms: float
    metadata: dict[str, Any]


class DialogManager:
    """Main class for managing dialogs with users.

    This class coordinates between agents, manages conversation context,
    and provides logging for all dialog operations.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        max_history: int = 20,
        max_contexts: int = 1000,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        """Initialize the dialog manager.

        Args:
            llm_provider: LLM provider for generating responses.
            max_history: Maximum messages to keep in conversation history.
            max_contexts: Maximum number of user contexts to maintain.
            style_type: Response style to use for agents.
        """
        self.llm_provider = llm_provider
        self.agent_registry = AgentRegistry()
        self.context_manager = ContextManager(max_contexts=max_contexts)
        self._style_type = style_type

        # Register default agent
        self._register_default_agents()

        logger.info(
            f"DialogManager initialized with provider: {llm_provider.provider_name}, style: {style_type.value}"
        )

    def _register_default_agents(self) -> None:
        """Register the default set of agents."""
        default_agent = DefaultAgent(self.llm_provider, style_type=self._style_type)
        self.agent_registry.register(default_agent)
        logger.debug(f"Registered agent: {default_agent.agent_type}")

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a custom agent.

        Args:
            agent: Agent instance to register.
        """
        self.agent_registry.register(agent)
        logger.info(f"Registered custom agent: {agent.agent_type}")

    def get_or_create_context(
        self,
        user_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        language_code: str | None = None,
    ) -> DialogContext:
        """Get or create a dialog context for a user.

        Args:
            user_id: Telegram user ID.
            first_name: User's first name.
            last_name: User's last name.
            username: User's username.
            language_code: User's language code.

        Returns:
            DialogContext for the user.
        """
        return self.context_manager.get_or_create(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
        )

    async def process_message(
        self,
        user_id: int,
        message: str,
        user_info: dict[str, Any] | None = None,
    ) -> ProcessResult:
        """Process a user message and generate a response.

        This is the main entry point for handling user messages. It:
        1. Gets or creates a dialog context
        2. Determines the appropriate agent
        3. Processes the message
        4. Updates the context
        5. Logs the interaction

        Args:
            user_id: Telegram user ID.
            message: User's message text.
            user_info: Optional dict with user information
                      (first_name, last_name, username, language_code).

        Returns:
            ProcessResult containing the response and metadata.
        """
        start_time = datetime.utcnow()

        # Extract user info
        info = user_info or {}
        context = self.get_or_create_context(
            user_id=user_id,
            first_name=info.get("first_name"),
            last_name=info.get("last_name"),
            username=info.get("username"),
            language_code=info.get("language_code"),
        )

        # Log incoming message
        logger.info(
            f"Processing message from {context.user_info.display_name} "
            f"(ID: {user_id}): {message[:100]}..."
        )

        try:
            # Get context data for agent selection
            agent_context = context.get_context_for_agent()

            # Determine the best agent
            agent = await self.agent_registry.determine_agent(message, agent_context)
            logger.debug(f"Selected agent: {agent.agent_type}")

            # Update context with current agent
            context.set_current_agent(agent.agent_type.value)

            # Add user message to history
            context.add_user_message(message)

            # Get history for LLM
            history = context.get_history_for_llm()

            # Process with agent
            result = await agent.process(message, agent_context, history)

            # Add assistant response to history
            context.add_assistant_message(result.response)

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Log successful processing
            logger.info(
                f"Processed message for {context.user_info.display_name} "
                f"with agent {result.agent_type.value} "
                f"(confidence: {result.confidence:.2f}, "
                f"time: {processing_time:.0f}ms)"
            )

            return ProcessResult(
                response=result.response,
                agent_type=result.agent_type,
                confidence=result.confidence,
                session_id=context.session_id,
                processing_time_ms=processing_time,
                metadata=result.metadata,
            )

        except Exception as e:
            # Log error
            logger.error(
                f"Error processing message for {context.user_info.display_name}: {e}",
                exc_info=True,
            )

            # Return error response
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ProcessResult(
                response="Извините, произошла ошибка при обработке вашего сообщения. Попробуйте позже.",
                agent_type=AgentType.DEFAULT,
                confidence=0.0,
                session_id=context.session_id,
                processing_time_ms=processing_time,
                metadata={"error": str(e)},
            )

    async def process_with_context(
        self,
        context: DialogContext,
        message: str,
    ) -> ProcessResult:
        """Process a message with an existing context.

        Args:
            context: Existing dialog context.
            message: User's message text.

        Returns:
            ProcessResult containing the response and metadata.
        """
        user_info = {
            "first_name": context.user_info.first_name,
            "last_name": context.user_info.last_name,
            "username": context.user_info.username,
            "language_code": context.user_info.language_code,
        }
        return await self.process_message(
            user_id=context.user_info.user_id,
            message=message,
            user_info=user_info,
        )

    def clear_user_context(self, user_id: int) -> bool:
        """Clear the dialog context for a user.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if context was cleared, False if not found.
        """
        result = self.context_manager.remove(user_id)
        if result:
            logger.info(f"Cleared context for user {user_id}")
        return result

    def get_context_stats(self) -> dict[str, Any]:
        """Get statistics about current contexts.

        Returns:
            Dictionary with context statistics.
        """
        return {
            "active_contexts": self.context_manager.context_count,
            "registered_agents": len(self.agent_registry.get_all()),
            "llm_provider": self.llm_provider.provider_name,
        }
