"""Base class for specialized agents with common functionality.

This module provides a base class for specialized agents that includes
common patterns like keyword-based message handling and context analysis.

The architecture uses the Template Method pattern with hook methods that
subclasses can override for custom behavior without duplicating logic.
"""

import re
from abc import abstractmethod
from functools import lru_cache
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage


class BaseSpecializedAgent(BaseAgent):
    """Base class for specialized agents with hook-based can_handle.
    
    This class uses the Template Method pattern to provide a standardized
    way for agents to determine confidence. Subclasses can customize behavior
    by:
    
    1. Setting class attributes (_keywords, _context_keys, etc.)
    2. Overriding hook methods (_calculate_custom_confidence, etc.)
    3. Completely overriding can_handle() only when necessary
    
    Architecture Pattern:
        can_handle() is the template method that calls:
        - _calculate_keyword_boost()      # Override for custom keyword logic
        - _calculate_context_boost()      # Override for custom context logic
        - _calculate_custom_confidence()  # Hook for agent-specific logic
    
    Attributes:
        _keywords: List of keywords that indicate this agent should handle the message.
        _patterns: List of regex patterns for more complex matching.
        _context_keys: Context keys that boost confidence when present.
        _base_confidence: Starting confidence value.
        _keyword_boost: Confidence increase per matched keyword.
        _context_boost: Confidence increase when context keys are present.
        _max_keyword_boost: Maximum confidence boost from keywords.
        _pattern_boost: Confidence boost when a pattern matches.
    
    Example:
        class NewsAgent(BaseSpecializedAgent):
            _keywords = ["новости", "news", "пресса"]
            _context_keys = ["search_results"]
            _patterns = [r"что пишут", r"what.*write"]
            
            @property
            def agent_type(self) -> AgentType:
                return AgentType.NEWS
            
            @property
            def system_prompt(self) -> str:
                return "Ты — агент для агрегации новостей..."
            
            async def _calculate_custom_confidence(
                self, message: str, context: dict[str, Any]
            ) -> float:
                # Hook: Extra confidence for multiple sources
                if context.get("sources_count", 0) >= 3:
                    return 0.2
                return 0.0
    """

    # Subclasses should override these
    _keywords: list[str] = []
    _patterns: list[str] = []  # Regex patterns for complex matching
    _context_keys: list[str] = []
    
    # Confidence parameters (can be overridden)
    _base_confidence: float = 0.2
    _keyword_boost: float = 0.15
    _context_boost: float = 0.25
    _max_keyword_boost: float = 0.5
    _pattern_boost: float = 0.3

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
        # Compile patterns for efficiency
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self._patterns
        ]

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine confidence using Template Method pattern.
        
        This is the template method that orchestrates confidence calculation.
        Subclasses should prefer overriding hook methods over this method.
        
        Args:
            message: User message to analyze.
            context: Current dialog context with accumulated data.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        confidence = self._base_confidence
        message_lower = message.lower()
        
        # 1. Keyword-based boost
        confidence += await self._calculate_keyword_boost(message_lower)
        
        # 2. Pattern-based boost (for complex matching)
        confidence += await self._calculate_pattern_boost(message)
        
        # 3. Context-based boost
        confidence += await self._calculate_context_boost(context)
        
        # 4. Hook for agent-specific logic
        confidence += await self._calculate_custom_confidence(message, context)
        
        return min(max(confidence, 0.0), 1.0)

    async def _calculate_keyword_boost(self, message_lower: str) -> float:
        """Calculate confidence boost from keyword matches.
        
        Subclasses can override for custom keyword matching logic
        (e.g., weighted keywords, phrase matching).
        
        Args:
            message_lower: Lowercase message for matching.
            
        Returns:
            Confidence boost (0.0 to _max_keyword_boost).
        """
        matched_keywords = sum(1 for kw in self._keywords if kw in message_lower)
        return min(matched_keywords * self._keyword_boost, self._max_keyword_boost)

    async def _calculate_pattern_boost(self, message: str) -> float:
        """Calculate confidence boost from regex pattern matches.
        
        Subclasses can override for custom pattern matching logic.
        
        Args:
            message: Original message for pattern matching.
            
        Returns:
            Confidence boost (0.0 or _pattern_boost).
        """
        for pattern in self._compiled_patterns:
            if pattern.search(message):
                return self._pattern_boost
        return 0.0

    async def _calculate_context_boost(self, context: dict[str, Any]) -> float:
        """Calculate confidence boost from context presence.
        
        Subclasses can override for custom context analysis.
        
        Args:
            context: Current dialog context.
            
        Returns:
            Confidence boost.
        """
        boost = 0.0
        
        # Check configured context keys
        for key in self._context_keys:
            if key in context:
                boost += self._context_boost
                break
        
        # Check for accumulated context from previous agents
        if self._has_relevant_context(context):
            boost += self._context_boost
        
        return boost

    async def _calculate_custom_confidence(
        self, message: str, context: dict[str, Any]
    ) -> float:
        """Hook method for agent-specific confidence calculation.
        
        Override this method to add custom logic without duplicating
        the base keyword/context matching.
        
        Common use cases:
        - Check for specific context values (e.g., sources_count >= 3)
        - Apply domain-specific heuristics
        - Combine multiple signals
        
        Args:
            message: Original user message.
            context: Current dialog context.
            
        Returns:
            Additional confidence (can be negative to reduce confidence).
        """
        return 0.0

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
