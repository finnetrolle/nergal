"""Default agent for handling general requests.

This module provides the DefaultAgent class which handles general
conversations and serves as a fallback for unhandled messages.
"""

from typing import Any

from nergal.dialog.agents import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType, get_style_prompt
from nergal.llm import LLMMessage, MessageRole


class DefaultAgent(BaseAgent):
    """Default agent for handling general requests.

    This agent handles general conversations, greetings, and serves
    as a fallback when no other agent is suitable.
    """

    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.DEFAULT

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent based on the configured style."""
        return get_style_prompt(self._style_type)

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Default agent can handle any message with low confidence.

        Args:
            message: User message to analyze.
            context: Current dialog context.

        Returns:
            Always returns 0.1 as this is a fallback agent.
        """
        return 0.1

    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message using default behavior.

        If search results are available in the context (from a previous web_search step),
        they will be used to provide a more informed response.

        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history for context.

        Returns:
            AgentResult containing the response and metadata.
        """
        # Check if we have search results from a previous agent
        search_results = context.get("search_results")
        original_message = context.get("previous_step_metadata", {}).get("original_message", message)

        if search_results:
            # Use search results to generate a better response
            response = await self._generate_response_with_search_results(
                original_message=original_message,
                search_results=search_results,
                search_queries=context.get("search_queries", []),
                history=history,
            )
        else:
            response = await self.generate_response(message, history)

        return AgentResult(
            response=response.content,
            agent_type=self.agent_type,
            confidence=0.1,
            metadata={"model": response.model, "usage": response.usage},
        )

    async def _generate_response_with_search_results(
        self,
        original_message: str,
        search_results: str,
        search_queries: list[str],
        history: list[LLMMessage],
    ) -> Any:
        """Generate response using search results from previous agent.

        Args:
            original_message: The original user message.
            search_results: Formatted search results from web search agent.
            search_queries: List of search queries that were used.
            history: Conversation history.

        Returns:
            LLMResponse with the generated answer.
        """
        queries_str = ", ".join(search_queries) if search_queries else "web search"
        search_context = (
            f"Ниже приведены результаты поиска по запросам: {queries_str}\n\n"
            f"{search_results}\n\n"
            "Используй эти результаты поиска, чтобы ответить на вопрос пользователя. "
            "Будь полезным и указывай источники информации где уместно. "
            "Отвечай на том же языке, что и вопрос пользователя."
        )

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.SYSTEM, content=search_context),
            *history,
            LLMMessage(role=MessageRole.USER, content=original_message),
        ]

        return await self.llm_provider.generate(messages)
