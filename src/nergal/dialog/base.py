"""Agent system for handling different types of user requests.

This module provides base classes and registry for managing agents.
Agents are responsible for handling specific types of user requests.

Individual agents are in separate modules:
- default_agent.py - DefaultAgent for general conversations
- dispatcher_agent.py - DispatcherAgent for routing messages
- web_search_agent.py - WebSearchAgent for web search queries
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, LLMResponse


class AgentCategory(str, Enum):
    """Categories for grouping agents by their purpose."""
    
    CORE = "core"                    # Core agents for basic functionality
    INFORMATION = "information"       # Agents that retrieve/gather information
    PROCESSING = "processing"         # Agents that process/analyze information
    SPECIALIZED = "specialized"       # Domain-specific agents


class AgentType(str, Enum):
    """Types of agents available in the system.

    Agents are organized by category:
    - Core: default, dispatcher
    - Information: web_search
    - Specialized: todoist
    """

    # Core agents
    DEFAULT = "default"
    DISPATCHER = "dispatcher"

    # Information gathering agents
    WEB_SEARCH = "web_search"

    # Specialized agents
    TODOIST = "todoist"  # Todoist task management agent
    HEALTH = "health"  # Health metrics tracking agent
    REMINDER = "reminder"  # General-purpose reminders agent

    @classmethod
    def get_category(cls, agent_type: "AgentType") -> AgentCategory:
        """Get the category for an agent type."""
        if agent_type in (cls.DEFAULT, cls.DISPATCHER):
            return AgentCategory.CORE
        elif agent_type in (cls.WEB_SEARCH,):
            return AgentCategory.INFORMATION
        elif agent_type in (cls.TODOIST, cls.HEALTH, cls.REMINDER):
            return AgentCategory.SPECIALIZED
        else:
            return AgentCategory.CORE


@dataclass
class PlanStep:
    """A single step in an execution plan.

    Attributes:
        agent_type: Type of agent to execute.
        description: Human-readable description of what this step does.
        input_transform: Optional transformation to apply to input (e.g., use previous output).
        is_optional: Whether this step can be skipped if agent is unavailable.
        depends_on: List of step indices this step depends on (empty = no dependency, can run in parallel).
        parallel_group: Optional group ID for steps that can run in parallel.
    """

    agent_type: AgentType
    description: str
    input_transform: str | None = None  # "original", "previous", or custom instruction
    is_optional: bool = False
    depends_on: list[int] = field(default_factory=list)  # List of step indices this depends on
    parallel_group: int | None = None  # Group ID for parallel execution


@dataclass
class ExecutionPlan:
    """A plan for executing multiple agents in sequence.

    The dispatcher creates execution plans to process complex requests
    that require multiple agents working together.

    Attributes:
        steps: List of steps to execute in order.
        reasoning: Explanation of why this plan was chosen.
        missing_agents: List of agent types that would be useful but are not available.
        missing_agents_reason: Explanation of what each missing agent would do.
    """

    steps: list[PlanStep]
    reasoning: str
    missing_agents: list[AgentType] = field(default_factory=list)
    missing_agents_reason: dict[str, str] = field(default_factory=dict)

    def get_agent_types(self) -> list[AgentType]:
        """Get list of all agent types needed for this plan."""
        return [step.agent_type for step in self.steps]

    def has_missing_agents(self) -> bool:
        """Check if plan requires agents that are not available."""
        return len(self.missing_agents) > 0


@dataclass
class AgentResult:
    """Result of agent processing.

    Attributes:
        response: The text response from the agent.
        agent_type: The type of agent that produced this result.
        confidence: Confidence score of the result (0.0 to 1.0).
        metadata: Additional metadata about the result.
        should_handoff: Whether this agent should hand off to another.
        handoff_agent: The agent type to hand off to, if applicable.
        tokens_used: Total tokens consumed (prompt + completion).
    """

    response: str
    agent_type: AgentType
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    should_handoff: bool = False
    handoff_agent: AgentType | None = None
    tokens_used: int | None = None  # Total tokens (prompt + completion)

    def get_typed_metadata(self) -> "BaseAgentMetadata | None":
        """Get typed metadata based on agent type.

        Returns:
            Typed metadata instance if metadata exists, None otherwise.
        """
        if not self.metadata:
            return None

        from nergal.dialog.metadata import create_metadata_from_dict

        return create_metadata_from_dict(self.agent_type.value, self.metadata)


@dataclass
class StepResult:
    """Result of executing a single step in an execution plan.

    Captures all information about a step execution for use by subsequent steps.

    Attributes:
        step_index: Index of the step in the execution plan.
        agent_type: Type of agent that executed this step.
        output: The text output from the agent.
        structured_data: Structured data extracted from the result (e.g., search results).
        confidence: Confidence score of the result (0.0 to 1.0).
        execution_time_ms: Time taken to execute the step in milliseconds.
        success: Whether the step completed successfully.
        error_message: Error message if the step failed.
    """

    step_index: int
    agent_type: AgentType
    output: str
    structured_data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    execution_time_ms: float = 0.0
    success: bool = True
    error_message: str | None = None

    def to_context_string(self) -> str:
        """Generate a string representation for context passing.

        Returns:
            Formatted string with step result summary.
        """
        status = "✓" if self.success else "✗"
        lines = [
            f"[Step {self.step_index}] {self.agent_type.value} {status}",
            f"Output: {self.output[:500]}{'...' if len(self.output) > 500 else ''}",
        ]
        if self.structured_data:
            lines.append(f"Data: {list(self.structured_data.keys())}")
        if not self.success and self.error_message:
            lines.append(f"Error: {self.error_message}")
        return "\n".join(lines)


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Agents are responsible for handling specific types of user requests.
    Each agent can decide if it can handle a request and process it.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        """Initialize the agent.

        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use for this agent.
        """
        self.llm_provider = llm_provider
        self._style_type = style_type

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    @abstractmethod
    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.

        Args:
            message: User message to analyze.
            context: Current dialog context.

        Returns:
            Confidence score (0.0 to 1.0) indicating how well this agent
            can handle the message.
        """
        pass

    @abstractmethod
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the user message and generate a response.

        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history for context.

        Returns:
            AgentResult containing the response and metadata.
        """
        pass

    async def build_messages(
        self,
        message: str,
        history: list[LLMMessage],
    ) -> list[LLMMessage]:
        """Build the message list for LLM request.

        Args:
            message: Current user message.
            history: Previous messages in the conversation.

        Returns:
            List of LLMMessage objects for the request.
        """
        from nergal.llm import MessageRole

        messages = [LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt)]
        messages.extend(history)
        messages.append(LLMMessage(role=MessageRole.USER, content=message))
        return messages

    async def generate_response(
        self,
        message: str,
        history: list[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response using the LLM provider.

        Args:
            message: Current user message.
            history: Previous messages in the conversation.
            **kwargs: Additional parameters for the LLM.

        Returns:
            LLMResponse from the provider.
        """
        messages = await self.build_messages(message, history)
        return await self.llm_provider.generate(messages, **kwargs)


class AgentRegistry:
    """Registry for managing available agents."""

    def __init__(self) -> None:
        """Initialize the agent registry."""
        self._agents: dict[AgentType, BaseAgent] = {}
        self._type_handlers: list[Callable[[str, dict[str, Any]], AgentType]] = []

    def register(self, agent: BaseAgent) -> None:
        """Register an agent.

        Args:
            agent: Agent instance to register.
        """
        self._agents[agent.agent_type] = agent

    def get(self, agent_type: AgentType) -> BaseAgent | None:
        """Get an agent by type.

        Args:
            agent_type: Type of agent to retrieve.

        Returns:
            Agent instance or None if not found.
        """
        return self._agents.get(agent_type)

    def get_all(self) -> list[BaseAgent]:
        """Get all registered agents.

        Returns:
            List of all registered agents.
        """
        return list(self._agents.values())

    def add_type_handler(
        self,
        handler: Callable[[str, dict[str, Any]], AgentType],
    ) -> None:
        """Add a handler for determining agent type from message.

        Args:
            handler: Function that takes message and context,
                    returns appropriate AgentType.
        """
        self._type_handlers.append(handler)

    async def determine_agent(
        self,
        message: str,
        context: dict[str, Any],
    ) -> BaseAgent:
        """Determine the best agent for a message.

        First checks type handlers, then falls back to confidence-based selection.

        Args:
            message: User message to analyze.
            context: Current dialog context.

        Returns:
            The most suitable agent for the message.
        """
        # Check type handlers first
        for handler in self._type_handlers:
            try:
                agent_type = handler(message, context)
                if agent := self.get(agent_type):
                    return agent
            except Exception:
                continue

        # Fall back to confidence-based selection
        best_agent: BaseAgent | None = None
        best_confidence = 0.0

        for agent in self.get_all():
            try:
                confidence = await agent.can_handle(message, context)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_agent = agent
            except Exception:
                continue

        # Return best agent or default
        if best_agent:
            return best_agent

        if default := self.get(AgentType.DEFAULT):
            return default

        raise RuntimeError("No agents registered, including default")
