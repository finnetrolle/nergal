"""Comparison agent for structured comparison of options.

This agent creates structured comparisons between technologies,
approaches, or alternatives based on specified criteria.
"""

import json
import logging
from typing import Any

from nergal.dialog.agents.base_specialized import BaseSpecializedAgent
from nergal.dialog.constants import COMPARISON_KEYWORDS
from nergal.dialog.base import AgentResult, AgentType
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


class ComparisonAgent(BaseSpecializedAgent):
    """Agent for structured comparison of alternatives.
    
    This agent creates comparison matrices, evaluates options
    against criteria, and provides recommendations.
    
    Use cases:
    - Compare technologies or frameworks
    - Evaluate different approaches
    - Create decision matrices
    - Weighted scoring of alternatives
    
    Architecture Note:
        Uses hook-based can_handle() pattern with:
        - _keywords: Comparison-related keywords from COMPARISON_KEYWORDS
        - _patterns: Regex patterns for "vs", "или" constructs
        - _calculate_custom_confidence(): Hook for choice pattern detection
    """
    
    # Configure base class behavior
    _keywords = COMPARISON_KEYWORDS
    _context_keys = ["search_results", "previous_step_output"]
    _base_confidence = 0.3
    _keyword_boost = 0.2
    _context_boost = 0.2
    
    # Comparison-specific patterns
    _patterns = [
        r"\s+vs\.?\s+",  # "X vs Y" or "X vs. Y"
        r"\s+или\s+.*\?",  # "X или Y?" pattern
        r"против\s+",  # "X против Y"
    ]
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
        default_criteria: list[str] | None = None,
    ) -> None:
        """Initialize the comparison agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use.
            default_criteria: Default comparison criteria.
        """
        super().__init__(llm_provider, style_type)
        self._default_criteria = default_criteria or [
            "Производительность",
            "Простота использования",
            "Поддержка сообщества",
            "Стоимость",
            "Масштабируемость",
        ]
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.COMPARISON
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return """Ты — агент сравнения. Твоя задача — структурированно
сравнивать альтернативы по заданным критериям.

При сравнении:
1. Определи объекты сравнения
2. Выбери релевантные критерии
3. Оцени каждый объект по каждому критерию
4. Сформируй итоговую рекомендацию

Формат ответа:
## Сравнение: [Объекты]

### Критерии сравнения
[Список критериев]

### Сравнительная таблица
| Критерий | Вариант A | Вариант B |
|----------|-----------|-----------|
| ... | ... | ... |

### Анализ по критериям
[Детальный разбор]

### Итоговые оценки
- **Вариант A**: X/10 — когда выбрать
- **Вариант B**: Y/10 — когда выбрать

### Рекомендация
[Итоговый вывод с учётом контекста]"""

    async def _calculate_custom_confidence(
        self, message: str, context: dict[str, Any]
    ) -> float:
        """Hook for comparison-specific confidence calculation.
        
        Adds extra confidence when:
        - Message contains "или" with "?" (choice question)
        - Message contains "vs" pattern
        
        Args:
            message: Original user message.
            context: Current dialog context.
            
        Returns:
            Additional confidence boost.
        """
        message_lower = message.lower()
        
        # High confidence for "vs" pattern
        if " vs " in message_lower or " vs. " in message_lower:
            return 0.5  # Strong boost - this is definitely a comparison
        
        # Good confidence for "или" with question mark
        if " или " in message_lower and "?" in message:
            return 0.4  # Good boost - likely a choice question
        
        # Moderate confidence for "против" pattern
        if " против " in message_lower:
            return 0.3
        
        return 0.0
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by creating a structured comparison.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with comparison analysis.
        """
        # Extract items to compare
        items = self._extract_items(message)
        
        # Extract or generate criteria
        criteria = self._extract_criteria(message, context)
        
        # Gather information about items
        item_info = self._gather_item_info(items, context)
        
        # Generate comparison
        comparison, tokens_used = await self._generate_comparison(
            message, items, criteria, item_info
        )
        
        return AgentResult(
            response=comparison,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={
                "items": items,
                "criteria": criteria,
                "comparison_type": self._determine_comparison_type(items),
            },
            tokens_used=tokens_used,
        )
    
    def _extract_items(self, message: str) -> list[str]:
        """Extract items to compare from message.
        
        Args:
            message: User message.
            
        Returns:
            List of items to compare.
        """
        message_lower = message.lower()
        items = []
        
        # Check for "vs" pattern
        if " vs " in message_lower:
            parts = message_lower.split(" vs ")
        elif " vs. " in message_lower:
            parts = message_lower.split(" vs. ")
        elif " или " in message_lower:
            parts = message_lower.split(" или ")
        elif " против " in message_lower:
            parts = message_lower.split(" против ")
        else:
            return []
        
        for part in parts[:3]:  # Max 3 items
            # Clean up the item name
            item = part.strip()
            # Remove question marks and common words
            item = item.replace("?", "").strip()
            # Take first few words if too long
            words = item.split()[:3]
            item = " ".join(words)
            if item:
                items.append(item)
        
        return items
    
    def _extract_criteria(
        self,
        message: str,
        context: dict[str, Any],
    ) -> list[str]:
        """Extract or generate comparison criteria.
        
        Args:
            message: User message.
            context: Dialog context.
            
        Returns:
            List of comparison criteria.
        """
        # Check if criteria were specified in context
        if "comparison_criteria" in context:
            return context["comparison_criteria"]
        
        # Use default criteria
        return self._default_criteria.copy()
    
    def _gather_item_info(
        self,
        items: list[str],
        context: dict[str, Any],
    ) -> dict[str, str]:
        """Gather information about items from context.
        
        Args:
            items: Items to gather info for.
            context: Dialog context with previous results.
            
        Returns:
            Dictionary of item -> info.
        """
        info = {}
        agent_results = context.get("agent_results", {})
        
        for item in items:
            item_info = ""
            
            # Look for relevant info in previous results
            for agent_type, result in agent_results.items():
                if isinstance(result, dict):
                    content = result.get("response", "")
                else:
                    content = getattr(result, "response", "")
                
                if item.lower() in content.lower():
                    item_info += content[:500] + "\n"
            
            info[item] = item_info if item_info else "Информация не найдена"
        
        return info
    
    async def _generate_comparison(
        self,
        message: str,
        items: list[str],
        criteria: list[str],
        item_info: dict[str, str],
    ) -> tuple[str, int | None]:
        """Generate structured comparison.
        
        Args:
            message: Original message.
            items: Items to compare.
            criteria: Comparison criteria.
            item_info: Information about each item.
            
        Returns:
            Tuple of (comparison text, tokens used or None).
        """
        if not items:
            # No items detected, ask for clarification
            return "Пожалуйста, укажите, что вы хотите сравнить. Например: 'Сравни React и Vue'", None
        
        items_text = " и ".join(items)
        criteria_text = ", ".join(criteria)
        
        info_section = ""
        for item, info in item_info.items():
            if info != "Информация не найдена":
                info_section += f"\n### {item}\n{info}\n"
        
        prompt = f"""Создай структурированное сравнение.

Запрос: {message}

Объекты сравнения: {items_text}
Критерии: {criteria_text}

{"Доступная информация:" + info_section if info_section else ""}

Сравни объекты по указанным критериям и дай рекомендацию."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1500)
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )
        return response.content, tokens_used
    
    def _determine_comparison_type(self, items: list[str]) -> str:
        """Determine the type of comparison.
        
        Args:
            items: Items being compared.
            
        Returns:
            Comparison type identifier.
        """
        if not items:
            return "unknown"
        
        tech_keywords = [
            "python", "javascript", "typescript", "go", "rust", "java",
            "react", "vue", "angular", "django", "fastapi", "node",
            "kubernetes", "docker", "postgres", "mysql", "mongodb",
        ]
        
        items_lower = " ".join(items).lower()
        
        for kw in tech_keywords:
            if kw in items_lower:
                return "technology"
        
        return "general"
    
    async def compare_with_weights(
        self,
        items: list[str],
        criteria: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Perform weighted comparison.
        
        Args:
            items: Items to compare.
            criteria: List of criteria with weights.
            context: Dialog context.
            
        Returns:
            Weighted comparison result.
        """
        # criteria format: [{"name": "...", "weight": 0.3}, ...]
        
        prompt = f"""Выполни взвешенное сравнение объектов.

Объекты: {', '.join(items)}

Критерии с весами:
{json.dumps(criteria, ensure_ascii=False, indent=2)}

Оцени каждый объект по каждому критерию от 1 до 10.
Рассчитай взвешенную сумму для каждого объекта.

Ответь в JSON формате:
{{
    "scores": {{
        "объект1": {{"критерий1": оценка, "критерий2": оценка}},
        "объект2": {{...}}
    }},
    "weighted_scores": {{"объект1": сумма, "объект2": сумма}},
    "winner": "объект-победитель",
    "reasoning": "обоснование"
}}"""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=800)
        
        try:
            start = response.content.find("{")
            end = response.content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response.content[start:end])
        except json.JSONDecodeError:
            pass
        
        return {"error": "Failed to parse weighted comparison"}
    
    async def create_decision_matrix(
        self,
        items: list[str],
        criteria: list[str],
        context: dict[str, Any],
    ) -> str:
        """Create a decision matrix for comparison.
        
        Args:
            items: Items to compare.
            criteria: Comparison criteria.
            context: Dialog context.
            
        Returns:
            Markdown table with decision matrix.
        """
        comparison = await self._generate_comparison(
            "Создай матрицу решений", items, criteria, {}
        )
        return comparison
