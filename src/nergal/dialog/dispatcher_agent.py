"""Dispatcher agent for routing messages to appropriate agents.

This module provides an agent that analyzes incoming messages, creates
execution plans, and coordinates multiple agents to fulfill complex requests.
"""

import json
import logging
from typing import Any

from nergal.dialog.base import (
    AgentRegistry,
    AgentResult,
    AgentType,
    BaseAgent,
    ExecutionPlan,
    PlanStep,
)
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)

# Agent descriptions for the dispatcher prompt
AGENT_DESCRIPTIONS: dict[AgentType, str] = {
    # Core agents
    AgentType.DEFAULT: "общий агент для обычных разговоров, приветствий, простых вопросов, личных бесед, финального формирования ответа пользователю",
    
    # Information gathering agents
    AgentType.WEB_SEARCH: "агент для поиска информации в интернете, актуальных новостей, фактов, погоды, курсов валют",
    AgentType.KNOWLEDGE_BASE: "агент для поиска по корпоративной базе знаний, внутренней документации, регламентам, стандартам компании",
    AgentType.TECH_DOCS: "агент для поиска по технической документации библиотек и фреймворков, API справочники, примеры кода",
    AgentType.CODE_ANALYSIS: "агент для анализа кодовой базы, поиска использования функций, объяснения работы кода, архитектурного анализа",
    AgentType.METRICS: "агент для получения метрик производительности, статистики, KPI, количественных данных из систем мониторинга",
    AgentType.NEWS: "агент для агрегации новостей из нескольких источников, сравнения информации, выявления консенсуса и противоречий, отслеживания ссылок и оценки достоверности источников",
    
    # Processing agents
    AgentType.ANALYSIS: "агент для анализа данных, сравнения информации, выявления закономерностей, синтеза выводов",
    AgentType.FACT_CHECK: "агент для проверки фактов на достоверность, верификации информации из поиска, оценки надёжности источников",
    AgentType.COMPARISON: "агент для структурированного сравнения альтернатив, создания сравнительных таблиц, взвешенной оценки",
    AgentType.SUMMARY: "агент для резюмирования длинных текстов, выделения ключевых пунктов, создания TL;DR",
    AgentType.CLARIFICATION: "агент для уточнения неоднозначных запросов, генерации уточняющих вопросов, дисамбигуации",
    
    # Specialized agents
    AgentType.EXPERTISE: "агент для экспертных знаний в специфических доменах: безопасность, юридические вопросы, финансы, архитектура",
    
    # Legacy agents (kept for backward compatibility)
    AgentType.FAQ: "агент для ответов на часто задаваемые вопросы",
    AgentType.SMALL_TALK: "агент для легких разговоров и светской беседы",
    AgentType.TASK: "агент для выполнения конкретных задач",
}

# Example execution plans for different scenarios
EXAMPLE_PLANS = """
Примеры планов:

1. Простое приветствие:
{
    "steps": [
        {"agent": "default", "description": "ответить на приветствие"}
    ],
    "reasoning": "простое приветствие не требует дополнительных агентов"
}

2. Поиск актуальной информации:
{
    "steps": [
        {"agent": "web_search", "description": "найти актуальную информацию по запросу"},
        {"agent": "fact_check", "description": "проверить достоверность найденной информации", "is_optional": true},
        {"agent": "default", "description": "сформировать ответ пользователю на основе найденного"}
    ],
    "reasoning": "для ответа нужен поиск, затем проверка фактов и формирование ответа",
    "missing_agents": ["fact_check"],
    "missing_agents_reason": {"fact_check": "проверка достоверности информации из интернета"}
}

3. Обычный вопрос без поиска:
{
    "steps": [
        {"agent": "default", "description": "ответить на вопрос пользователя"}
    ],
    "reasoning": "вопрос не требует актуальной информации, можно ответить напрямую"
}
"""


class DispatcherAgent(BaseAgent):
    """Agent for dispatching messages and creating execution plans.

    This agent uses LLM to analyze messages, create execution plans with
    multiple steps, and coordinate between different agents.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        agent_registry: AgentRegistry | None = None,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        """Initialize the dispatcher agent.

        Args:
            llm_provider: LLM provider for analyzing messages.
            agent_registry: Registry of available agents for dynamic discovery.
            style_type: Response style (not used by dispatcher).
        """
        super().__init__(llm_provider, style_type)
        self._agent_registry = agent_registry

    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.DISPATCHER

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt dynamically based on available agents.

        Returns:
            System prompt with list of available agents.
        """
        # Get available agents
        available_agents = self._get_available_agents()

        # Build agent list description
        agent_list = []
        for agent_type in available_agents:
            description = AGENT_DESCRIPTIONS.get(
                agent_type, f"агент типа {agent_type.value}"
            )
            agent_list.append(f"- {agent_type.value}: {description}")

        agents_text = "\n".join(agent_list)

        prompt = f"""Ты — диспетчер-планировщик, который анализирует входящие сообщения и составляет план их обработки.

Доступные агенты:
{agents_text}

Твоя задача:
1. Проанализировать сообщение пользователя
2. Составить план выполнения из нескольких шагов
3. Указать каких агентов не хватает для идеального выполнения задачи

Отвечай ТОЛЬКО в формате JSON:
{{
    "steps": [
        {{"agent": "имя_агента", "description": "описание что делает этот шаг", "is_optional": false}}
    ],
    "reasoning": "краткое обоснование плана на русском языке",
    "missing_agents": ["агент1", "агент2"],
    "missing_agents_reason": {{"агент1": "зачем нужен этот агент"}}
}}

Правила составления плана:
- Для простых приветствий и разговоров достаточно одного агента default
- Для поиска информации: web_search -> default (для формирования ответа)
- Для поиска с проверкой: web_search -> fact_check -> default
- Всегда завершай план агентом default для формирования финального ответа
- Если нужного агента нет в списке доступных, добавь его в missing_agents
- is_optional: true если шаг можно пропустить при отсутствии агента

{EXAMPLE_PLANS}
"""
        return prompt

    def _get_available_agents(self) -> list[AgentType]:
        """Get list of available agent types from registry.

        Returns:
            List of available AgentType values.
        """
        if self._agent_registry is None:
            # Default agents if no registry
            return [AgentType.DEFAULT, AgentType.WEB_SEARCH]

        agents = []
        for agent in self._agent_registry.get_all():
            # Skip dispatcher itself to avoid infinite loop
            if agent.agent_type != AgentType.DISPATCHER:
                agents.append(agent.agent_type)

        # Always include default as fallback
        if AgentType.DEFAULT not in agents:
            agents.insert(0, AgentType.DEFAULT)

        return agents

    def set_agent_registry(self, registry: AgentRegistry) -> None:
        """Set the agent registry for dynamic agent discovery.

        Args:
            registry: AgentRegistry instance.
        """
        self._agent_registry = registry

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Dispatcher can always handle messages for routing.

        Args:
            message: User message to analyze.
            context: Current dialog context.

        Returns:
            Always returns 1.0 as dispatcher should always run first.
        """
        return 1.0

    async def create_plan(
        self,
        message: str,
        context: dict[str, Any],
    ) -> ExecutionPlan:
        """Analyze message and create an execution plan.

        Args:
            message: User message to analyze.
            context: Current dialog context.

        Returns:
            ExecutionPlan with steps to execute.
        """
        # Build context message with memory information
        context_parts = [f"Составь план для сообщения: {message}"]
        
        # Add memory context if available
        if "memory" in context:
            memory = context["memory"]
            profile_summary = memory.get("profile_summary", "")
            if profile_summary and profile_summary != "Информация о пользователе отсутствует.":
                context_parts.append(f"\nКонтекст о пользователе:\n{profile_summary}")
            
            recent_messages = memory.get("recent_messages", [])
            if recent_messages:
                context_parts.append("\nПоследние сообщения:")
                for msg in recent_messages[-3:]:  # Last 3 messages
                    role = "Пользователь" if msg.get("role") == "user" else "Ассистент"
                    content = msg.get("content", "")[:100]
                    context_parts.append(f"  {role}: {content}...")
        
        user_message = "\n".join(context_parts)
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=user_message),
        ]

        try:
            response = await self.llm_provider.generate(messages, max_tokens=500)
            plan = self._parse_plan_response(response.content)

            # Filter out missing agents that are actually available
            available_agents = set(self._get_available_agents())
            plan.missing_agents = [
                agent for agent in plan.missing_agents
                if agent not in available_agents
            ]
            # Also filter the reasons
            plan.missing_agents_reason = {
                agent: reason for agent, reason in plan.missing_agents_reason.items()
                if self._map_agent_type(agent.lower()) not in available_agents
            }

            # Get first 10 words of message for logging
            words = message.split()[:10]
            message_preview = " ".join(words)

            # Log the plan
            steps_desc = " -> ".join(s.agent_type.value for s in plan.steps)
            logger.info(
                f"я отправлю сообщение [{message_preview}] по плану: {steps_desc} потому что {plan.reasoning}"
            )

            # Log missing agents if any (only truly missing ones)
            if plan.has_missing_agents():
                logger.warning(
                    f"Для полноценного выполнения плана не хватает агентов: "
                    f"{', '.join(a.value for a in plan.missing_agents)}. "
                    f"Причины: {plan.missing_agents_reason}"
                )

            return plan

        except Exception as e:
            logger.warning(f"Dispatcher failed, falling back to default plan: {e}")
            words = message.split()[:10]
            message_preview = " ".join(words)
            logger.info(
                f"я отправлю сообщение [{message_preview}] агенту {AgentType.DEFAULT.value} потому что ошибка планирования: {e}"
            )
            # Return simple fallback plan
            return ExecutionPlan(
                steps=[PlanStep(agent_type=AgentType.DEFAULT, description="обработать сообщение")],
                reasoning=f"Ошибка планирования: {e}",
            )

    def _parse_plan_response(self, response: str) -> ExecutionPlan:
        """Parse LLM response to extract execution plan.

        Args:
            response: Raw LLM response text.

        Returns:
            ExecutionPlan with steps.
        """
        try:
            # Find JSON in response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)

                # Parse steps
                steps = []
                for step_data in data.get("steps", []):
                    agent_str = step_data.get("agent", "default").lower()
                    agent_type = self._map_agent_type(agent_str)
                    steps.append(PlanStep(
                        agent_type=agent_type,
                        description=step_data.get("description", ""),
                        input_transform=step_data.get("input_transform"),
                        is_optional=step_data.get("is_optional", False),
                    ))

                # Parse missing agents
                missing_agents = []
                missing_agents_reason = {}
                for agent_str in data.get("missing_agents", []):
                    agent_type = self._map_agent_type(agent_str.lower())
                    missing_agents.append(agent_type)
                    
                reasons = data.get("missing_agents_reason", {})
                for agent_str, reason in reasons.items():
                    missing_agents_reason[agent_str.lower()] = reason

                reasoning = data.get("reasoning", "план составлен автоматически")

                return ExecutionPlan(
                    steps=steps,
                    reasoning=reasoning,
                    missing_agents=missing_agents,
                    missing_agents_reason=missing_agents_reason,
                )

        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse JSON from dispatcher response: {response}, error: {e}")

        # Fallback: simple plan with default agent
        return ExecutionPlan(
            steps=[PlanStep(agent_type=AgentType.DEFAULT, description="обработать сообщение")],
            reasoning="не удалось разобрать план из ответа LLM",
        )

    def _map_agent_type(self, agent_str: str) -> AgentType:
        """Map string agent name to AgentType enum.

        Args:
            agent_str: String representation of agent type.

        Returns:
            Corresponding AgentType enum value.
        """
        mapping = {
            # Core agents
            "default": AgentType.DEFAULT,
            
            # Information gathering agents
            "web_search": AgentType.WEB_SEARCH,
            "websearch": AgentType.WEB_SEARCH,
            "search": AgentType.WEB_SEARCH,
            "knowledge_base": AgentType.KNOWLEDGE_BASE,
            "knowledge": AgentType.KNOWLEDGE_BASE,
            "kb": AgentType.KNOWLEDGE_BASE,
            "tech_docs": AgentType.TECH_DOCS,
            "techdocs": AgentType.TECH_DOCS,
            "documentation": AgentType.TECH_DOCS,
            "code_analysis": AgentType.CODE_ANALYSIS,
            "code": AgentType.CODE_ANALYSIS,
            "codeanalysis": AgentType.CODE_ANALYSIS,
            "metrics": AgentType.METRICS,
            "stats": AgentType.METRICS,
            "statistics": AgentType.METRICS,
            
            # Processing agents
            "fact_check": AgentType.FACT_CHECK,
            "factcheck": AgentType.FACT_CHECK,
            "fact-check": AgentType.FACT_CHECK,
            "analysis": AgentType.ANALYSIS,
            "analyze": AgentType.ANALYSIS,
            "comparison": AgentType.COMPARISON,
            "compare": AgentType.COMPARISON,
            "summary": AgentType.SUMMARY,
            "summarize": AgentType.SUMMARY,
            "tldr": AgentType.SUMMARY,
            "clarification": AgentType.CLARIFICATION,
            "clarify": AgentType.CLARIFICATION,
            
            # Specialized agents
            "expertise": AgentType.EXPERTISE,
            "expert": AgentType.EXPERTISE,
            "security": AgentType.EXPERTISE,
            "legal": AgentType.EXPERTISE,
            
            # Legacy agents
            "faq": AgentType.FAQ,
            "small_talk": AgentType.SMALL_TALK,
            "smalltalk": AgentType.SMALL_TALK,
            "task": AgentType.TASK,
        }
        return mapping.get(agent_str, AgentType.DEFAULT)

    async def dispatch(
        self,
        message: str,
        context: dict[str, Any],
    ) -> tuple[AgentType, str]:
        """Legacy method for backward compatibility.

        Args:
            message: User message to analyze.
            context: Current dialog context.

        Returns:
            Tuple of (first AgentType, reasoning string).
        """
        plan = await self.create_plan(message, context)
        if plan.steps:
            return plan.steps[0].agent_type, plan.reasoning
        return AgentType.DEFAULT, plan.reasoning

    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process message by creating an execution plan.

        Note: This method returns the plan. The actual execution is handled
        by DialogManager.

        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history for context.

        Returns:
            AgentResult with execution plan in metadata.
        """
        plan = await self.create_plan(message, context)
        return AgentResult(
            response=f"Plan: {' -> '.join(s.agent_type.value for s in plan.steps)}",
            agent_type=self.agent_type,
            confidence=1.0,
            metadata={
                "plan": plan,
                "steps": [(s.agent_type.value, s.description) for s in plan.steps],
                "missing_agents": [a.value for a in plan.missing_agents],
                "missing_agents_reason": plan.missing_agents_reason,
            },
            should_handoff=True,
            handoff_agent=plan.steps[0].agent_type if plan.steps else AgentType.DEFAULT,
        )
