"""Fact check agent for verifying information accuracy.

This agent cross-references information from multiple sources
to verify claims and assess reliability.
"""

import logging
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


class FactCheckAgent(BaseAgent):
    """Agent for verifying facts and claims.
    
    This agent cross-references information from multiple sources,
    assesses source reliability, and provides verification results.
    
    Use cases:
    - Verify claims from web search results
    - Check accuracy of statements
    - Assess source reliability
    - Identify outdated or incorrect information
    """
    
    # Keywords indicating need for fact-checking
    FACT_CHECK_KEYWORDS = [
        "правда", "верно", "точно", "действительно", "проверь",
        "подтверди", "так ли", "правильно ли", "актуально",
        "достоверно", "официально", "источник",
    ]
    
    # Reliability scores for different source types
    SOURCE_RELIABILITY = {
        "official": 0.9,      # Official documentation
        "academic": 0.85,     # Academic papers
        "news": 0.7,          # News sites
        "blog": 0.5,          # Blogs and personal sites
        "social": 0.3,        # Social media
        "unknown": 0.5,       # Unknown sources
    }
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
        min_sources: int = 2,
    ) -> None:
        """Initialize the fact check agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use.
            min_sources: Minimum sources for verification.
        """
        super().__init__(llm_provider, style_type)
        self._min_sources = min_sources
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.FACT_CHECK
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return """Ты — агент проверки фактов. Твоя задача — верифицировать
информацию путём перекрёстной проверки источников.

Критерии оценки:
1. Подтверждение: факт подтверждён несколькими независимыми источниками
2. Частичное подтверждение: часть информации подтверждена
3. Опровержение: источники противоречат информации
4. Недостаточно данных: мало источников для проверки

Оценивай надёжность источников:
- Официальная документация: высокая надёжность
- Академические источники: высокая надёжность
- Новости: средняя надёжность
- Блоги: низкая надёжность
- Социальные сети: очень низкая надёжность

Формат ответа:
## Результат проверки
[Подтверждено / Частично подтверждено / Опровергнуто / Недостаточно данных]

## Анализ источников
[Оценка каждого источника]

## Вывод
[Итоговое заключение о достоверности]"""

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.
        
        Higher confidence for messages about verification or
        when there's information to verify from other agents.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        message_lower = message.lower()
        
        # Check for fact-check keywords
        for keyword in self.FACT_CHECK_KEYWORDS:
            if keyword in message_lower:
                return 0.85
        
        # Check if there's web search results to verify
        agent_results = context.get("agent_results", {})
        if "web_search" in agent_results:
            return 0.7
        
        # Questions about accuracy or truth
        if "?" in message and any(kw in message_lower for kw in ["ли", "правда", "так"]):
            return 0.65
        
        return 0.2
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by verifying available information.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with verification results.
        """
        # Get information to verify
        info_to_verify = self._extract_info_to_verify(message, context)
        
        if not info_to_verify:
            return AgentResult(
                response="Нет информации для проверки фактов.",
                agent_type=self.agent_type,
                confidence=0.3,
                metadata={"verified": False, "reason": "no_info"}
            )
        
        # Perform verification
        verification_result = await self._verify_information(info_to_verify, context)
        
        # Generate response
        response_text = await self._generate_verification_response(
            info_to_verify, verification_result
        )
        
        return AgentResult(
            response=response_text,
            agent_type=self.agent_type,
            confidence=verification_result.get("confidence", 0.7),
            metadata={
                "verified": True,
                "result": verification_result.get("result"),
                "sources_checked": verification_result.get("sources_checked", 0),
                "reliability_score": verification_result.get("reliability_score"),
            }
        )
    
    def _extract_info_to_verify(
        self,
        message: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Extract information that needs verification.
        
        Args:
            message: User message.
            context: Dialog context with previous results.
            
        Returns:
            Information to verify or None.
        """
        info = {
            "claim": message,
            "sources": [],
        }
        
        # Get sources from web search results
        agent_results = context.get("agent_results", {})
        
        if "web_search" in agent_results:
            ws_result = agent_results["web_search"]
            if isinstance(ws_result, dict):
                info["sources"] = ws_result.get("metadata", {}).get("sources", [])
                info["content"] = ws_result.get("response", "")
            else:
                info["sources"] = getattr(ws_result, "metadata", {}).get("sources", [])
                info["content"] = getattr(ws_result, "response", "")
        
        return info if info["sources"] or info.get("content") else None
    
    async def _verify_information(
        self,
        info: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Verify information against sources.
        
        Args:
            info: Information to verify with sources.
            context: Dialog context.
            
        Returns:
            Verification result dictionary.
        """
        sources = info.get("sources", [])
        content = info.get("content", "")
        claim = info.get("claim", "")
        
        # Calculate reliability score
        reliability_score = self._calculate_reliability(sources)
        
        # Use LLM to analyze consistency
        consistency_analysis = await self._analyze_consistency(claim, content, sources)
        
        return {
            "result": consistency_analysis.get("result", "insufficient"),
            "confidence": consistency_analysis.get("confidence", 0.5),
            "sources_checked": len(sources),
            "reliability_score": reliability_score,
            "analysis": consistency_analysis.get("analysis", ""),
        }
    
    def _calculate_reliability(self, sources: list[str]) -> float:
        """Calculate overall reliability score for sources.
        
        Args:
            sources: List of source identifiers.
            
        Returns:
            Reliability score (0.0 to 1.0).
        """
        if not sources:
            return 0.0
        
        scores = []
        for source in sources:
            source_lower = source.lower()
            
            if any(kw in source_lower for kw in ["official", "docs", "documentation"]):
                scores.append(self.SOURCE_RELIABILITY["official"])
            elif any(kw in source_lower for kw in ["arxiv", "academic", "edu", "research"]):
                scores.append(self.SOURCE_RELIABILITY["academic"])
            elif any(kw in source_lower for kw in ["news", "times", "post", "journal"]):
                scores.append(self.SOURCE_RELIABILITY["news"])
            elif any(kw in source_lower for kw in ["blog", "medium", "substack"]):
                scores.append(self.SOURCE_RELIABILITY["blog"])
            elif any(kw in source_lower for kw in ["twitter", "reddit", "facebook"]):
                scores.append(self.SOURCE_RELIABILITY["social"])
            else:
                scores.append(self.SOURCE_RELIABILITY["unknown"])
        
        return sum(scores) / len(scores) if scores else 0.5
    
    async def _analyze_consistency(
        self,
        claim: str,
        content: str,
        sources: list[str],
    ) -> dict[str, Any]:
        """Analyze consistency of claim with found content.
        
        Args:
            claim: Original claim to verify.
            content: Found content.
            sources: List of sources.
            
        Returns:
            Consistency analysis result.
        """
        prompt = f"""Проанализируй, подтверждается ли утверждение найденной информацией.

Утверждение: {claim}

Найденная информация:
{content[:2000]}

Источники: {', '.join(sources[:5]) if sources else 'не указаны'}

Определи:
1. Подтверждается ли утверждение?
2. Насколько надёжны источники?
3. Есть ли противоречия?

Ответь в JSON формате:
{{
    "result": "confirmed/partially_confirmed/refuted/insufficient",
    "confidence": 0.0-1.0,
    "analysis": "краткий анализ"
}}"""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        try:
            response = await self.llm_provider.generate(messages, max_tokens=500)
            # Parse JSON from response
            import json
            start = response.content.find("{")
            end = response.content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response.content[start:end])
        except Exception as e:
            logger.warning(f"Consistency analysis failed: {e}")
        
        return {"result": "insufficient", "confidence": 0.5, "analysis": ""}
    
    async def _generate_verification_response(
        self,
        info: dict[str, Any],
        verification: dict[str, Any],
    ) -> str:
        """Generate human-readable verification response.
        
        Args:
            info: Original information.
            verification: Verification results.
            
        Returns:
            Formatted response text.
        """
        result = verification.get("result", "insufficient")
        confidence = verification.get("confidence", 0.5)
        reliability = verification.get("reliability_score", 0.5)
        
        result_labels = {
            "confirmed": "✅ Подтверждено",
            "partially_confirmed": "⚠️ Частично подтверждено",
            "refuted": "❌ Опровергнуто",
            "insufficient": "❓ Недостаточно данных",
        }
        
        label = result_labels.get(result, "❓ Неизвестно")
        
        response = f"""## {label}

**Уровень доверия:** {confidence * 100:.0f}%
**Надёжность источников:** {reliability * 100:.0f}%

{verification.get("analysis", "")}

Проверено источников: {verification.get("sources_checked", 0)}"""
        
        return response
    
    async def check_claim(self, claim: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
        """Check a specific claim against provided sources.
        
        Args:
            claim: The claim to verify.
            sources: List of sources with content.
            
        Returns:
            Verification result.
        """
        return await self._verify_information({
            "claim": claim,
            "sources": [s.get("source", "") for s in sources],
            "content": "\n".join([s.get("content", "") for s in sources]),
        }, {})
