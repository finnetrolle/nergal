"""Tests for DialogManager class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nergal.dialog.manager import DialogManager, ProcessResult, PlanExecutionResult
from nergal.dialog.base import AgentType, ExecutionPlan, PlanStep, AgentResult
from nergal.dialog.styles import StyleType


class TestDialogManager:
    """Tests for DialogManager class."""
    
    def test_initialization(self, mock_llm_provider):
        """Test DialogManager initialization."""
        manager = DialogManager(
            llm_provider=mock_llm_provider,
            max_history=10,
            max_contexts=100,
            style_type=StyleType.DEFAULT,
            use_dispatcher=False,
        )
        
        assert manager.llm_provider == mock_llm_provider
        assert manager.context_manager is not None
        assert len(manager.agent_registry.get_all()) >= 1  # Default agent
    
    def test_initialization_with_dispatcher(self, mock_llm_provider):
        """Test DialogManager initialization with dispatcher enabled."""
        manager = DialogManager(
            llm_provider=mock_llm_provider,
            use_dispatcher=True,
        )
        
        assert manager._dispatcher is not None
    
    def test_register_agent(self, mock_llm_provider, mock_agent):
        """Test registering a custom agent."""
        manager = DialogManager(llm_provider=mock_llm_provider)
        initial_count = len(manager.agent_registry.get_all())
        
        manager.register_agent(mock_agent)
        
        assert len(manager.agent_registry.get_all()) == initial_count + 1
    
    def test_get_or_create_context(self, mock_llm_provider):
        """Test context creation and retrieval."""
        manager = DialogManager(llm_provider=mock_llm_provider)
        
        # Create new context
        context = manager.get_or_create_context(
            user_id=12345,
            first_name="Test",
            last_name="User",
        )
        
        assert context is not None
        assert context.user_info.user_id == 12345
        assert context.user_info.first_name == "Test"
        
        # Get existing context
        context2 = manager.get_or_create_context(user_id=12345)
        assert context2.user_info.first_name == "Test"
    
    @pytest.mark.asyncio
    async def test_process_message_simple(self, mock_llm_provider):
        """Test simple message processing without dispatcher."""
        manager = DialogManager(
            llm_provider=mock_llm_provider,
            use_dispatcher=False,
        )
        
        result = await manager.process_message(
            user_id=12345,
            message="Привет!",
            user_info={"first_name": "Test"},
        )
        
        assert isinstance(result, ProcessResult)
        assert result.response is not None
        assert result.agent_type == AgentType.DEFAULT
    
    @pytest.mark.asyncio
    async def test_process_message_with_context(self, mock_llm_provider):
        """Test message processing preserves context."""
        manager = DialogManager(
            llm_provider=mock_llm_provider,
            use_dispatcher=False,
        )
        
        # First message
        await manager.process_message(
            user_id=12345,
            message="Меня зовут Иван",
            user_info={"first_name": "Test"},
        )
        
        # Second message - context should be preserved
        context = manager.get_or_create_context(user_id=12345)
        assert len(context.messages) >= 2  # User + assistant messages
    
    def test_clear_user_context(self, mock_llm_provider):
        """Test clearing user context."""
        manager = DialogManager(llm_provider=mock_llm_provider)
        
        # Create context
        manager.get_or_create_context(user_id=12345)
        
        # Clear it
        result = manager.clear_user_context(12345)
        assert result is True
        
        # Try to clear non-existent
        result = manager.clear_user_context(99999)
        assert result is False
    
    def test_get_context_stats(self, mock_llm_provider):
        """Test getting context statistics."""
        manager = DialogManager(llm_provider=mock_llm_provider)
        
        # Create some contexts
        manager.get_or_create_context(user_id=1)
        manager.get_or_create_context(user_id=2)
        
        stats = manager.get_context_stats()
        
        assert "active_contexts" in stats
        assert "registered_agents" in stats
        assert "llm_provider" in stats
        assert stats["active_contexts"] == 2


class TestPlanExecutionResult:
    """Tests for PlanExecutionResult dataclass."""
    
    def test_success_result(self):
        """Test successful execution result."""
        result = PlanExecutionResult(
            success=True,
            final_response="Test response",
            executed_steps=[{"agent": "default", "status": "success"}],
        )
        
        assert result.success is True
        assert result.final_response == "Test response"
        assert len(result.executed_steps) == 1
        assert result.error is None
    
    def test_error_result(self):
        """Test failed execution result."""
        result = PlanExecutionResult(
            success=False,
            final_response="",
            error="Agent failed",
        )
        
        assert result.success is False
        assert result.error == "Agent failed"


class TestProcessResult:
    """Tests for ProcessResult dataclass."""
    
    def test_basic_result(self):
        """Test basic process result."""
        result = ProcessResult(
            response="Test response",
            agent_type=AgentType.DEFAULT,
            confidence=0.9,
            session_id="test-session",
            processing_time_ms=100.0,
            metadata={},
        )
        
        assert result.response == "Test response"
        assert result.agent_type == AgentType.DEFAULT
        assert result.confidence == 0.9
        assert result.processing_time_ms == 100.0
