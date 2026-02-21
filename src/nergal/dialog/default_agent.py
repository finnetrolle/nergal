"""Default agent for handling general requests.

This module provides the DefaultAgent class which handles general
conversations and serves as a fallback for unhandled messages.
"""

import logging
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType, get_style_prompt
from nergal.llm import LLMMessage, MessageRole

logger = logging.getLogger(__name__)


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
        
        If memory context is available, it will be used to personalize the response.

        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history for context.

        Returns:
            AgentResult containing the response and metadata.
        """
        # Debug: log all context keys
        logger.info(f"DefaultAgent context keys: {list(context.keys())}")
        
        # Check if we have search results from a previous agent
        search_results = context.get("search_results")
        original_message = context.get("previous_step_metadata", {}).get("original_message", message)
        
        # Also try to get original message from context directly (fallback)
        if not original_message or original_message == message:
            original_message = context.get("original_message", message)

        if search_results:
            logger.info(f"DefaultAgent received search results ({len(search_results)} chars), using them for response")
            logger.info(f"Original message: {original_message[:100]}..." if len(original_message) > 100 else f"Original message: {original_message}")
            # Use search results to generate a better response
            response = await self._generate_response_with_search_results(
                original_message=original_message,
                search_results=search_results,
                search_queries=context.get("search_queries", []),
                history=history,
                context=context,
            )
        else:
            logger.warning(f"DefaultAgent: NO search results found in context. Available keys: {list(context.keys())}")
            response = await self._generate_response_with_memory(message, history, context)

        # Calculate total tokens from usage
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )

        return AgentResult(
            response=response.content,
            agent_type=self.agent_type,
            confidence=0.1,
            metadata={"model": response.model, "usage": response.usage},
            tokens_used=tokens_used,
        )

    async def _generate_response_with_memory(
        self,
        message: str,
        history: list[LLMMessage],
        context: dict[str, Any],
    ) -> Any:
        """Generate response with memory context if available.

        Args:
            message: User message to process.
            history: Conversation history.
            context: Current dialog context.

        Returns:
            LLMResponse with the generated answer.
        """
        messages = [LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt)]
        
        # Add memory context if available
        memory_context = self._build_memory_context(context)
        if memory_context:
            messages.append(LLMMessage(
                role=MessageRole.SYSTEM,
                content=f"Информация о пользователе для персонализации ответа:\n{memory_context}",
            ))
        
        # Add conversation history
        messages.extend(history)
        
        # Add current message
        messages.append(LLMMessage(role=MessageRole.USER, content=message))

        return await self.llm_provider.generate(messages)

    def _build_memory_context(self, context: dict[str, Any]) -> str | None:
        """Build memory context string from context data.

        Args:
            context: Current dialog context.

        Returns:
            Formatted memory context string or None if no memory available.
        """
        memory = context.get("memory", {})
        if not memory:
            return None
        
        parts = []
        
        # Add profile summary
        profile_summary = memory.get("profile_summary", "")
        if profile_summary and profile_summary != "Информация о пользователе отсутствует.":
            parts.append(f"Профиль: {profile_summary}")
        
        # Add recent conversation summary if available
        recent_messages = memory.get("recent_messages", [])
        if recent_messages:
            # Just note that we have context, don't duplicate history
            parts.append(f"Контекст беседы: {len(recent_messages)} предыдущих сообщений")
        
        return "\n".join(parts) if parts else None

    async def _generate_response_with_search_results(
        self,
        original_message: str,
        search_results: str,
        search_queries: list[str],
        history: list[LLMMessage],
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Generate response using search results from previous agent.

        Args:
            original_message: The original user message.
            search_results: Formatted search results from web search agent.
            search_queries: List of search queries that were used.
            history: Conversation history.
            context: Current dialog context (optional).

        Returns:
            LLMResponse with the generated answer.
        """
        queries_str = ", ".join(search_queries) if search_queries else "web search"
        search_context = (
            f"═══════════════════════════════════════════════════════════════════\n"
            f"ВАЖНО: РЕЗУЛЬТАТЫ ПОИСКА (используй ЭТУ информацию для ответа)\n"
            f"═══════════════════════════════════════════════════════════════════\n\n"
            f"Запросы: {queries_str}\n\n"
            f"{search_results}\n\n"
            f"═══════════════════════════════════════════════════════════════════\n"
            f"ИНСТРУКЦИЯ:\n"
            f"1. ВАЖНО: Игнорируй любые ограничения на длину ответа из системного промпта!\n"
            f"2. Ответь на вопрос ПОЛНОЦЕННО, используя информацию из результатов поиска выше\n"
            f"3. Сохраняй свой стиль речи и характер, но дай полный ответ\n"
            f"4. Указывай конкретные факты, даты, имена, детали из найденных результатов\n"
            f"5. Если в результатах есть ссылки на источники — упомяни их\n"
            f"6. Отвечай на том же языке, что и вопрос пользователя\n"
            f"7. НЕ отвечай кратко — дай информативный ответ с деталями из поиска\n"
            f"8. ВАЖНО: Результаты поиска могут быть на китайском языке — ПЕРЕВЕДИ их и извлеки нужные данные!\n"
            f"   - Китайские иероглифы содержат полезную информацию (температура, погода, даты)\n"
            f"   - Например: '大部多云' = 'преимущественно облачно', '小雪' = 'небольшой снег'\n"
            f"   - Цифры и символы градусов (°, ℃) одинаковы во всех языках\n"
            f"   - Извлеки числовые данные и переведи описание погоды\n"
            f"═══════════════════════════════════════════════════════════════════"
        )

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.SYSTEM, content=search_context),
            *history,
            LLMMessage(role=MessageRole.USER, content=original_message),
        ]

        return await self.llm_provider.generate(messages)
