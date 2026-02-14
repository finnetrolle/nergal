"""Clarification agent for disambiguating user queries.

This agent analyzes user messages for ambiguity and generates
clarifying questions when needed.
"""

import json
import logging
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


class ClarificationAgent(BaseAgent):
    """Agent for clarifying ambiguous user queries.
    
    This agent determines if a user's question is ambiguous and
    generates appropriate clarifying questions to improve understanding.
    
    The agent can:
    - Detect ambiguity in queries
    - Generate clarifying questions
    - Interpret user responses to clarifications
    """
    
    # Ambiguity indicators
    AMBIGUITY_INDICATORS = [
        "настроить", "проблема", "ошибка", "не работает",
        "лучше", "оптимальный", "правильный", "нужно",
        "сделать", "изменить", "проверить", "понять",
    ]
    
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
        
        # Check for ambiguity indicators
        message_lower = message.lower()
        indicator_count = sum(
            1 for indicator in self.AMBIGUITY_INDICATORS
            if indicator in message_lower
        )
        
        if indicator_count >= 2:
            return 0.7
        elif indicator_count == 1:
            return 0.5
        
        # Short questions might need clarification
        words = message.split()
        if len(words) <= 3 and "?" in message:
            return 0.6
        
        return 0.2
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message and determine if clarification is needed.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with clarification question or confirmation.
        """
        # Check if we already have clarification count
        clarification_count = context.get("clarification_count", 0)
        
        if clarification_count >= self._max_clarifications:
            # Max clarifications reached, proceed without
            return AgentResult(
                response="Продолжаю с текущей информацией.",
                agent_type=self.agent_type,
                confidence=0.5,
                metadata={
                    "clarification_needed": False,
                    "max_reached": True,
                }
            )
        
        # Analyze for ambiguity
        analysis = await self._analyze_query(message, history)
        
        if not analysis.get("clarification_needed", False):
            return AgentResult(
                response="Запрос понятен, уточнение не требуется.",
                agent_type=self.agent_type,
                confidence=0.8,
                metadata={
                    "clarification_needed": False,
                    "reason": analysis.get("reason", ""),
                }
            )
        
        # Generate clarification question
        question = analysis.get("question", "Уточните, пожалуйста, ваш запрос.")
        options = analysis.get("options", [])
        
        # Format response with options if available
        if options:
            options_text = "\n".join(f"• {opt}" for opt in options)
            response = f"{question}\n\nВарианты:\n{options_text}"
        else:
            response = question
        
        return AgentResult(
            response=response,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={
                "clarification_needed": True,
                "question": question,
                "options": options,
                "reason": analysis.get("reason", ""),
            }
        )
    
    async def _analyze_query(
        self,
        message: str,
        history: list[LLMMessage],
    ) -> dict[str, Any]:
        """Analyze query for ambiguity using LLM.
        
        Args:
            message: User message to analyze.
            history: Conversation history for context.
            
        Returns:
            Analysis result with clarification details.
        """
        # Build context from recent history
        recent_context = ""
        if history:
            recent_messages = history[-3:]  # Last 3 messages
            recent_context = "\n".join([
                f"{'Пользователь' if msg.role == MessageRole.USER else 'Ассистент'}: {msg.content[:100]}"
                for msg in recent_messages
            ])
        
        analysis_prompt = f"""Проанализируй запрос пользователя на наличие неопределенности.

{"Контекст разговора:" + chr(10) + recent_context if recent_context else ""}

Запрос пользователя: {message}

Нужно ли уточнение? Отвечай в JSON формате."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=analysis_prompt),
        ]
        
        try:
            response = await self.llm_provider.generate(messages, max_tokens=300)
            return self._parse_analysis_response(response.content)
        except Exception as e:
            logger.warning(f"Clarification analysis failed: {e}")
            return {"clarification_needed": False, "reason": str(e)}
    
    def _parse_analysis_response(self, response: str) -> dict[str, Any]:
        """Parse LLM response for analysis result.
        
        Args:
            response: Raw LLM response.
            
        Returns:
            Parsed analysis dictionary.
        """
        try:
            # Find JSON in response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse clarification response: {e}")
        
        return {"clarification_needed": False, "reason": "Failed to parse response"}
    
    async def interpret_response(
        self,
        user_response: str,
        clarification_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Interpret user's response to a clarification question.
        
        Args:
            user_response: User's answer to clarification.
            clarification_context: Context from original clarification.
            
        Returns:
            Interpreted response with clarified intent.
        """
        options = clarification_context.get("options", [])
        
        if not options:
            return {"interpreted": True, "clarification": user_response}
        
        # Check if user selected one of the options
        user_response_lower = user_response.lower().strip()
        
        for i, option in enumerate(options, 1):
            if (user_response_lower == str(i) or
                user_response_lower == option.lower() or
                option.lower() in user_response_lower):
                return {
                    "interpreted": True,
                    "selected_option": i - 1,
                    "clarification": option,
                }
        
        # User provided custom response
        return {"interpreted": True, "clarification": user_response}
