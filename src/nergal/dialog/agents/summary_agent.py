"""Summary agent for condensing and structuring information.

This agent creates concise summaries of long texts, extracts
key points, and adapts detail level to user needs.
"""

import logging
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


class SummaryAgent(BaseAgent):
    """Agent for summarizing and condensing information.
    
    This agent creates TL;DR summaries, extracts key points,
    and structures long content into digestible formats.
    
    Use cases:
    - TL;DR for long texts
    - Extract key points from documents
    - Structure information by sections
    - Adjust detail level
    """
    
    # Summary-related keywords
    SUMMARY_KEYWORDS = [
        "кратко", "сократи", "резюме", "суть", "главное",
        "основное", "tldr", "tl;dr", "summary", "в двух словах",
        "выдели главное", "перечисли основные", "итог",
    ]
    
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

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.
        
        Higher confidence for summary requests or when there's
        accumulated context to summarize.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        message_lower = message.lower()
        
        # Check for summary keywords
        for keyword in self.SUMMARY_KEYWORDS:
            if keyword in message_lower:
                return 0.9
        
        # Check if there's accumulated context to summarize
        agent_results = context.get("agent_results", {})
        if len(agent_results) >= 2:
            # Multiple sources might need summarization
            return 0.6
        
        # Long content in context
        accumulated_context = context.get("accumulated_context", {})
        if accumulated_context:
            return 0.5
        
        return 0.2
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by summarizing available information.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with summary.
        """
        # Gather content to summarize
        content_to_summarize = self._gather_content(message, context, history)
        
        if not content_to_summarize:
            return AgentResult(
                response="Нет информации для резюмирования.",
                agent_type=self.agent_type,
                confidence=0.3,
                metadata={"summarized": False}
            )
        
        # Determine summary type
        summary_type = self._determine_summary_type(message)
        
        # Generate summary
        summary = await self._generate_summary(
            content_to_summarize, summary_type, message
        )
        
        return AgentResult(
            response=summary,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={
                "summarized": True,
                "summary_type": summary_type,
                "content_length": len(content_to_summarize),
            }
        )
    
    def _gather_content(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> str:
        """Gather content to summarize from various sources.
        
        Args:
            message: User message.
            context: Dialog context.
            history: Message history.
            
        Returns:
            Combined content to summarize.
        """
        content_parts = []
        
        # Get content from previous agent results
        agent_results = context.get("agent_results", {})
        for agent_type, result in agent_results.items():
            if isinstance(result, dict):
                response = result.get("response", "")
            else:
                response = getattr(result, "response", "")
            
            if response:
                content_parts.append(f"[{agent_type}]\n{response}")
        
        # Get accumulated context
        accumulated = context.get("accumulated_context", {})
        if accumulated:
            for key, value in accumulated.items():
                if isinstance(value, str):
                    content_parts.append(f"[{key}]\n{value}")
        
        # Include recent history if relevant
        if history:
            recent = history[-3:]  # Last 3 messages
            for msg in recent:
                if msg.role == MessageRole.ASSISTANT:
                    content_parts.append(f"[history]\n{msg.content[:500]}")
        
        return "\n\n---\n\n".join(content_parts)
    
    def _determine_summary_type(self, message: str) -> str:
        """Determine the type of summary needed.
        
        Args:
            message: User message.
            
        Returns:
            Summary type identifier.
        """
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["tldr", "tl;dr", "в двух словах"]):
            return "tldr"
        elif any(kw in message_lower for kw in ["пункты", "список", "перечисли"]):
            return "bullet_points"
        elif any(kw in message_lower for kw in ["подробно", "детально"]):
            return "detailed"
        elif any(kw in message_lower for kw in ["вывод", "итог", "заключение"]):
            return "conclusion"
        else:
            return "standard"
    
    async def _generate_summary(
        self,
        content: str,
        summary_type: str,
        original_message: str,
    ) -> str:
        """Generate summary of content.
        
        Args:
            content: Content to summarize.
            summary_type: Type of summary to generate.
            original_message: Original user message.
            
        Returns:
            Generated summary.
        """
        type_instructions = {
            "tldr": "Создай максимально краткий TL;DR в 1-2 предложения.",
            "bullet_points": f"Выдели до {self._default_max_points} ключевых пунктов в виде списка.",
            "detailed": "Создай подробное резюме с сохранением важных деталей.",
            "conclusion": "Сделай итоговое заключение на основе информации.",
            "standard": "Создай краткое резюме с ключевыми пунктами.",
        }
        
        instruction = type_instructions.get(summary_type, type_instructions["standard"])
        
        prompt = f"""{instruction}

Исходный запрос: {original_message}

Информация для резюмирования:
{content[:4000]}

Создай структурированное резюме."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=800)
        return response.content
    
    async def create_tldr(self, text: str) -> str:
        """Create a TL;DR for given text.
        
        Args:
            text: Text to summarize.
            
        Returns:
            TL;DR summary.
        """
        prompt = f"""Создай TL;DR для следующего текста в 1-2 предложения:

{text[:2000]}"""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=150)
        return response.content
    
    async def extract_key_points(
        self,
        text: str,
        max_points: int = 5,
    ) -> list[str]:
        """Extract key points from text.
        
        Args:
            text: Text to analyze.
            max_points: Maximum number of points.
            
        Returns:
            List of key points.
        """
        prompt = f"""Выдели до {max_points} ключевых пунктов из текста.

Формат ответа - JSON массив строк:
["пункт 1", "пункт 2", ...]

Текст:
{text[:2000]}"""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
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
        lines = response.content.strip().split("\n")
        points = [line.lstrip("•-* ").strip() for line in lines if line.strip()]
        return points[:max_points]
    
    async def adjust_detail_level(
        self,
        text: str,
        target_length: str = "medium",
    ) -> str:
        """Adjust the detail level of text.
        
        Args:
            text: Original text.
            target_length: Target length (short, medium, long).
            
        Returns:
            Adjusted text.
        """
        length_instructions = {
            "short": "Сократи до 2-3 предложений, оставив только суть.",
            "medium": "Создай средний по объёму текст с ключевыми деталями.",
            "long": "Расширь текст, добавив пояснения и примеры.",
        }
        
        instruction = length_instructions.get(target_length, length_instructions["medium"])
        
        prompt = f"""{instruction}

Исходный текст:
{text[:2000]}"""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1000)
        return response.content
