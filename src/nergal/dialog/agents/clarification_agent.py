"""Clarification agent for disambiguating user queries.

This agent analyzes user messages for ambiguity and generates
clarifying questions when needed.
"""

import json
import logging
from typing import Any

from nergal.dialog.agents.base_specialized import BaseSpecializedAgent
from nergal.dialog.constants import CLARIFICATION_KEYWORDS
from nergal.dialog.base import AgentResult, AgentType
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


class ClarificationAgent(BaseSpecializedAgent):
    """Agent for clarifying ambiguous user queries.
    
    This agent determines if a user's question is ambiguous and
    generates appropriate clarifying questions to improve understanding.
    
    The agent can:
    - Detect ambiguity in queries
    - Generate clarifying questions
    - Interpret user responses to clarifications
    """
    
    # Configure base class behavior
    _keywords = CLARIFICATION_KEYWORDS
    _context_keys = []
    _base_confidence = 0.2
    _keyword_boost = 0.15
    _context_boost = 0.3
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
        max_clarifications: int = 2,
    ) -> None:
        """Initialize the clarification agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use.
            max_clarifications: Maximum clarifying questions per query.
        """
        super().__init__(llm_provider, style_type)
        self._max_clarifications = max_clarifications
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.CLARIFICATION
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return """Ты — агент уточнения запросов. Твоя задача — определить,
нужно ли уточнить запрос пользователя и сформулировать уточняющий вопрос.

Анализируй запрос на наличие неопределенности:
- Неясные термины или понятия
- Несколько возможных интерпретаций
- Отсутствие важного контекста
- Слишком общий вопрос

Если запрос ясен и однозначен — верни JSON с clarification_needed: false.
Если нужно уточнение — верни JSON с clarification_needed: true и вопросом.

Отвечай ТОЛЬКО в формате JSON:
{
    "clarification_needed": true/false,
    "reason": "причина почему нужно/не нужно уточнение",
    "question": "уточняющий вопрос на русском",
    "options": ["вариант1", "вариант2"] // опционально
}"""

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent should handle the message.
        
        Higher confidence for messages that seem ambiguous or
        when clarification has been requested.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        # Check if clarification was explicitly requested
        if context.get("needs_clarification"):
            return 0.95
        
        # Use base class keyword matching
        return await super().can_handle(message, context)

    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by checking for ambiguity.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with clarification if needed.
        """
        # Analyze message for ambiguity
        analysis, tokens_used = await self._analyze_message(message, context)
        
        if not analysis.get("clarification_needed", False):
            return AgentResult(
                response="Запрос понятен, уточнение не требуется.",
                agent_type=self.agent_type,
                confidence=0.5,
                metadata={
                    "clarification_needed": False,
                    "reason": analysis.get("reason", ""),
                },
                tokens_used=tokens_used,
            )
        
        # Format clarification response
        response = self._format_clarification_response(analysis)
        
        return AgentResult(
            response=response,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={
                "clarification_needed": True,
                "question": analysis.get("question", ""),
                "options": analysis.get("options", []),
                "reason": analysis.get("reason", ""),
            },
            tokens_used=tokens_used,
        )
    
    async def _analyze_message(
        self,
        message: str,
        context: dict[str, Any],
    ) -> tuple[dict[str, Any], int | None]:
        """Analyze message for ambiguity.
        
        Args:
            message: User message to analyze.
            context: Dialog context.
            
        Returns:
            Tuple of (analysis result dictionary, tokens used or None).
        """
        prompt = f"""Проанализируй запрос на наличие неопределенности.

Запрос: {message}

Определи:
1. Ясен ли запрос или требует уточнения
2. Если требует — сформулируй уточняющий вопрос
3. Если возможно — предложи варианты ответа"""

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=300)
        
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )
        
        # Parse JSON response
        try:
            start = response.content.find("{")
            end = response.content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response.content[start:end]), tokens_used
        except json.JSONDecodeError:
            pass
        
        # Default: no clarification needed
        return {
            "clarification_needed": False,
            "reason": "Не удалось проанализировать запрос",
        }, tokens_used
    
    def _format_clarification_response(self, analysis: dict[str, Any]) -> str:
        """Format clarification response for user.
        
        Args:
            analysis: Analysis result dictionary.
            
        Returns:
            Formatted response string.
        """
        question = analysis.get("question", "Уточните, пожалуйста, ваш запрос.")
        options = analysis.get("options", [])
        
        response = f"🤔 {question}"
        
        if options:
            response += "\n\nВарианты:\n"
            for i, option in enumerate(options[:4], 1):
                response += f"{i}. {option}\n"
        
        return response
