"""Analysis agent for deep analysis and synthesis of information.

This agent analyzes information from multiple sources, identifies patterns,
and synthesizes comprehensive insights.
"""

import logging
from typing import Any

from nergal.dialog.agents.base_specialized import BaseSpecializedAgent
from nergal.dialog.constants import ANALYSIS_KEYWORDS
from nergal.dialog.base import AgentResult, AgentType
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseSpecializedAgent):
    """Agent for analyzing and synthesizing information.
    
    This agent performs deep analysis of information gathered from
    other agents, identifies patterns, contradictions, and insights.
    
    Use cases:
    - Compare information from multiple sources
    - Identify contradictions or gaps
    - Synthesize comprehensive conclusions
    - Extract key insights from large amounts of data
    """
    
    # Configure base class behavior
    _keywords = ANALYSIS_KEYWORDS
    _context_keys = ["search_results", "previous_step_output"]
    _base_confidence = 0.25
    _keyword_boost = 0.15
    _context_boost = 0.35
    
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
