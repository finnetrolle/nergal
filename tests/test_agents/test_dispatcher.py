"""Tests for DispatcherAgent functionality.

This module tests the dispatcher agent's ability to create
execution plans and route messages to appropriate agents.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from nergal.dialog.base import (
    AgentRegistry,
    AgentType,
    BaseAgent,
    ExecutionPlan,
    PlanStep,
)
from nergal.dialog.dispatcher_agent import DispatcherAgent, AGENT_DESCRIPTIONS
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMResponse, LLMMessage


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_provider() -> BaseLLMProvider:
    """Create a mock LLM provider for testing."""
    provider = MagicMock(spec=BaseLLMProvider)
    provider.provider_name = "mock-provider"
    
    # Default response with a simple plan
    default_plan = {
        "steps": [
            {"agent": "default", "description": "respond to greeting"}
        ],
        "reasoning": "simple greeting",
    }
    
    provider.generate = AsyncMock(return_value=LLMResponse(
        content=json.dumps(default_plan),
        model="test-model",
        usage={"total_tokens": 100},
        finish_reason="stop",
    ))
    return provider


@pytest.fixture
def agent_registry(mock_llm_provider: BaseLLMProvider) -> AgentRegistry:
    """Create an agent registry with mock agents."""
    registry = AgentRegistry()
    
    # Add mock default agent
    default_agent = MagicMock(spec=BaseAgent)
    default_agent.agent_type = AgentType.DEFAULT
    default_agent.can_handle = AsyncMock(return_value=0.8)
    default_agent.process = AsyncMock(return_value=MagicMock(
        response="Default response",
        agent_type=AgentType.DEFAULT,
        confidence=0.9,
    ))
    registry.register(default_agent)
    
    # Add mock web search agent
    web_search_agent = MagicMock(spec=BaseAgent)
    web_search_agent.agent_type = AgentType.WEB_SEARCH
    web_search_agent.can_handle = AsyncMock(return_value=0.7)
    registry.register(web_search_agent)
    
    return registry


@pytest.fixture
def dispatcher(mock_llm_provider: BaseLLMProvider, agent_registry: AgentRegistry) -> DispatcherAgent:
    """Create a dispatcher agent with registry configured."""
    dispatcher = DispatcherAgent(mock_llm_provider)
    dispatcher.set_agent_registry(agent_registry)
    return dispatcher


# =============================================================================
# Basic Tests
# =============================================================================

class TestDispatcherAgentBasics:
    """Basic tests for DispatcherAgent."""
    
    def test_agent_type(self, dispatcher: DispatcherAgent) -> None:
        """Test that dispatcher has correct agent type."""
        assert dispatcher.agent_type == AgentType.DISPATCHER
    
    def test_system_prompt_contains_agent_list(
        self, dispatcher: DispatcherAgent
    ) -> None:
        """Test that system prompt includes available agents."""
        prompt = dispatcher.system_prompt
        
        # Should mention default agent
        assert "default" in prompt.lower()
        # Should contain agent descriptions section
        assert "агенты" in prompt.lower() or "agents" in prompt.lower()
    
    def test_system_prompt_is_dynamic(
        self, mock_llm_provider: BaseLLMProvider, agent_registry: AgentRegistry
    ) -> None:
        """Test that system prompt changes based on registered agents."""
        dispatcher = DispatcherAgent(mock_llm_provider)
        dispatcher.set_agent_registry(agent_registry)
        
        prompt_with_agents = dispatcher.system_prompt
        
        # Create dispatcher without registry
        dispatcher_no_registry = DispatcherAgent(mock_llm_provider)
        prompt_without_registry = dispatcher_no_registry.system_prompt
        
        # Prompts should be different
        # (one has more agents listed than the other)
        assert prompt_with_agents != prompt_without_registry


# =============================================================================
# Plan Creation Tests
# =============================================================================

class TestPlanCreation:
    """Tests for execution plan creation."""
    
    @pytest.mark.asyncio
    async def test_create_plan_returns_execution_plan(
        self, dispatcher: DispatcherAgent
    ) -> None:
        """Test that create_plan returns an ExecutionPlan."""
        plan = await dispatcher.create_plan("hello", {})
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) > 0
        assert plan.reasoning
    
    @pytest.mark.asyncio
    async def test_create_plan_simple_greeting(
        self, mock_llm_provider: BaseLLMProvider, dispatcher: DispatcherAgent
    ) -> None:
        """Test plan creation for a simple greeting."""
        # Configure mock to return a simple plan
        simple_plan = {
            "steps": [
                {"agent": "default", "description": "respond to greeting"}
            ],
            "reasoning": "simple greeting, no search needed",
        }
        mock_llm_provider.generate = AsyncMock(return_value=LLMResponse(
            content=json.dumps(simple_plan),
            model="test-model",
            usage={"total_tokens": 50},
            finish_reason="stop",
        ))
        
        plan = await dispatcher.create_plan("Привет!", {})
        
        assert len(plan.steps) == 1
        assert plan.steps[0].agent_type == AgentType.DEFAULT
    
    @pytest.mark.asyncio
    async def test_create_plan_with_search(
        self, mock_llm_provider: BaseLLMProvider, dispatcher: DispatcherAgent
    ) -> None:
        """Test plan creation for a search query."""
        search_plan = {
            "steps": [
                {"agent": "web_search", "description": "find current weather"},
                {"agent": "default", "description": "formulate response"}
            ],
            "reasoning": "needs current information",
        }
        mock_llm_provider.generate = AsyncMock(return_value=LLMResponse(
            content=json.dumps(search_plan),
            model="test-model",
            usage={"total_tokens": 100},
            finish_reason="stop",
        ))
        
        plan = await dispatcher.create_plan("Какая погода в Москве?", {})
        
        assert len(plan.steps) == 2
        assert plan.steps[0].agent_type == AgentType.WEB_SEARCH
        assert plan.steps[1].agent_type == AgentType.DEFAULT
    
    @pytest.mark.asyncio
    async def test_create_plan_with_optional_step(
        self, mock_llm_provider: BaseLLMProvider, dispatcher: DispatcherAgent
    ) -> None:
        """Test plan creation with optional steps."""
        plan_with_optional = {
            "steps": [
                {"agent": "web_search", "description": "find information"},
                {"agent": "fact_check", "description": "verify facts", "is_optional": True},
                {"agent": "default", "description": "respond"}
            ],
            "reasoning": "search with optional fact check",
        }
        mock_llm_provider.generate = AsyncMock(return_value=LLMResponse(
            content=json.dumps(plan_with_optional),
            model="test-model",
            usage={"total_tokens": 100},
            finish_reason="stop",
        ))
        
        plan = await dispatcher.create_plan("Найди информацию", {})
        
        assert len(plan.steps) == 3
        # Fact check step should be optional
        fact_check_step = next(
            (s for s in plan.steps if s.agent_type == AgentType.FACT_CHECK), None
        )
        if fact_check_step:
            assert fact_check_step.is_optional
    
    @pytest.mark.asyncio
    async def test_create_plan_handles_malformed_json(
        self, mock_llm_provider: BaseLLMProvider, dispatcher: DispatcherAgent
    ) -> None:
        """Test that dispatcher handles malformed JSON response."""
        mock_llm_provider.generate = AsyncMock(return_value=LLMResponse(
            content="This is not valid JSON",
            model="test-model",
            usage={"total_tokens": 20},
            finish_reason="stop",
        ))
        
        # Should fall back to default agent
        plan = await dispatcher.create_plan("test message", {})
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) >= 1
        # Should have at least default agent as fallback
        assert any(s.agent_type == AgentType.DEFAULT for s in plan.steps)


# =============================================================================
# Available Agents Tests
# =============================================================================

class TestAvailableAgents:
    """Tests for dynamic agent discovery."""
    
    def test_get_available_agents_excludes_dispatcher(
        self, dispatcher: DispatcherAgent
    ) -> None:
        """Test that dispatcher excludes itself from available agents."""
        available = dispatcher._get_available_agents()
        
        assert AgentType.DISPATCHER not in available
    
    def test_get_available_agents_includes_default(
        self, dispatcher: DispatcherAgent
    ) -> None:
        """Test that default agent is always available."""
        available = dispatcher._get_available_agents()
        
        assert AgentType.DEFAULT in available
    
    def test_get_available_agents_with_registry(
        self, dispatcher: DispatcherAgent
    ) -> None:
        """Test that available agents match registry."""
        available = dispatcher._get_available_agents()
        
        # Should include default and web_search from our fixture
        assert AgentType.DEFAULT in available
        assert AgentType.WEB_SEARCH in available


# =============================================================================
# Agent Descriptions Tests
# =============================================================================

class TestAgentDescriptions:
    """Tests for agent descriptions used in prompts."""
    
    def test_all_agent_types_have_descriptions(self) -> None:
        """Test that all AgentType values have descriptions."""
        # Check that common agent types have descriptions
        expected_types = [
            AgentType.DEFAULT,
            AgentType.WEB_SEARCH,
            AgentType.NEWS,
            AgentType.COMPARISON,
            AgentType.FACT_CHECK,
            AgentType.ANALYSIS,
        ]
        
        for agent_type in expected_types:
            assert agent_type in AGENT_DESCRIPTIONS, f"Missing description for {agent_type}"
            assert len(AGENT_DESCRIPTIONS[agent_type]) > 0
    
    def test_descriptions_are_informative(self) -> None:
        """Test that descriptions are informative (not too short)."""
        for agent_type, description in AGENT_DESCRIPTIONS.items():
            # Descriptions should be at least 20 characters
            assert len(description) >= 20, f"Description too short for {agent_type}"


# =============================================================================
# Fallback Behavior Tests
# =============================================================================

class TestFallbackBehavior:
    """Tests for fallback behavior when things go wrong."""
    
    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(
        self, mock_llm_provider: BaseLLMProvider, dispatcher: DispatcherAgent
    ) -> None:
        """Test fallback when LLM raises an error."""
        mock_llm_provider.generate = AsyncMock(side_effect=Exception("LLM error"))
        
        plan = await dispatcher.create_plan("test message", {})
        
        # Should return a fallback plan with default agent
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) >= 1
        assert plan.steps[0].agent_type == AgentType.DEFAULT
    
    @pytest.mark.asyncio
    async def test_fallback_on_empty_response(
        self, mock_llm_provider: BaseLLMProvider, dispatcher: DispatcherAgent
    ) -> None:
        """Test fallback when LLM returns empty content."""
        mock_llm_provider.generate = AsyncMock(return_value=LLMResponse(
            content="",
            model="test-model",
            usage={"total_tokens": 0},
            finish_reason="stop",
        ))
        
        plan = await dispatcher.create_plan("test message", {})
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) >= 1


# =============================================================================
# Plan Validation Tests
# =============================================================================

class TestPlanValidation:
    """Tests for execution plan validation."""
    
    @pytest.mark.asyncio
    async def test_plan_steps_have_required_fields(
        self, mock_llm_provider: BaseLLMProvider, dispatcher: DispatcherAgent
    ) -> None:
        """Test that plan steps have all required fields."""
        valid_plan = {
            "steps": [
                {"agent": "web_search", "description": "search"},
                {"agent": "default", "description": "respond"}
            ],
            "reasoning": "test",
        }
        mock_llm_provider.generate = AsyncMock(return_value=LLMResponse(
            content=json.dumps(valid_plan),
            model="test-model",
            usage={"total_tokens": 50},
            finish_reason="stop",
        ))
        
        plan = await dispatcher.create_plan("test", {})
        
        for step in plan.steps:
            assert isinstance(step, PlanStep)
            assert step.agent_type is not None
            assert step.description is not None
    
    @pytest.mark.asyncio
    async def test_plan_with_missing_agents_tracking(
        self, mock_llm_provider: BaseLLMProvider, dispatcher: DispatcherAgent
    ) -> None:
        """Test that plan tracks missing agents."""
        plan_with_missing = {
            "steps": [
                {"agent": "default", "description": "respond"}
            ],
            "reasoning": "simplified plan",
            "missing_agents": ["fact_check"],
            "missing_agents_reason": {"fact_check": "would verify facts"}
        }
        mock_llm_provider.generate = AsyncMock(return_value=LLMResponse(
            content=json.dumps(plan_with_missing),
            model="test-model",
            usage={"total_tokens": 50},
            finish_reason="stop",
        ))
        
        plan = await dispatcher.create_plan("test", {})
        
        assert plan.has_missing_agents()
        assert AgentType.FACT_CHECK in plan.missing_agents
