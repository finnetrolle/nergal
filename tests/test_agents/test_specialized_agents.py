"""Tests for specialized agents using the hook-based architecture.

This module contains parametrized tests for all specialized agents
that inherit from BaseSpecializedAgent.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lib import BaseLLMProvider, LLMResponse
from nergal.dialog.agents.base_specialized import BaseSpecializedAgent
from nergal.dialog.base import AgentResult, AgentType

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_provider() -> BaseLLMProvider:
    """Create a mock LLM provider for testing."""
    provider = MagicMock(spec=BaseLLMProvider)
    provider.provider_name = "mock-provider"
    provider.generate = AsyncMock(return_value=LLMResponse(
        content="Test response",
        model="test-model",
        usage={"total_tokens": 100},
        finish_reason="stop",
    ))
    return provider


@pytest.fixture
def empty_context() -> dict[str, Any]:
    """Create an empty dialog context."""
    return {}


@pytest.fixture
def context_with_search_results() -> dict[str, Any]:
    """Create a context with search results."""
    return {
        "search_results": "Test search result content",
        "sources": ["https://example.com"],
        "previous_step_output": "Previous agent output",
    }


# =============================================================================
# Concrete Test Agent (named to avoid pytest collection)
# =============================================================================

class MockSpecializedAgent(BaseSpecializedAgent):
    """Concrete implementation for testing BaseSpecializedAgent."""
    
    _keywords = ["test", "testing", "тест"]
    _patterns = [r"\btest\b", r"\btesting\b"]
    _context_keys = ["search_results"]
    _base_confidence = 0.3
    _keyword_boost = 0.2
    _context_boost = 0.25
    
    @property
    def agent_type(self) -> AgentType:
        return AgentType.WEB_SEARCH
    
    @property
    def system_prompt(self) -> str:
        return "You are a test agent."


# =============================================================================
# BaseSpecializedAgent Tests
# =============================================================================

class TestBaseSpecializedAgent:
    """Tests for BaseSpecializedAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_can_handle_no_keywords_returns_base_confidence(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that can_handle returns base confidence when no keywords match."""
        agent = MockSpecializedAgent(mock_llm_provider)
        confidence = await agent.can_handle("hello world", empty_context)
        
        # Should return base confidence (0.3) since no keywords match
        assert confidence == pytest.approx(0.3, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_can_handle_single_keyword_boosts_confidence(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that a single matching keyword boosts confidence."""
        agent = MockSpecializedAgent(mock_llm_provider)
        confidence = await agent.can_handle("this is a test message", empty_context)
        
        # Base (0.3) + keyword boost (0.2) + pattern boost (0.3) = 0.8
        # Note: "test" matches both keyword and pattern
        assert confidence == pytest.approx(0.8, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_can_handle_multiple_keywords_capped(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that multiple keywords are capped at max_keyword_boost."""
        agent = MockSpecializedAgent(mock_llm_provider)
        confidence = await agent.can_handle("test testing test testing", empty_context)
        
        # Should be capped at 1.0
        assert confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_can_handle_context_boost(
        self, mock_llm_provider: BaseLLMProvider, context_with_search_results: dict[str, Any]
    ) -> None:
        """Test that relevant context boosts confidence."""
        agent = MockSpecializedAgent(mock_llm_provider)
        confidence = await agent.can_handle("hello world", context_with_search_results)
        
        # Base (0.3) + context boost (0.25) for search_results + context boost for relevant context
        assert confidence >= 0.55
    
    @pytest.mark.asyncio
    async def test_can_handle_pattern_match(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that pattern matching boosts confidence."""
        agent = MockSpecializedAgent(mock_llm_provider)
        confidence_with_pattern = await agent.can_handle("I am testing this", empty_context)
        confidence_without_pattern = await agent.can_handle("hello world", empty_context)
        
        # Pattern match should increase confidence
        assert confidence_with_pattern > confidence_without_pattern
    
    @pytest.mark.asyncio
    async def test_can_handle_never_exceeds_one(
        self, mock_llm_provider: BaseLLMProvider, context_with_search_results: dict[str, Any]
    ) -> None:
        """Test that confidence is never greater than 1.0."""
        agent = MockSpecializedAgent(mock_llm_provider)
        
        # Message with all keywords and context
        confidence = await agent.can_handle(
            "test testing test testing test",
            context_with_search_results
        )
        
        assert confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_can_handle_never_below_zero(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that confidence is never less than 0.0."""
        agent = MockSpecializedAgent(mock_llm_provider)
        confidence = await agent.can_handle("unrelated message", empty_context)
        
        assert confidence >= 0.0
    
    @pytest.mark.asyncio
    async def test_process_returns_agent_result(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that process returns a valid AgentResult."""
        agent = MockSpecializedAgent(mock_llm_provider)
        result = await agent.process("test message", empty_context, [])
        
        assert isinstance(result, AgentResult)
        assert result.response == "Test response"
        assert result.agent_type == AgentType.WEB_SEARCH
    
    @pytest.mark.asyncio
    async def test_custom_confidence_hook(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that custom confidence hook is called."""
        
        class CustomAgent(MockSpecializedAgent):
            async def _calculate_custom_confidence(
                self, message: str, context: dict[str, Any]
            ) -> float:
                if "special" in message.lower():
                    return 0.5
                return 0.0
        
        agent = CustomAgent(mock_llm_provider)
        
        confidence_normal = await agent.can_handle("test message", empty_context)
        confidence_special = await agent.can_handle("special test message", empty_context)
        
        assert confidence_special > confidence_normal


# =============================================================================
# Hook Method Tests
# =============================================================================

class TestHookMethods:
    """Tests for hook method functionality."""
    
    @pytest.mark.asyncio
    async def test_calculate_keyword_boost_override(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that _calculate_keyword_boost can be overridden."""
        
        class CustomKeywordAgent(MockSpecializedAgent):
            async def _calculate_keyword_boost(self, message_lower: str) -> float:
                # Custom: double the boost
                matched = sum(1 for kw in self._keywords if kw in message_lower)
                return min(matched * self._keyword_boost * 2, self._max_keyword_boost)
        
        agent = CustomKeywordAgent(mock_llm_provider)
        confidence = await agent.can_handle("test message", empty_context)
        
        # Should have higher confidence due to doubled boost
        assert confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_calculate_pattern_boost_no_match(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test pattern boost returns 0 when no patterns match."""
        agent = MockSpecializedAgent(mock_llm_provider)
        boost = await agent._calculate_pattern_boost("no patterns here")
        
        assert boost == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_pattern_boost_with_match(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test pattern boost returns boost value when pattern matches."""
        agent = MockSpecializedAgent(mock_llm_provider)
        boost = await agent._calculate_pattern_boost("this is a test")
        
        assert boost == agent._pattern_boost
    
    @pytest.mark.asyncio
    async def test_calculate_context_boost_empty_context(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test context boost with empty context."""
        agent = MockSpecializedAgent(mock_llm_provider)
        boost = await agent._calculate_context_boost(empty_context)
        
        assert boost == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_context_boost_with_relevant_context(
        self, mock_llm_provider: BaseLLMProvider, context_with_search_results: dict[str, Any]
    ) -> None:
        """Test context boost with relevant context."""
        agent = MockSpecializedAgent(mock_llm_provider)
        boost = await agent._calculate_context_boost(context_with_search_results)
        
        # Should have boost from both context_keys and relevant context
        assert boost > 0.0
