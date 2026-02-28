"""Tests for DialogManager class."""

import pytest

from nergal.dialog.manager import DialogManager, ProcessResult
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
        )

        assert manager.llm_provider == mock_llm_provider
        assert manager.context_manager is not None

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
        """Test simple message processing."""
        manager = DialogManager(llm_provider=mock_llm_provider)

        result = await manager.process_message(
            user_id=12345,
            message="Привет!",
            user_info={"first_name": "Test"},
        )

        assert isinstance(result, ProcessResult)
        assert result.response is not None

    @pytest.mark.asyncio
    async def test_process_message_with_context(self, mock_llm_provider):
        """Test message processing preserves context."""
        manager = DialogManager(llm_provider=mock_llm_provider)

        # First message
        await manager.process_message(
            user_id=12345,
            message="Меня зовут Иван",
            user_info={"first_name": "Test"},
        )

        # Second message - context should be preserved
        context = manager.get_or_create_context(user_id=12345)
        assert len(context.history) >= 2  # User + assistant messages

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
        assert "llm_provider" in stats
        assert stats["active_contexts"] == 2


class TestProcessResult:
    """Tests for ProcessResult dataclass."""

    def test_basic_result(self):
        """Test basic process result."""
        result = ProcessResult(
            response="Test response",
            processing_time_ms=100.0,
            metadata={},
        )

        assert result.response == "Test response"
        assert result.processing_time_ms == 100.0
