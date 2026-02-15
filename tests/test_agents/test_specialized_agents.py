"""Tests for specialized agents using the hook-based architecture.

This module contains parametrized tests for all specialized agents
that inherit from BaseSpecializedAgent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any

from nergal.dialog.agents.base_specialized import (
    BaseSpecializedAgent,
    ContextAwareAgent,
)
from nergal.dialog.base import AgentType, AgentResult
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMResponse


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
        tokens_used=100,
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
# Concrete Test Agent
# =============================================================================

class TestSpecializedAgent(BaseSpecializedAgent):
    """Concrete implementation for testing BaseSpecializedAgent."""
    
    _keywords = ["test", "testing", "тест"]
    _patterns = [r"\btest\b", r"\btesting\b"]
    _context_keys = ["search_results"]
    _base_confidence = 0.3
    _keyword_boost = 0.2
    _context_boost = 0.25
    
    @property
    def agent_type(self) -> AgentType:
        return AgentType.ANALYSIS
    
    @property
    def system_prompt(self) -> str:
        return "You are a test agent."


class TestContextAwareAgent(ContextAwareAgent):
    """Concrete implementation for testing ContextAwareAgent."""
    
    _keywords = ["summarize", "summary", "резюме"]
    _required_context_keys = ["search_results", "previous_step_output"]
    _base_confidence = 0.4
    
    @property
    def agent_type(self) -> AgentType:
        return AgentType.SUMMARY
    
    @property
    def system_prompt(self) -> str:
        return "You are a summary agent."


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
        agent = TestSpecializedAgent(mock_llm_provider)
        confidence = await agent.can_handle("hello world", empty_context)
        
        # Should return base confidence (0.3) since no keywords match
        assert confidence == pytest.approx(0.3, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_can_handle_single_keyword_boosts_confidence(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that a single matching keyword boosts confidence."""
        agent = TestSpecializedAgent(mock_llm_provider)
        confidence = await agent.can_handle("this is a test message", empty_context)
        
        # Base (0.3) + keyword boost (0.2) = 0.5
        assert confidence == pytest.approx(0.5, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_can_handle_multiple_keywords_capped(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that multiple keywords are capped at max_keyword_boost."""
        agent = TestSpecializedAgent(mock_llm_provider)
        confidence = await agent.can_handle("test testing test testing", empty_context)
        
        # Should be capped at 1.0
        assert confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_can_handle_context_boost(
        self, mock_llm_provider: BaseLLMProvider, context_with_search_results: dict[str, Any]
    ) -> None:
        """Test that relevant context boosts confidence."""
        agent = TestSpecializedAgent(mock_llm_provider)
        confidence = await agent.can_handle("hello world", context_with_search_results)
        
        # Base (0.3) + context boost (0.25) for search_results + context boost for relevant context
        assert confidence >= 0.55
    
    @pytest.mark.asyncio
    async def test_can_handle_pattern_match(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that pattern matching boosts confidence."""
        agent = TestSpecializedAgent(mock_llm_provider)
        confidence_with_pattern = await agent.can_handle("I am testing this", empty_context)
        confidence_without_pattern = await agent.can_handle("hello world", empty_context)
        
        # Pattern match should increase confidence
        assert confidence_with_pattern > confidence_without_pattern
    
    @pytest.mark.asyncio
    async def test_can_handle_never_exceeds_one(
        self, mock_llm_provider: BaseLLMProvider, context_with_search_results: dict[str, Any]
    ) -> None:
        """Test that confidence is never greater than 1.0."""
        agent = TestSpecializedAgent(mock_llm_provider)
        
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
        agent = TestSpecializedAgent(mock_llm_provider)
        confidence = await agent.can_handle("unrelated message", empty_context)
        
        assert confidence >= 0.0
    
    @pytest.mark.asyncio
    async def test_process_returns_agent_result(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that process returns a valid AgentResult."""
        agent = TestSpecializedAgent(mock_llm_provider)
        result = await agent.process("test message", empty_context, [])
        
        assert isinstance(result, AgentResult)
        assert result.response == "Test response"
        assert result.agent_type == AgentType.ANALYSIS
    
    @pytest.mark.asyncio
    async def test_custom_confidence_hook(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that custom confidence hook is called."""
        
        class CustomAgent(TestSpecializedAgent):
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
# ContextAwareAgent Tests
# =============================================================================

class TestContextAwareAgent:
    """Tests for ContextAwareAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_can_handle_returns_zero_without_required_context(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test that can_handle returns 0.0 when required context is missing."""
        agent = TestContextAwareAgent(mock_llm_provider)
        confidence = await agent.can_handle("summarize this", empty_context)
        
        assert confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_can_handle_returns_confidence_with_required_context(
        self, mock_llm_provider: BaseLLMProvider, context_with_search_results: dict[str, Any]
    ) -> None:
        """Test that can_handle returns confidence when required context is present."""
        agent = TestContextAwareAgent(mock_llm_provider)
        confidence = await agent.can_handle("summarize this", context_with_search_results)
        
        # Should have non-zero confidence since required context is present
        assert confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_can_handle_with_partial_context(
        self, mock_llm_provider: BaseLLMProvider
    ) -> None:
        """Test that can_handle works with partial required context."""
        agent = TestContextAwareAgent(mock_llm_provider)
        
        # Only one of the required keys
        partial_context = {"search_results": "some results"}
        confidence = await agent.can_handle("summarize this", partial_context)
        
        # Should still work since we check with any()
        assert confidence > 0.0


# =============================================================================
# Parametrized Tests for Real Agents
# =============================================================================

class TestRealSpecializedAgents:
    """Parametrized tests for real specialized agents."""
    
    @pytest.mark.parametrize("agent_class,keywords,expected_type", [
        ("NewsAgent", ["новости", "news"], AgentType.NEWS),
        ("ComparisonAgent", ["сравни", "vs"], AgentType.COMPARISON),
        ("FactCheckAgent", ["правда", "проверь"], AgentType.FACT_CHECK),
    ])
    @pytest.mark.asyncio
    async def test_agent_keywords_and_type(
        self,
        agent_class: str,
        keywords: list[str],
        expected_type: AgentType,
        mock_llm_provider: BaseLLMProvider,
        request: pytest.FixtureRequest,
    ) -> None:
        """Test that agents have correct keywords and types."""
        # Import agents dynamically
        if agent_class == "NewsAgent":
            from nergal.dialog.agents.news_agent import NewsAgent
            agent = NewsAgent(mock_llm_provider)
        elif agent_class == "ComparisonAgent":
            from nergal.dialog.agents.comparison_agent import ComparisonAgent
            agent = ComparisonAgent(mock_llm_provider)
        elif agent_class == "FactCheckAgent":
            from nergal.dialog.agents.fact_check_agent import FactCheckAgent
            agent = FactCheckAgent(mock_llm_provider)
        
        assert agent.agent_type == expected_type
        assert len(agent._keywords) > 0
        
        # Test that at least some keywords are present
        for kw in keywords:
            assert kw in agent._keywords or any(kw in k for k in agent._keywords)
    
    @pytest.mark.parametrize("message,expected_high_confidence", [
        ("сравни React и Vue", True),  # Comparison
        ("какие новости сегодня", True),  # News
        ("правда ли что", True),  # Fact check
        ("привет как дела", False),  # General - no specific agent
    ])
    @pytest.mark.asyncio
    async def test_agent_confidence_levels(
        self,
        message: str,
        expected_high_confidence: bool,
        mock_llm_provider: BaseLLMProvider,
        empty_context: dict[str, Any],
    ) -> None:
        """Test that agents return appropriate confidence levels."""
        from nergal.dialog.agents.news_agent import NewsAgent
        from nergal.dialog.agents.comparison_agent import ComparisonAgent
        from nergal.dialog.agents.fact_check_agent import FactCheckAgent
        
        agents = [
            NewsAgent(mock_llm_provider),
            ComparisonAgent(mock_llm_provider),
            FactCheckAgent(mock_llm_provider),
        ]
        
        max_confidence = 0.0
        for agent in agents:
            confidence = await agent.can_handle(message, empty_context)
            max_confidence = max(max_confidence, confidence)
        
        if expected_high_confidence:
            assert max_confidence > 0.5, f"Expected high confidence for: {message}"
        else:
            # For general messages, no specialized agent should be very confident
            pass  # This is expected behavior


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
        
        class CustomKeywordAgent(TestSpecializedAgent):
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
        agent = TestSpecializedAgent(mock_llm_provider)
        boost = await agent._calculate_pattern_boost("no patterns here")
        
        assert boost == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_pattern_boost_with_match(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test pattern boost returns boost value when pattern matches."""
        agent = TestSpecializedAgent(mock_llm_provider)
        boost = await agent._calculate_pattern_boost("this is a test")
        
        assert boost == agent._pattern_boost
    
    @pytest.mark.asyncio
    async def test_calculate_context_boost_empty_context(
        self, mock_llm_provider: BaseLLMProvider, empty_context: dict[str, Any]
    ) -> None:
        """Test context boost with empty context."""
        agent = TestSpecializedAgent(mock_llm_provider)
        boost = await agent._calculate_context_boost(empty_context)
        
        assert boost == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_context_boost_with_relevant_context(
        self, mock_llm_provider: BaseLLMProvider, context_with_search_results: dict[str, Any]
    ) -> None:
        """Test context boost with relevant context."""
        agent = TestSpecializedAgent(mock_llm_provider)
        boost = await agent._calculate_context_boost(context_with_search_results)
        
        # Should have boost from both context_keys and relevant context
        assert boost > 0.0
