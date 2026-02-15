"""Base class for specialized agents with common functionality.

This module provides a base class for specialized agents that includes
common patterns like keyword-based message handling and context analysis.
"""

from abc import abstractmethod
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage


class BaseSpecializedAgent(BaseAgent):
    """Base class for specialized agents with keyword-based can_handle.
    
    This class provides a standardized way for agents to determine if they
    can handle a message based on keywords and context. Subclasses can
    customize the behavior by setting class attributes or overriding methods.
    
    Attributes:
        _keywords: List of keywords that indicate this agent should handle the message.
        _context_keys: Context keys that boost confidence when present.
        _base_confidence: Starting confidence value.
        _keyword_boost: Confidence increase per matched keyword.
        _context_boost: Confidence increase when context keys are present.
        _max_keyword_boost: Maximum confidence boost from keywords.
    
    Example:
        class NewsAgent(BaseSpecializedAgent):
            _keywords = ["новости", "news", "пресса"]
            _context_keys = ["search_results"]
            
            @property
            def agent_type(self) -> AgentType:
                return AgentType.NEWS
            
            @property
            def system_prompt(self) -> str:
                return "Ты — агент для агрегации новостей..."
    """

    # Subclasses should override these
    _keywords: list[str] = []
    _context_keys: list[str] = []
    
    # Confidence parameters (can be overridden)
    _base_confidence: float = 0.2
    _keyword_boost: float = 0.15
    _context_boost: float = 0.25
    _max_keyword_boost: float = 0.5

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        """Initialize the specialized agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use.
        """
        super().__init__(llm_provider, style_type)

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine confidence based on keywords and context.
        
        Uses configurable keyword matching and context analysis.
        Subclasses can override for custom logic.
        
        Args:
            message: User message to analyze.
            context: Current dialog context with accumulated data.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        confidence = self._base_confidence
        message_lower = message.lower()
        
        # Keyword matching with boost
        matched_keywords = sum(1 for kw in self._keywords if kw in message_lower)
        keyword_boost = min(matched_keywords * self._keyword_boost, self._max_keyword_boost)
        confidence += keyword_boost
        
        # Context-based boost
        for key in self._context_keys:
            if key in context:
                confidence += self._context_boost
                break
        
        # Check for accumulated context from previous agents
        if self._has_relevant_context(context):
            confidence += self._context_boost
        
        return min(confidence, 1.0)

    def _has_relevant_context(self, context: dict[str, Any]) -> bool:
        """Check if context contains relevant data for this agent.
        
        Subclasses can override to check for specific context data.
        
        Args:
            context: Current dialog context.
            
        Returns:
            True if context contains relevant data.
        """
        # Default implementation checks for common context keys
        relevant_keys = ["search_results", "previous_step_output", "previous_agent"]
        return any(key in context for key in relevant_keys)

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

    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the user message and generate a response.
        
        This implementation provides a standard pattern for specialized agents.
        Subclasses can override for custom processing logic.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history for context.
            
        Returns:
            AgentResult containing the response and metadata.
        """
        # Build messages with context
        messages = await self._build_messages_with_context(message, context, history)
        
        # Generate response
        response = await self.llm_provider.generate(messages)
        
        # Calculate total tokens from usage
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )
        
        return AgentResult(
            response=response.content,
            agent_type=self.agent_type,
            confidence=1.0,
            metadata={
                "usage": response.usage,
                "model": response.model,
            },
            tokens_used=tokens_used,
        )

    async def _build_messages_with_context(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> list[LLMMessage]:
        """Build message list including context information.
        
        Args:
            message: Current user message.
            context: Dialog context with accumulated data.
            history: Previous messages in conversation.
            
        Returns:
            List of LLMMessage objects for the request.
        """
        from nergal.llm import MessageRole
        
        messages = [LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt)]
        
        # Add context information if available
        context_content = self._format_context_for_prompt(context)
        if context_content:
            messages.append(LLMMessage(
                role=MessageRole.SYSTEM,
                content=f"Контекст из предыдущих шагов:\n{context_content}"
            ))
        
        messages.extend(history)
        messages.append(LLMMessage(role=MessageRole.USER, content=message))
        
        return messages

    def _format_context_for_prompt(self, context: dict[str, Any]) -> str | None:
        """Format context data for inclusion in prompt.
        
        Subclasses can override to customize context formatting.
        
        Args:
            context: Dialog context dictionary.
            
        Returns:
            Formatted context string or None if no relevant context.
        """
        parts = []
        
        if "search_results" in context:
            search_results = context["search_results"]
            if isinstance(search_results, str) and search_results.strip():
                # Truncate very long search results
                preview = search_results[:2000] + "..." if len(search_results) > 2000 else search_results
                parts.append(f"Результаты поиска:\n{preview}")
        
        if "previous_step_output" in context:
            prev_output = context["previous_step_output"]
            if isinstance(prev_output, str) and prev_output.strip():
                parts.append(f"Результат предыдущего шага:\n{prev_output[:1000]}")
        
        return "\n\n".join(parts) if parts else None


class ContextAwareAgent(BaseSpecializedAgent):
    """Agent that requires specific context to function.
    
    This class is for agents that only make sense when there's
    accumulated context from previous agent executions.
    
    Example:
        class SummaryAgent(ContextAwareAgent):
            # Only activates when there's content to summarize
            _required_context_keys = ["search_results", "previous_step_output"]
    """
    
    # Subclasses should set keys that must be present
    _required_context_keys: list[str] = []
    
    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Only handle if required context is present.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            High confidence if context is present, low otherwise.
        """
        # Check if required context is present
        has_required_context = any(
            key in context for key in self._required_context_keys
        )
        
        if not has_required_context:
            return 0.0
        
        # Use parent logic for confidence calculation
        return await super().can_handle(message, context)
