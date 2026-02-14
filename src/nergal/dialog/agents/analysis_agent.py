"""Analysis agent for deep analysis and synthesis of information.

This agent analyzes information from multiple sources, identifies patterns,
and synthesizes comprehensive insights.
"""

import logging
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """Agent for analyzing and synthesizing information.
    
    This agent performs deep analysis of information gathered from
    other agents, identifies patterns, contradictions, and insights.
    
    Use cases:
    - Compare information from multiple sources
    - Identify contradictions or gaps
    - Synthesize comprehensive conclusions
    - Extract key insights from large amounts of data
    """
    
    # Keywords indicating need for analysis
    ANALYSIS_KEYWORDS = [
        "сравни", "проанализируй", "в чем разница", "преимущества",
        "недостатки", "плюсы", "минусы", "за и против", "выводы",
        "какой вывод", "что лучше", "что выбрать", "оцени",
    ]
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        """Initialize the analysis agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use.
        """
        super().__init__(llm_provider, style_type)
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.ANALYSIS
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return """Ты — аналитик, специализирующийся на глубоком анализе информации.

Твои задачи:
1. Анализировать информацию из нескольких источников
2. Выявлять закономерности, противоречия и пробелы
3. Синтезировать комплексные выводы
4. Формулировать рекомендации на основе анализа

Принципы работы:
- Объективность: рассматривай все точки зрения
- Структурированность: организуй анализ логично
- Доказательность: опирайся на факты
- Практичность: делай полезные выводы

Формат ответа:
## Краткое резюме
[1-2 предложения с главным выводом]

## Анализ
[Структурированный анализ с аргументами]

## Выводы
[Нумерованный список ключевых выводов]

## Рекомендации
[Практические рекомендации, если применимо]"""

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.
        
        Higher confidence for messages requiring analysis or
        when there's accumulated context from other agents.
        
        Args:
            message: User message to analyze.
            context: Current dialog context with accumulated data.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        message_lower = message.lower()
        
        # Check for analysis keywords
        for keyword in self.ANALYSIS_KEYWORDS:
            if keyword in message_lower:
                return 0.85
        
        # Check if there's accumulated context from other agents
        agent_results = context.get("agent_results", {})
        if len(agent_results) >= 2:
            return 0.8
        
        # Check for comparison patterns
        comparison_patterns = ["или", "против", "vs", "versus"]
        if any(pattern in message_lower for pattern in comparison_patterns):
            return 0.75
        
        return 0.3
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by analyzing available information.
        
        Args:
            message: User message to process.
            context: Current dialog context with accumulated data.
            history: Message history.
            
        Returns:
            AgentResult with analysis and conclusions.
        """
        # Gather context from previous agents
        gathered_info = self._gather_context(context)
        
        # Build analysis prompt
        analysis_prompt = self._build_analysis_prompt(message, gathered_info)
        
        # Generate analysis
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=analysis_prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1500)
        
        return AgentResult(
            response=response.content,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={
                "sources_analyzed": len(gathered_info.get("sources", [])),
                "analysis_type": self._determine_analysis_type(message),
            }
        )
    
    def _gather_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Gather information from previous agent results.
        
        Args:
            context: Context with agent results.
            
        Returns:
            Gathered information dictionary.
        """
        gathered = {
            "sources": [],
            "content": [],
            "metadata": {},
        }
        
        agent_results = context.get("agent_results", {})
        
        for agent_type, result in agent_results.items():
            if isinstance(result, dict):
                content = result.get("response", "")
                metadata = result.get("metadata", {})
            else:
                content = getattr(result, "response", "")
                metadata = getattr(result, "metadata", {})
            
            gathered["content"].append({
                "agent": agent_type,
                "content": content,
                "metadata": metadata,
            })
            
            if metadata.get("sources"):
                gathered["sources"].extend(metadata["sources"])
        
        return gathered
    
    def _build_analysis_prompt(
        self,
        message: str,
        gathered_info: dict[str, Any],
    ) -> str:
        """Build the analysis prompt with gathered context.
        
        Args:
            message: Original user message.
            gathered_info: Information gathered from other agents.
            
        Returns:
            Formatted analysis prompt.
        """
        prompt_parts = [f"Запрос пользователя: {message}\n"]
        
        if gathered_info["content"]:
            prompt_parts.append("\n## Собранная информация:\n")
            for info in gathered_info["content"]:
                agent = info["agent"]
                content = info["content"]
                prompt_parts.append(f"\n### От агента {agent}:\n{content}\n")
        
        prompt_parts.append("\nНа основе собранной информации проведи анализ и дай ответ.")
        
        return "\n".join(prompt_parts)
    
    def _determine_analysis_type(self, message: str) -> str:
        """Determine the type of analysis needed.
        
        Args:
            message: User message.
            
        Returns:
            Analysis type identifier.
        """
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["сравни", "разница", "vs", "или"]):
            return "comparison"
        elif any(kw in message_lower for kw in ["преимущества", "плюсы", "за"]):
            return "pros_analysis"
        elif any(kw in message_lower for kw in ["недостатки", "минусы", "против"]):
            return "cons_analysis"
        elif any(kw in message_lower for kw in ["оцени", "рейтинг"]):
            return "evaluation"
        elif any(kw in message_lower for kw in ["вывод", "итог", "резюме"]):
            return "synthesis"
        else:
            return "general"
    
    async def compare_sources(
        self,
        sources: list[dict[str, Any]],
        criteria: list[str] | None = None,
    ) -> str:
        """Compare multiple sources on specified criteria.
        
        Args:
            sources: List of source dictionaries with content.
            criteria: Optional list of comparison criteria.
            
        Returns:
            Comparative analysis text.
        """
        criteria_text = ", ".join(criteria) if criteria else "общие характеристики"
        
        sources_text = "\n\n".join([
            f"Источник {i+1}: {s.get('content', '')}"
            for i, s in enumerate(sources)
        ])
        
        prompt = f"""Сравни следующие источники по критериям: {criteria_text}

{sources_text}

Проведи сравнительный анализ и выдели ключевые различия."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1000)
        return response.content
    
    async def identify_contradictions(
        self,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Identify contradictions between sources.
        
        Args:
            sources: List of sources to analyze.
            
        Returns:
            List of identified contradictions.
        """
        sources_text = "\n\n".join([
            f"[{s.get('source', i)}] {s.get('content', '')}"
            for i, s in enumerate(sources)
        ])
        
        prompt = f"""Проанализируй следующие источники на наличие противоречий:

{sources_text}

Выяви все противоречия и несоответствия. Отметь, какие источники противоречат друг другу и в чем именно."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=800)
        
        # Return structured result (simplified for now)
        return [{
            "analysis": response.content,
            "sources_compared": len(sources),
        }]
