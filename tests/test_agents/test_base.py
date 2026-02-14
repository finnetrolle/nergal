"""Tests for base agent functionality and registry."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from nergal.dialog.base import (
    AgentRegistry,
    AgentType,
    AgentCategory,
    BaseAgent,
    ExecutionPlan,
    PlanStep,
    AgentResult,
)
from nergal.dialog.agents.base_specialized import (
    BaseSpecializedAgent,
    ContextAwareAgent,
)
from nergal.dialog.constants import ANALYSIS_KEYWORDS, SUMMARY_KEYWORDS


class TestAgentType:
    """Tests for AgentType enum."""
    
    def test_agent_type_values(self):
        """Test that agent types have expected values."""
        assert AgentType.DEFAULT.value == "default"
        assert AgentType.WEB_SEARCH.value == "web_search"
        assert AgentType.NEWS.value == "news"
        assert AgentType.ANALYSIS.value == "analysis"
    
    def test_get_category_core(self):
        """Test category assignment for core agents."""
        assert AgentType.get_category(AgentType.DEFAULT) == AgentCategory.CORE
        assert AgentType.get_category(AgentType.DISPATCHER) == AgentCategory.CORE
    
    def test_get_category_information(self):
        """Test category assignment for information agents."""
        assert AgentType.get_category(AgentType.WEB_SEARCH) == AgentCategory.INFORMATION
        assert AgentType.get_category(AgentType.NEWS) == AgentCategory.INFORMATION
        assert AgentType.get_category(AgentType.TECH_DOCS) == AgentCategory.INFORMATION
    
    def test_get_category_processing(self):
        """Test category assignment for processing agents."""
        assert AgentType.get_category(AgentType.ANALYSIS) == AgentCategory.PROCESSING
        assert AgentType.get_category(AgentType.COMPARISON) == AgentCategory.PROCESSING
        assert AgentType.get_category(AgentType.SUMMARY) == AgentCategory.PROCESSING


class TestExecutionPlan:
    """Tests for ExecutionPlan dataclass."""
    
    def test_empty_plan(self):
        """Test creating an empty execution plan."""
        plan = ExecutionPlan(steps=[], reasoning="test")
        
        assert len(plan.steps) == 0
        assert plan.reasoning == "test"
        assert not plan.has_missing_agents()
    
    def test_plan_with_steps(self):
        """Test creating a plan with steps."""
        steps = [
            PlanStep(agent_type=AgentType.WEB_SEARCH, description="search"),
            PlanStep(agent_type=AgentType.DEFAULT, description="respond"),
        ]
        plan = ExecutionPlan(steps=steps, reasoning="test plan")
        
        assert len(plan.steps) == 2
        assert plan.get_agent_types() == [AgentType.WEB_SEARCH, AgentType.DEFAULT]
    
    def test_missing_agents(self):
        """Test missing agents tracking."""
        plan = ExecutionPlan(
            steps=[],
            reasoning="test",
            missing_agents=[AgentType.FACT_CHECK],
            missing_agents_reason={"fact_check": "verification needed"},
        )
        
        assert plan.has_missing_agents()
        assert AgentType.FACT_CHECK in plan.missing_agents


class TestAgentResult:
    """Tests for AgentResult dataclass."""
    
    def test_basic_result(self):
        """Test creating a basic agent result."""
        result = AgentResult(
            response="Test response",
            agent_type=AgentType.DEFAULT,
        )
        
        assert result.response == "Test response"
        assert result.agent_type == AgentType.DEFAULT
        assert result.confidence == 1.0
        assert result.metadata == {}
    
    def test_result_with_metadata(self):
        """Test creating a result with metadata."""
        result = AgentResult(
            response="Test",
            agent_type=AgentType.WEB_SEARCH,
            confidence=0.9,
            metadata={"sources": ["url1", "url2"]},
        )
        
        assert result.confidence == 0.9
        assert result.metadata["sources"] == ["url1", "url2"]


class TestAgentRegistry:
    """Tests for AgentRegistry class."""
    
    def test_empty_registry(self):
        """Test creating an empty registry."""
        registry = AgentRegistry()
        
        assert len(registry.get_all()) == 0
        assert registry.get(AgentType.DEFAULT) is None
    
    def test_register_agent(self, mock_agent: BaseAgent):
        """Test registering an agent."""
        registry = AgentRegistry()
        
        registry.register(mock_agent)
        
        assert registry.get(AgentType.DEFAULT) == mock_agent
        assert len(registry.get_all()) == 1
    
    def test_get_all_agents(self, mock_agent: BaseAgent):
        """Test getting all registered agents."""
        registry = AgentRegistry()
        
        # Register multiple agents
        agent1 = MagicMock(spec=BaseAgent, agent_type=AgentType.DEFAULT)
        agent2 = MagicMock(spec=BaseAgent, agent_type=AgentType.WEB_SEARCH)
        
        registry.register(agent1)
        registry.register(agent2)
        
        all_agents = registry.get_all()
        
        assert len(all_agents) == 2
        assert agent1 in all_agents
        assert agent2 in all_agents
    
    def test_overwrite_agent(self, mock_agent: BaseAgent):
        """Test that registering same type overwrites."""
        registry = AgentRegistry()
        
        agent1 = MagicMock(spec=BaseAgent, agent_type=AgentType.DEFAULT)
        agent1.name = "agent1"
        agent2 = MagicMock(spec=BaseAgent, agent_type=AgentType.DEFAULT)
        agent2.name = "agent2"
        
        registry.register(agent1)
        registry.register(agent2)
        
        assert len(registry.get_all()) == 1
        assert registry.get(AgentType.DEFAULT).name == "agent2"
    
    @pytest.mark.asyncio
    async def test_determine_agent_by_confidence(self, mock_llm_provider):
        """Test agent selection by confidence score."""
        registry = AgentRegistry()
        
        # Create agents with different confidence levels
        agent1 = MagicMock(spec=BaseAgent)
        agent1.agent_type = AgentType.DEFAULT
        agent1.can_handle = AsyncMock(return_value=0.5)
        
        agent2 = MagicMock(spec=BaseAgent)
        agent2.agent_type = AgentType.WEB_SEARCH
        agent2.can_handle = AsyncMock(return_value=0.9)
        
        registry.register(agent1)
        registry.register(agent2)
        
        selected = await registry.determine_agent("test message", {})
        
        assert selected.agent_type == AgentType.WEB_SEARCH


class TestBaseSpecializedAgent:
    """Tests for BaseSpecializedAgent class."""
    
    def test_keywords_configuration(self, mock_llm_provider):
        """Test that keywords are properly configured."""
        class TestAgent(BaseSpecializedAgent):
            _keywords = ["test", "keywords"]
            agent_type = AgentType.ANALYSIS
            system_prompt = "test"
        
        agent = TestAgent(mock_llm_provider)
        
        assert agent._keywords == ["test", "keywords"]
    
    @pytest.mark.asyncio
    async def test_can_handle_keyword_matching(self, mock_llm_provider):
        """Test can_handle with keyword matching."""
        class TestAgent(BaseSpecializedAgent):
            _keywords = ANALYSIS_KEYWORDS
            _base_confidence = 0.2
            _keyword_boost = 0.2
            agent_type = AgentType.ANALYSIS
            system_prompt = "test"
        
        agent = TestAgent(mock_llm_provider)
        
        # Message with analysis keywords
        confidence = await agent.can_handle("сравни эти два варианта", {})
        assert confidence > 0.2
        
        # Message without keywords
        confidence = await agent.can_handle("привет как дела", {})
        assert confidence == 0.2  # base confidence only
    
    @pytest.mark.asyncio
    async def test_can_handle_context_boost(self, mock_llm_provider):
        """Test can_handle with context boost."""
        class TestAgent(BaseSpecializedAgent):
            _context_keys = ["search_results"]
            _base_confidence = 0.2
            _context_boost = 0.3
            agent_type = AgentType.ANALYSIS
            system_prompt = "test"
        
        agent = TestAgent(mock_llm_provider)
        
        # Without context
        confidence_no_context = await agent.can_handle("test", {})
        
        # With relevant context
        confidence_with_context = await agent.can_handle(
            "test", {"search_results": "some data"}
        )
        
        assert confidence_with_context > confidence_no_context


class TestContextAwareAgent:
    """Tests for ContextAwareAgent class."""
    
    @pytest.mark.asyncio
    async def test_requires_context(self, mock_llm_provider):
        """Test that context-aware agent requires context."""
        class TestContextAgent(ContextAwareAgent):
            _required_context_keys = ["search_results"]
            agent_type = AgentType.SUMMARY
            system_prompt = "test"
        
        agent = TestContextAgent(mock_llm_provider)
        
        # Without required context
        confidence = await agent.can_handle("summarize this", {})
        assert confidence == 0.0
        
        # With required context
        confidence = await agent.can_handle(
            "summarize this", {"search_results": "data"}
        )
        assert confidence > 0.0
