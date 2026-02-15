"""Expertise agent for domain-specific knowledge.

This agent provides specialized knowledge in specific domains
like security, legal, finance, or other expert areas.
"""

import logging
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


class ExpertiseDomain:
    """Enumeration of expertise domains."""
    
    SECURITY = "security"
    LEGAL = "legal"
    FINANCE = "finance"
    HR = "hr"
    COMPLIANCE = "compliance"
    ARCHITECTURE = "architecture"
    GENERAL = "general"


class ExpertiseAgent(BaseAgent):
    """Agent for domain-specific expertise.
    
    This agent provides specialized knowledge and advice
    in specific domains like security, legal, or finance.
    
    Use cases:
    - Security best practices
    - Legal compliance questions
    - Financial analysis
    - HR policies
    """
    
    # Domain-specific keywords
    DOMAIN_KEYWORDS = {
        ExpertiseDomain.SECURITY: [
            "безопасность", "уязвимость", "взлом", "хакер", "защита",
            "security", "vulnerability", "exploit", "аутентификация",
            "шифрование", "пароль", "доступ", "права", "audit",
        ],
        ExpertiseDomain.LEGAL: [
            "закон", "право", "юридическ", "договор", "контракт",
            "лицензия", "copyright", "патент", "gdpr", "персональные данные",
            "согласие", "регламент", "compliance", "норматив",
        ],
        ExpertiseDomain.FINANCE: [
            "бюджет", "расход", "доход", "финанс", "инвестици",
            "roi", "cost", "бухгалтер", "налог", "платеж",
            "биллинг", "смета", "фактура",
        ],
        ExpertiseDomain.HR: [
            "кадр", "сотрудник", "найм", "увольнение", "отпуск",
            "зарплата", "премия", "оценка", "аттестация", "обучение",
            "карьера", "позиция", "вакансия",
        ],
        ExpertiseDomain.COMPLIANCE: [
            "соответствие", "стандарт", "iso", "сертификат",
            "аудит", "проверка", "регулятор", "требование",
        ],
        ExpertiseDomain.ARCHITECTURE: [
            "архитектура", "паттерн", "микросервис", "монолит",
            "масштабирова", "надежность", "отказоустойчивость",
            "distributed", "scalability",
        ],
    }
    
    # Domain-specific system prompts
    DOMAIN_PROMPTS = {
        ExpertiseDomain.SECURITY: """Ты — эксперт по информационной безопасности.
Специализируешься на защите данных, анализе уязвимостей и best practices.

При ответе:
1. Оцени риски
2. Приведи конкретные рекомендации
3. Укажи на потенциальные угрозы
4. Предложи меры защиты

Всегда предупреждай о важности тестирования изменений.""",

        ExpertiseDomain.LEGAL: """Ты — эксперт по юридическим вопросам в IT.
Специализируешься на лицензиях, защите данных и корпоративном праве.

При ответе:
1. Укажи применимое законодательство
2. Приведи риски и последствия
3. Рекомендуй проконсультироваться с юристом для важных решений
4. Ссылайся на конкретные нормы если применимо

Важно: твои советы носят информационный характер.""",

        ExpertiseDomain.FINANCE: """Ты — эксперт по финансовым вопросам в IT-компаниях.
Специализируешься на бюджетировании, инвестициях и финансовом анализе.

При ответе:
1. Приведи цифры и расчёты
2. Оцени финансовые риски
3. Предложи альтернативы
4. Укажи на скрытые затраты""",

        ExpertiseDomain.HR: """Ты — эксперт по кадровым вопросам.
Специализируешься на управлении персоналом в IT-компаниях.

При ответе:
1. Учитывай трудовое законодательство
2. Приведи best practices
3. Предложи конкретные действия
4. Укажи на возможные риски""",

        ExpertiseDomain.COMPLIANCE: """Ты — эксперт по соответствию стандартам и регуляторным требованиям.
Специализируешься на ISO, GDPR и отраслевых стандартах.

При ответе:
1. Укажи применимые стандарты
2. Приведи требования
3. Предложи план действий
4. Укажи на типичные нарушения""",

        ExpertiseDomain.ARCHITECTURE: """Ты — эксперт по программной архитектуре.
Специализируешься на проектировании масштабируемых и надёжных систем.

При ответе:
1. Приведи паттерны и анти-паттерны
2. Оцени trade-offs
3. Предложи альтернативы
4. Учитывай долгосрочную перспективу""",
    }
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        default_domain: str = ExpertiseDomain.GENERAL,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        """Initialize the expertise agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            default_domain: Default expertise domain.
            style_type: Response style to use.
        """
        super().__init__(llm_provider, style_type)
        self._default_domain = default_domain
        self._current_domain = default_domain
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.EXPERTISE
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        domain_prompt = self.DOMAIN_PROMPTS.get(
            self._current_domain,
            self.DOMAIN_PROMPTS[ExpertiseDomain.GENERAL]
        )
        
        return f"""{domain_prompt}

Формат ответа:
## Краткий ответ
[Суть в 1-2 предложениях]

## Детали
[Подробное объяснение]

## Рекомендации
[Конкретные действия]

## Предупреждения
[Риски и ограничения если есть]"""
    
    def set_domain(self, domain: str) -> None:
        """Set the current expertise domain.
        
        Args:
            domain: Domain identifier.
        """
        self._current_domain = domain
    
    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.
        
        Higher confidence for domain-specific questions.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        message_lower = message.lower()
        
        # Check for domain-specific keywords
        max_confidence = 0.2
        detected_domain = None
        
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in message_lower)
            if matches >= 2:
                confidence = 0.85
                if confidence > max_confidence:
                    max_confidence = confidence
                    detected_domain = domain
            elif matches == 1:
                confidence = 0.65
                if confidence > max_confidence:
                    max_confidence = confidence
                    detected_domain = domain
        
        if detected_domain:
            self._current_domain = detected_domain
        
        return max_confidence
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message with domain expertise.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with expert advice.
        """
        # Detect domain from message
        detected_domain = self._detect_domain(message)
        if detected_domain != ExpertiseDomain.GENERAL:
            self._current_domain = detected_domain
        
        # Gather relevant context
        relevant_context = self._gather_domain_context(message, context)
        
        # Generate expert response
        response, tokens_used = await self._generate_expert_response(
            message, relevant_context, self._current_domain
        )
        
        return AgentResult(
            response=response,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={
                "domain": self._current_domain,
                "detected_domain": detected_domain,
            },
            tokens_used=tokens_used,
        )
    
    def _detect_domain(self, message: str) -> str:
        """Detect expertise domain from message.
        
        Args:
            message: User message.
            
        Returns:
            Detected domain identifier.
        """
        message_lower = message.lower()
        
        domain_scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            domain_scores[domain] = score
        
        max_domain = max(domain_scores, key=domain_scores.get)
        max_score = domain_scores[max_domain]
        
        if max_score >= 1:
            return max_domain
        
        return ExpertiseDomain.GENERAL
    
    def _gather_domain_context(
        self,
        message: str,
        context: dict[str, Any],
    ) -> str:
        """Gather context relevant to the domain.
        
        Args:
            message: User message.
            context: Dialog context.
            
        Returns:
            Relevant context string.
        """
        context_parts = []
        
        # Get relevant info from previous agent results
        agent_results = context.get("agent_results", {})
        
        for agent_type, result in agent_results.items():
            if isinstance(result, dict):
                content = result.get("response", "")
            else:
                content = getattr(result, "response", "")
            
            if content:
                context_parts.append(f"[{agent_type}]\n{content[:500]}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_expert_response(
        self,
        message: str,
        relevant_context: str,
        domain: str,
    ) -> tuple[str, int | None]:
        """Generate expert response.
        
        Args:
            message: User message.
            relevant_context: Relevant context.
            domain: Expertise domain.
            
        Returns:
            Tuple of (expert response, tokens used or None).
        """
        domain_prompt = self.DOMAIN_PROMPTS.get(
            domain,
            self.DOMAIN_PROMPTS[ExpertiseDomain.GENERAL]
        )
        
        prompt = f"""{domain_prompt}

Вопрос: {message}

{f"Контекст: {relevant_context}" if relevant_context else ""}

Дай экспертный ответ в указанном формате."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1200)
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )
        return response.content, tokens_used
    
    async def get_security_assessment(self, topic: str) -> tuple[str, int | None]:
        """Get security assessment for a topic.
        
        Args:
            topic: Topic to assess.
            
        Returns:
            Tuple of (security assessment, tokens used or None).
        """
        self._current_domain = ExpertiseDomain.SECURITY
        return await self._generate_expert_response(
            f"Проведи оценку безопасности: {topic}",
            "",
            ExpertiseDomain.SECURITY
        )
    
    async def get_legal_analysis(self, topic: str) -> tuple[str, int | None]:
        """Get legal analysis for a topic.
        
        Args:
            topic: Topic to analyze.
            
        Returns:
            Tuple of (legal analysis, tokens used or None).
        """
        self._current_domain = ExpertiseDomain.LEGAL
        return await self._generate_expert_response(
            f"Дай юридический анализ: {topic}",
            "",
            ExpertiseDomain.LEGAL
        )
    
    async def get_architecture_review(self, description: str) -> tuple[str, int | None]:
        """Get architecture review.
        
        Args:
            description: Architecture description.
            
        Returns:
            Tuple of (architecture review, tokens used or None).
        """
        self._current_domain = ExpertiseDomain.ARCHITECTURE
        return await self._generate_expert_response(
            f"Проведи ревью архитектуры: {description}",
            "",
            ExpertiseDomain.ARCHITECTURE
        )
