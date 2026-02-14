"""Agent system for handling different types of user requests.

This module provides a base class for agents and a registry for managing them.
Agents are responsible for handling specific types of user requests.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from nergal.dialog.styles import StyleType, get_style_prompt
from nergal.llm import BaseLLMProvider, LLMMessage, LLMResponse


class AgentType(str, Enum):
    """Types of agents available in the system."""

    DEFAULT = "default"
    FAQ = "faq"
    SMALL_TALK = "small_talk"
    TASK = "task"
    UNKNOWN = "unknown"


@dataclass
class AgentResult:
    """Result of agent processing."""

    response: str
    agent_type: AgentType
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    should_handoff: bool = False
    handoff_agent: AgentType | None = None


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


class DefaultAgent(BaseAgent):
    """Default agent for handling general requests."""

    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.DEFAULT

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent based on the configured style."""
        return get_style_prompt(self._style_type)

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Default agent can handle any message with low confidence."""
        return 0.1

    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message using default behavior."""
        response = await self.generate_response(message, history)
        return AgentResult(
            response=response.content,
            agent_type=self.agent_type,
            confidence=0.1,
            metadata={"model": response.model, "usage": response.usage},
        )


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
