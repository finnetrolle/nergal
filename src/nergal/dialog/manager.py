"""Dialog manager for handling user conversations.

This module provides the main DialogManager class that manages
conversation context and generates responses using LLM.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from llm_lib import BaseLLMProvider, LLMMessage, MessageRole
from nergal.dialog.context import ContextManager, DialogContext
from nergal.dialog.styles import StyleType
from web_search_lib.providers import ZaiMcpHttpSearchProvider

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """Result of processing a user message."""

    response: str
    processing_time_ms: float
    metadata: dict[str, Any]


class DialogManager:
    """Main class for managing dialogs with users.

    This class manages conversation context and generates responses
    using the LLM provider.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        max_history: int = 20,
        max_contexts: int = 1000,
        style_type: StyleType = StyleType.DEFAULT,
        web_search_provider: ZaiMcpHttpSearchProvider | None = None,
    ) -> None:
        """Initialize the dialog manager.

        Args:
            llm_provider: LLM provider for generating responses.
            max_history: Maximum messages to keep in conversation history.
            max_contexts: Maximum number of user contexts to maintain.
            style_type: Response style to use.
            web_search_provider: Optional web search provider.
        """
        self.llm_provider = llm_provider
        self.context_manager = ContextManager(max_contexts=max_contexts)
        self._style_type = style_type
        self._web_search_provider = web_search_provider

        logger.info(
            f"DialogManager initialized with provider: {llm_provider.provider_name}, "
            f"style: {style_type.value}"
        )

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
        2. Optionally performs web search if available
        3. Generates a response using LLM
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
        start_time = datetime.now(UTC)

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
            # Add user message to history
            context.add_user_message(message)

            # Perform web search if available
            search_context = ""
            if self._web_search_provider:
                try:
                    search_results = await self._web_search_provider.search(message)
                    if search_results:
                        search_context = f"\n\nSearch results:\n{search_results}"
                        logger.debug(f"Found search results for query: {message[:50]}...")
                except Exception as e:
                    logger.warning(f"Web search failed: {e}")

            # Get history for LLM
            history = context.get_history_for_llm()

            # Build system prompt with style
            system_prompt = self._get_system_prompt()

            # Prepare messages for LLM
            messages = [LLMMessage(role=MessageRole.SYSTEM, content=system_prompt)]
            messages.extend(history)

            # Add search context to the last user message if available
            if search_context and messages and messages[-1].role == MessageRole.USER:
                messages[-1] = LLMMessage(
                    role=MessageRole.USER,
                    content=messages[-1].content + search_context
                )

            # Generate response
            response = await self.llm_provider.generate(messages)

            # Add assistant response to history
            context.add_assistant_message(response.content)

            # Calculate processing time
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Log successful processing
            logger.info(
                f"Processed message for {context.user_info.display_name} "
                f"(time: {processing_time:.0f}ms)"
            )

            return ProcessResult(
                response=response.content,
                processing_time_ms=processing_time,
                metadata={
                    "model": response.model,
                    "tokens_used": response.usage.get("total_tokens", 0) if response.usage else 0,
                },
            )

        except Exception as e:
            # Log error
            logger.error(
                f"Error processing message for {context.user_info.display_name}: {e}",
                exc_info=True,
            )

            # Return error response
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            return ProcessResult(
                response="Извините, произошла ошибка при обработке вашего сообщения. Попробуйте позже.",
                processing_time_ms=processing_time,
                metadata={"error": str(e)},
            )

    def _get_system_prompt(self) -> str:
        """Get system prompt based on style."""
        from nergal.dialog.styles import STYLE_PROMPTS, DEFAULT_STYLE_PROMPT
        return STYLE_PROMPTS.get(self._style_type, DEFAULT_STYLE_PROMPT)

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
            "llm_provider": self.llm_provider.provider_name,
        }
