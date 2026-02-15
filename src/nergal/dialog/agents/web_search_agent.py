"""Web search agent for handling search-related queries.

This module provides an agent that can search the web for information
and synthesize responses using the LLM.
"""

import json
import logging
import re
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.constants import (
    FILLER_WORDS,
    SEARCH_KEYWORDS,
    SEARCH_PATTERNS,
    TIME_RELATED_WORDS,
)
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole
from nergal.web_search import BaseSearchProvider, SearchError, SearchRequest

logger = logging.getLogger(__name__)

SEARCH_QUERY_GENERATION_PROMPT = """You are a search query generator. Your task is to analyze the user's question and generate optimal search queries for finding relevant information.

Rules:
1. Generate ONLY ONE search query unless the question asks for clearly DIFFERENT information
2. Each query must search for UNIQUE, NON-OVERLAPPING information - never generate synonyms or rephrasings of the same query
3. Queries should be concise and focused
4. Queries should be in the same language as the user's question
5. Return ONLY a JSON array of strings, nothing else

CRITICAL: Do NOT generate multiple queries for the same topic. One well-formed query is sufficient.

Examples:
User: "What's the weather like in Moscow and St. Petersburg?"
Output: ["weather Moscow today", "weather St. Petersburg today"]
( TWO queries because TWO different cities - this is correct)

User: "Какая погода будет в Питере завтра утром?"
Output: ["погода Санкт-Петербург завтра утром"]
(ONE query is enough - do NOT add "прогноз погоды Питер завтра" or similar)

User: "Сравни iPhone 15 и Samsung Galaxy S24"
Output: ["iPhone 15 vs Samsung Galaxy S24 сравнение"]
(ONE query is enough - search engines handle comparisons)

User: "Who won the Champions League in 2024?"
Output: ["Champions League 2024 winner"]
(ONE query is enough)

User: "Какие новости в России и в мире сегодня?"
Output: ["новости Россия сегодня", "мировые новости сегодня"]
(TWO queries because TWO different topics - domestic vs world news)

Now generate search queries for this user question:
{question}"""


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
        return AgentType.WEB_SEARCH

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent.

        Note: This agent is an intermediate step, so it uses a neutral prompt.
        The style is applied only at the final step by DefaultAgent.
        """
        return (
            "You are a search assistant. Your task is to analyze web search results "
            "and extract relevant information to answer the user's question. "
            "Be factual and objective. Focus on accuracy rather than style. "
            "Include source links when available. "
            "If the search results don't contain relevant information, state that clearly."
        )

    def _deduplicate_queries(self, queries: list[str]) -> list[str]:
        """Remove duplicate or very similar search queries.

        This method ensures that we don't search for essentially the same
        information multiple times.

        Args:
            queries: List of search queries.

        Returns:
            Deduplicated list of search queries.
        """
        if len(queries) <= 1:
            return queries

        unique_queries = []
        seen_normalized = set()

        for query in queries:
            # Normalize query for comparison: lowercase, remove extra spaces
            normalized = ' '.join(query.lower().split())

            # Check if this normalized query is similar to any we've seen
            is_duplicate = False
            for seen in seen_normalized:
                # Check for high overlap - if one query contains most of another
                seen_words = set(seen.split())
                query_words = set(normalized.split())

                # Calculate Jaccard similarity
                if seen_words and query_words:
                    intersection = len(seen_words & query_words)
                    union = len(seen_words | query_words)
                    similarity = intersection / union if union > 0 else 0

                    # If similarity > 0.7, consider it a duplicate
                    if similarity > 0.7:
                        is_duplicate = True
                        logger.debug(
                            f"Query '{query}' is similar to '{seen}' (similarity: {similarity:.2f}), skipping"
                        )
                        break

            if not is_duplicate:
                unique_queries.append(query)
                seen_normalized.add(normalized)

        if len(unique_queries) < len(queries):
            logger.info(
                f"Deduplicated queries: {len(queries)} -> {len(unique_queries)}"
            )

        return unique_queries if unique_queries else queries[:1]

    async def _generate_search_queries(self, message: str) -> list[str]:
        """Generate optimal search queries using LLM.

        This method uses the LLM to analyze the user's question and
        generate one or more targeted search queries.

        Args:
            message: User's message.

        Returns:
            List of search queries.
        """
        prompt = SEARCH_QUERY_GENERATION_PROMPT.format(question=message)

        messages = [
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]

        try:
            response = await self.llm_provider.generate(messages)
            content = response.content.strip() if response.content else ""

            if not content:
                logger.warning("LLM returned empty response for query generation")
                return [self._fallback_extract_query(message)]

            # Try to extract JSON from the response
            # Sometimes LLM adds extra text, so we try to find JSON array
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            queries = json.loads(content)

            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                # Deduplicate queries to avoid searching for the same thing twice
                queries = self._deduplicate_queries(queries)
                logger.info(f"Generated {len(queries)} search queries: {queries}")
                return queries

            logger.warning(f"Invalid query format from LLM: {content}")
            return [self._fallback_extract_query(message)]

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse LLM query response: {e}")
            return [self._fallback_extract_query(message)]
        except Exception as e:
            logger.error(f"Error generating search queries: {type(e).__name__}: {e}", exc_info=True)
            return [self._fallback_extract_query(message)]

    def _fallback_extract_query(self, message: str) -> str:
        """Fallback method to extract search query from user message.

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

        This method first uses the LLM to generate optimal search queries,
        then performs the searches and synthesizes a response.

        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history for context.

        Returns:
            AgentResult containing the response.
        """
        try:
            # Step 1: Generate search queries using LLM
            search_queries = await self._generate_search_queries(message)

            if not search_queries:
                search_queries = [self._fallback_extract_query(message)]

            logger.info(f"Performing web searches for: {search_queries}")

            # Step 2: Execute all searches and collect results
            all_results = await self._execute_multiple_searches(search_queries)

            if not all_results:
                response, tokens_used = await self._generate_no_results_response(
                    message, search_queries, history
                )
                return AgentResult(
                    response=response,
                    agent_type=self.agent_type,
                    confidence=0.5,
                    metadata={"search_queries": search_queries, "results_count": 0},
                    tokens_used=tokens_used,
                )

            # Step 3: Generate response with combined results
            formatted_results = self._format_multiple_results(all_results)
            response, tokens_used = await self._generate_response_with_results(
                message, search_queries, formatted_results, history
            )

            # Collect all unique sources
            all_sources = []
            seen_links = set()
            for query, results in all_results:
                for r in results.results[:3]:
                    if r.link not in seen_links:
                        all_sources.append(r.link)
                        seen_links.add(r.link)

            return AgentResult(
                response=response,
                agent_type=self.agent_type,
                confidence=0.9,
                metadata={
                    "search_queries": search_queries,
                    "results_count": sum(len(r.results) for _, r in all_results),
                    "sources": all_sources[:5],
                    # Store formatted results for subsequent agents
                    "search_results": formatted_results,
                    "original_message": message,
                },
                tokens_used=tokens_used,
            )

        except SearchError as e:
            logger.error(
                f"Web search failed for query '{message}': {type(e).__name__}: {e}",
                exc_info=True,
            )
            response = await self.generate_response(message, history)
            tokens_used = None
            if response.usage:
                tokens_used = response.usage.get("total_tokens") or (
                    response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
                )
            return AgentResult(
                response=f"{response.content}\n\n_(Примечание: Не удалось выполнить поиск в сети)_",
                agent_type=self.agent_type,
                confidence=0.3,
                metadata={"error": str(e), "error_type": type(e).__name__},
                tokens_used=tokens_used,
            )
        except Exception as e:
            # Catch any other errors (e.g., LLM provider errors during response generation)
            logger.error(
                f"Unexpected error in web search agent for query '{message}': {type(e).__name__}: {e}",
                exc_info=True,
            )
            # Check if it's a timeout error
            error_name = type(e).__name__
            if "Timeout" in error_name or "timeout" in str(e).lower():
                return AgentResult(
                    response="Превышено время ожидания ответа. Попробуйте упростить запрос или повторить позже.",
                    agent_type=self.agent_type,
                    confidence=0.1,
                    metadata={"error": str(e), "error_type": error_name},
                    tokens_used=None,
                )
            return AgentResult(
                response="Произошла ошибка при обработке вашего запроса. Попробуйте позже или переформулируйте вопрос.",
                agent_type=self.agent_type,
                confidence=0.1,
                metadata={"error": str(e), "error_type": error_name},
                tokens_used=None,
            )

    async def _execute_multiple_searches(
        self, queries: list[str]
    ) -> list[tuple[str, Any]]:
        """Execute multiple search queries and return results.

        Args:
            queries: List of search queries to execute.

        Returns:
            List of (query, results) tuples.
        """
        all_results = []

        for query in queries:
            try:
                request = SearchRequest(
                    query=query,
                    count=self.max_search_results,
                )
                results = await self.search_provider.search(request)

                if not results.is_empty():
                    all_results.append((query, results))
                    logger.debug(f"Found {len(results.results)} results for: {query}")
                else:
                    logger.debug(f"No results for query: {query}")

            except SearchError as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                continue

        return all_results

    def _format_multiple_results(
        self, all_results: list[tuple[str, Any]]
    ) -> str:
        """Format results from multiple searches.

        Args:
            all_results: List of (query, results) tuples.

        Returns:
            Formatted string with all search results.
        """
        formatted_parts = []

        for query, results in all_results:
            formatted_parts.append(f"=== Results for: {query} ===")
            formatted_parts.append(results.to_text(max_results=self.max_search_results))
            formatted_parts.append("")

        return "\n".join(formatted_parts)

    async def _generate_response_with_results(
        self,
        message: str,
        search_queries: list[str],
        formatted_results: str,
        history: list[LLMMessage],
    ) -> tuple[str, int | None]:
        """Generate response using LLM with search results.

        Args:
            message: Original user message.
            search_queries: List of search queries used.
            formatted_results: Formatted search results.
            history: Conversation history.

        Returns:
            Tuple of (generated response, tokens used or None).
        """
        queries_str = ", ".join(search_queries)
        search_context = (
            f"Search queries: {queries_str}\n\n"
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
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )
        return response.content, tokens_used

    async def _generate_no_results_response(
        self,
        message: str,
        search_queries: list[str],
        history: list[LLMMessage],
    ) -> tuple[str, int | None]:
        """Generate response when no search results found.

        Args:
            message: Original user message.
            search_queries: List of search queries used.
            history: Conversation history.

        Returns:
            Tuple of (generated response, tokens used or None).
        """
        queries_str = ", ".join(search_queries)
        no_results_context = (
            f"You searched for '{queries_str}' but found no relevant results. "
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
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )
        return response.content, tokens_used
