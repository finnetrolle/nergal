"""Web search agent for handling search-related queries.

This module provides an agent that can search the web for information
and synthesize responses using the LLM.
"""

import logging
import re
from typing import Any

from nergal.dialog.agents import AgentResult, AgentType, BaseAgent
from nergal.dialog.constants import (
    FILLER_WORDS,
    SEARCH_KEYWORDS,
    SEARCH_PATTERNS,
    TIME_RELATED_WORDS,
)
from nergal.dialog.styles import StyleType, get_style_prompt
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole
from nergal.web_search import BaseSearchProvider, SearchError, SearchRequest

logger = logging.getLogger(__name__)


class WebSearchAgent(BaseAgent):
    """Agent for handling web search queries.

    This agent detects when a user wants to search the web,
    performs the search, and synthesizes a response using the LLM.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        search_provider: BaseSearchProvider,
        style_type: StyleType = StyleType.DEFAULT,
        max_search_results: int = 5,
        min_confidence: float = 0.6,
    ) -> None:
        """Initialize the web search agent.

        Args:
            llm_provider: LLM provider for generating responses.
            search_provider: Web search provider for searching.
            style_type: Response style to use.
            max_search_results: Maximum number of search results to use.
            min_confidence: Minimum confidence threshold for handling.
        """
        super().__init__(llm_provider, style_type)
        self.search_provider = search_provider
        self.max_search_results = max_search_results
        self.min_confidence = min_confidence

    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.TASK

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        base_prompt = get_style_prompt(self._style_type)
        return (
            f"{base_prompt}\n\n"
            "You have access to web search results to answer the user's question. "
            "Use the provided search results to give accurate, up-to-date information. "
            "Always cite your sources by mentioning where you found the information. "
            "If the search results don't contain relevant information, say so honestly. "
            "Synthesize information from multiple sources when possible."
        )

    def _extract_search_query(self, message: str) -> str:
        """Extract search query from user message.

        Args:
            message: User's message.

        Returns:
            Extracted search query.
        """
        message_lower = message.lower().strip()

        # Try to match patterns
        for pattern in SEARCH_PATTERNS:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Remove filler words from the message
        query = message_lower
        for word in FILLER_WORDS:
            query = re.sub(rf"\b{word}\b", "", query)

        return query.strip()

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.

        Args:
            message: User message to analyze.
            context: Current dialog context.

        Returns:
            Confidence score (0.0 to 1.0).
        """
        message_lower = message.lower().strip()

        # Check for explicit search keywords
        for keyword in SEARCH_KEYWORDS:
            if keyword in message_lower:
                logger.debug(f"Search keyword found: {keyword}")
                return self.min_confidence + 0.2

        # Check for question patterns that suggest needing current info
        question_patterns = [
            r"\?$",  # Ends with question mark
            r"^(who|what|when|where|why|how|кто|что|когда|где|почему|как)",
            r"(?:сейчас|сегодня|недавно|последние|latest|current|recent|today)",
        ]

        for pattern in question_patterns:
            if re.search(pattern, message_lower):
                # Questions about current/recent events get higher confidence
                if any(word in message_lower for word in TIME_RELATED_WORDS):
                    return self.min_confidence + 0.3
                return self.min_confidence

        return 0.0

    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by searching the web.

        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history for context.

        Returns:
            AgentResult containing the response.
        """
        try:
            search_query = self._extract_search_query(message)
            logger.info(f"Performing web search for: {search_query}")

            request = SearchRequest(query=search_query, count=self.max_search_results)
            results = await self.search_provider.search(request)

            if results.is_empty():
                response = await self._generate_no_results_response(
                    message, search_query, history
                )
                return AgentResult(
                    response=response,
                    agent_type=self.agent_type,
                    confidence=0.5,
                    metadata={"search_query": search_query, "results_count": 0},
                )

            formatted_results = results.to_text(max_results=self.max_search_results)
            response = await self._generate_response_with_results(
                message, search_query, formatted_results, history
            )

            return AgentResult(
                response=response,
                agent_type=self.agent_type,
                confidence=0.9,
                metadata={
                    "search_query": search_query,
                    "results_count": len(results.results),
                    "sources": [r.link for r in results.results[:3]],
                },
            )

        except SearchError as e:
            logger.error(
                f"Web search failed for query '{message}': {type(e).__name__}: {e}",
                exc_info=True,
            )
            response = await self.generate_response(message, history)
            return AgentResult(
                response=f"{response.content}\n\n_(Примечание: Не удалось выполнить поиск в сети)_",
                agent_type=self.agent_type,
                confidence=0.3,
                metadata={"error": str(e), "error_type": type(e).__name__},
            )

    async def _generate_response_with_results(
        self,
        message: str,
        search_query: str,
        formatted_results: str,
        history: list[LLMMessage],
    ) -> str:
        """Generate response using LLM with search results.

        Args:
            message: Original user message.
            search_query: Search query used.
            formatted_results: Formatted search results.
            history: Conversation history.

        Returns:
            Generated response.
        """
        search_context = (
            f"Search query: {search_query}\n\n"
            f"Search results:\n{formatted_results}\n\n"
            "Based on these search results, answer the user's question. "
            "Be helpful and cite sources when appropriate."
        )

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.SYSTEM, content=search_context),
            *history,
            LLMMessage(role=MessageRole.USER, content=message),
        ]

        response = await self.llm_provider.generate(messages)
        return response.content

    async def _generate_no_results_response(
        self,
        message: str,
        search_query: str,
        history: list[LLMMessage],
    ) -> str:
        """Generate response when no search results found.

        Args:
            message: Original user message.
            search_query: Search query used.
            history: Conversation history.

        Returns:
            Generated response.
        """
        no_results_context = (
            f"You searched for '{search_query}' but found no relevant results. "
            "Apologize to the user and suggest they try a different search query "
            "or provide what information you can from your training data."
        )

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.SYSTEM, content=no_results_context),
            *history,
            LLMMessage(role=MessageRole.USER, content=message),
        ]

        response = await self.llm_provider.generate(messages)
        return response.content
