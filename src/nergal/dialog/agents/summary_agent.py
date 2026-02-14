"""Summary agent for condensing and structuring information.

This agent creates concise summaries of long texts, extracts
key points, and adapts detail level to user needs.
"""

import logging
from typing import Any

from nergal.dialog.agents.base_specialized import ContextAwareAgent
from nergal.dialog.constants import SUMMARY_KEYWORDS
from nergal.dialog.base import AgentResult, AgentType
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


class SummaryAgent(ContextAwareAgent):
    """Agent for summarizing and condensing information.
    
    This agent creates TL;DR summaries, extracts key points,
    and structures long content into digestible formats.
    
    Use cases:
    - TL;DR for long texts
    - Extract key points from documents
    - Structure information by sections
    - Adjust detail level
    """
    
    # Configure base class behavior
    _keywords = SUMMARY_KEYWORDS
    _required_context_keys = ["search_results", "previous_step_output"]
    _base_confidence = 0.3
    _keyword_boost = 0.2
    _context_boost = 0.4
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
        default_max_points: int = 5,
    ) -> None:
        """Initialize the summary agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use.
            default_max_points: Default max key points to extract.
        """
        super().__init__(llm_provider, style_type)
        self._default_max_points = default_max_points
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.SUMMARY
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return """Ты — агент резюмирования. Твоя задача — сокращать и
структурировать информацию, выделяя главное.

Принципы:
1. Сохраняй ключевой смысл
2. Убирай лишние детали
3. Структурируй информацию
4. Используй списки для перечислений
5. Выделяй важное

Форматы ответа:

**TL;DR** (для длинных текстов):
> [1-2 предложения с сутью]

**Ключевые пункты:**
• Пункт 1
• Пункт 2
• ...

**Детали** (опционально):
[Важные детали если нужны]

**Вывод:**
[Итоговое заключение]"""

    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by summarizing content.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with summary.
        """
        # Get content to summarize from context
        content_to_summarize = self._get_content_to_summarize(context)
        
        if not content_to_summarize:
            return AgentResult(
                response="Нет содержимого для резюмирования. Сначала получите информацию через поиск или другой агент.",
                agent_type=self.agent_type,
                confidence=0.3,
                metadata={"error": "no_content"},
            )
        
        # Generate summary
        summary = await self._generate_summary(message, content_to_summarize)
        
        return AgentResult(
            response=summary,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={
                "content_length": len(content_to_summarize),
                "max_points": self._default_max_points,
            },
        )
    
    def _get_content_to_summarize(self, context: dict[str, Any]) -> str:
        """Extract content to summarize from context.
        
        Args:
            context: Dialog context.
            
        Returns:
            Content string to summarize.
        """
        # Check for search results
        if "search_results" in context:
            return context["search_results"]
        
        # Check for previous step output
        if "previous_step_output" in context:
            return context["previous_step_output"]
        
        # Check in metadata
        if "previous_step_metadata" in context:
            metadata = context["previous_step_metadata"]
            if "search_results" in metadata:
                return metadata["search_results"]
        
        return ""
    
    async def _generate_summary(
        self,
        message: str,
        content: str,
    ) -> str:
        """Generate summary of content.
        
        Args:
            message: Original user message.
            content: Content to summarize.
            
        Returns:
            Summary text.
        """
        # Truncate very long content
        max_content_length = 4000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n...[обрезано]"
        
        prompt = f"""Создай краткое резюме следующего содержимого.

Запрос пользователя: {message}

Содержимое для резюмирования:
{content}

Создай структурированное резюме с ключевыми пунктами (максимум {self._default_max_points} пунктов)."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=800)
        return response.content
    
    async def extract_key_points(
        self,
        content: str,
        max_points: int | None = None,
    ) -> list[str]:
        """Extract key points from content.
        
        Args:
            content: Content to analyze.
            max_points: Maximum number of points to extract.
            
        Returns:
            List of key points.
        """
        max_points = max_points or self._default_max_points
        
        prompt = f"""Извлеки ключевые пункты из текста.

Текст:
{content[:2000]}

Верни список из максимум {max_points} ключевых пунктов в формате JSON:
["пункт1", "пункт2", ...]"""
        
        messages = [
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=500)
        
        # Try to parse JSON
        import json
        try:
            start = response.content.find("[")
            end = response.content.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(response.content[start:end])
        except json.JSONDecodeError:
            pass
        
        # Fallback: split by newlines
        return [
            line.strip().lstrip("•-1234567890. ")
            for line in response.content.split("\n")
            if line.strip()
        ][:max_points]
