"""Tests for cancellation and executor modules."""

import asyncio

import pytest

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.cancellation import (
    AgentCancelledError,
    CancellationToken,
    CancellationTokenSource,
    CancellationStats,
    AgentTimeoutError,
)
from nergal.dialog.executor import (
    AgentExecutor,
    ExecutionResult,
    TimeoutSettings,
)
from nergal.llm import BaseLLMProvider, LLMMessage
from nergal.dialog.styles import StyleType


# ============= CancellationToken Tests =============


class TestCancellationToken:
    """Tests for CancellationToken class."""

    def test_token_not_cancelled_by_default(self) -> None:
        """Test that token is not cancelled by default."""
        token = CancellationToken()
        assert not token.is_cancelled

    def test_cancel_sets_flag(self) -> None:
        """Test that cancel() sets the cancelled flag."""
        token = CancellationToken()
        token.cancel()
        assert token.is_cancelled

    def test_cancel_with_reason(self) -> None:
        """Test cancellation with a reason."""
        token = CancellationToken()
        token.cancel("User requested")

        assert token.is_cancelled
        assert token.cancel_reason == "User requested"

    def test_cancelled_at_timestamp(self) -> None:
        """Test that cancelled_at is set on cancellation."""
        token = CancellationToken()
        token.cancel()

        assert token.cancelled_at is not None

    def test_check_cancelled_raises_when_cancelled(self) -> None:
        """Test that check_cancelled raises when cancelled."""
        token = CancellationToken()
        token.cancel("Test cancellation")

        with pytest.raises(AgentCancelledError) as exc_info:
            token.check_cancelled()

        assert "Test cancellation" in str(exc_info.value)

    def test_check_cancelled_no_raise_when_active(self) -> None:
        """Test that check_cancelled doesn't raise when active."""
        token = CancellationToken()
        # Should not raise
        token.check_cancelled()

    def test_reset_clears_cancellation(self) -> None:
        """Test that reset clears the cancellation state."""
        token = CancellationToken()
        token.cancel("Test")
        token.reset()

        assert not token.is_cancelled
        assert token.cancel_reason is None
        assert token.cancelled_at is None

    def test_repr(self) -> None:
        """Test string representation."""
        active_token = CancellationToken()
        cancelled_token = CancellationToken()
        cancelled_token.cancel("Test")

        assert "active" in repr(active_token)
        assert "cancelled" in repr(cancelled_token)
        assert "Test" in repr(cancelled_token)


class TestCancellationTokenSource:
    """Tests for CancellationTokenSource class."""

    def test_source_provides_token(self) -> None:
        """Test that source provides a token."""
        source = CancellationTokenSource()
        assert source.token is not None
        assert isinstance(source.token, CancellationToken)

    def test_cancel_cancels_token(self) -> None:
        """Test that source.cancel() cancels the token."""
        source = CancellationTokenSource()
        source.cancel("Test reason")

        assert source.is_cancelled
        assert source.token.is_cancelled
        assert source.token.cancel_reason == "Test reason"

    def test_link_cancels_linked_token(self) -> None:
        """Test that linked tokens are cancelled with source."""
        source = CancellationTokenSource()
        linked_token = CancellationToken()

        source.link(linked_token)
        source.cancel("Source cancelled")

        assert linked_token.is_cancelled
        assert linked_token.cancel_reason == "Source cancelled"

    def test_link_already_cancelled_source(self) -> None:
        """Test linking to an already cancelled source."""
        source = CancellationTokenSource()
        source.cancel("Already cancelled")

        new_token = CancellationToken()
        source.link(new_token)

        assert new_token.is_cancelled

    def test_reset_clears_all(self) -> None:
        """Test that reset clears source and linked tokens."""
        source = CancellationTokenSource()
        linked_token = CancellationToken()
        source.link(linked_token)

        source.cancel("Test")
        source.reset()

        assert not source.is_cancelled
        assert not linked_token.is_cancelled


class TestCancellationStats:
    """Tests for CancellationStats class."""

    def test_default_stats(self) -> None:
        """Test default stats values."""
        stats = CancellationStats()

        assert stats.total_cancellations == 0
        assert stats.timeout_cancellations == 0
        assert stats.user_cancellations == 0
        assert stats.system_cancellations == 0

    def test_record_timeout(self) -> None:
        """Test recording a timeout."""
        stats = CancellationStats()
        stats.record_timeout()

        assert stats.total_cancellations == 1
        assert stats.timeout_cancellations == 1

    def test_record_user_cancellation(self) -> None:
        """Test recording a user cancellation."""
        stats = CancellationStats()
        stats.record_user_cancellation()

        assert stats.total_cancellations == 1
        assert stats.user_cancellations == 1

    def test_record_system_cancellation(self) -> None:
        """Test recording a system cancellation."""
        stats = CancellationStats()
        stats.record_system_cancellation()

        assert stats.total_cancellations == 1
        assert stats.system_cancellations == 1

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        stats = CancellationStats()
        stats.record_timeout()
        stats.record_user_cancellation()

        result = stats.to_dict()

        assert result["total_cancellations"] == 2
        assert result["timeout_cancellations"] == 1
        assert result["user_cancellations"] == 1


class TestAgentCancelledError:
    """Tests for AgentCancelledError exception."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = AgentCancelledError()
        assert "cancelled" in str(error).lower()
        assert error.message == "Operation was cancelled"

    def test_custom_message(self) -> None:
        """Test custom error message."""
        error = AgentCancelledError("Custom reason")
        assert "Custom reason" in str(error)
        assert error.message == "Custom reason"


class TestAgentTimeoutError:
    """Tests for AgentTimeoutError exception."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = AgentTimeoutError()
        assert "timed out" in str(error).lower()

    def test_with_timeout_seconds(self) -> None:
        """Test with timeout duration."""
        error = AgentTimeoutError(timeout_seconds=30.0)
        assert error.timeout_seconds == 30.0


# ============= TimeoutSettings Tests =============


class TestTimeoutSettings:
    """Tests for TimeoutSettings class."""

    def test_default_timeouts(self) -> None:
        """Test default timeout values."""
        settings = TimeoutSettings()

        assert settings.default_timeout == 30.0
        assert settings.web_search_timeout == 45.0
        assert settings.todoist_timeout == 20.0

    def test_get_timeout_for_agent(self) -> None:
        """Test getting timeout for specific agent types."""
        settings = TimeoutSettings()

        assert settings.get_timeout_for_agent(AgentType.WEB_SEARCH) == 45.0
        assert settings.get_timeout_for_agent(AgentType.TODOIST) == 20.0
        assert settings.get_timeout_for_agent(AgentType.NEWS) == 40.0
        assert settings.get_timeout_for_agent(AgentType.DEFAULT) == 30.0

    def test_get_timeout_for_unknown_agent(self) -> None:
        """Test getting timeout for unknown agent type."""
        settings = TimeoutSettings()

        # Unknown agents should use default timeout
        assert (
            settings.get_timeout_for_agent(AgentType.ANALYSIS)
            == settings.default_timeout
        )


# ============= AgentExecutor Tests =============


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(
        self,
        response: str = "Test response",
        delay: float = 0.0,
        should_raise: Exception | None = None,
    ) -> None:
        """Initialize mock agent."""
        self._response = response
        self._delay = delay
        self._should_raise = should_raise
        super().__init__(llm_provider=None)  # type: ignore

    @property
    def agent_type(self) -> AgentType:
        """Return agent type."""
        return AgentType.DEFAULT

    @property
    def system_prompt(self) -> str:
        """Return system prompt."""
        return "You are a test agent."

    def can_handle(self, message: str, context: dict | None = None) -> float:
        """Return confidence score."""
        return 1.0

    async def process(
        self,
        message: str,
        context: dict | None = None,
        history: list | None = None,
    ) -> AgentResult:
        """Process message."""
        if self._should_raise:
            raise self._should_raise

        if self._delay:
            await asyncio.sleep(self._delay)

        return AgentResult(
            response=self._response,
            agent_type=self.agent_type,
        )


class TestAgentExecutor:
    """Tests for AgentExecutor class."""

    @pytest.mark.asyncio
    async def test_execute_successful(self) -> None:
        """Test successful execution."""
        executor = AgentExecutor()
        agent = MockAgent(response="Hello!")

        result = await executor.execute(
            agent=agent,
            message="Hi",
            context={},
            history=[],
        )

        assert result.success
        assert result.result is not None
        assert result.result.response == "Hello!"
        assert not result.timed_out
        assert not result.cancelled

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self) -> None:
        """Test execution with timeout."""
        executor = AgentExecutor()
        # Agent that takes 2 seconds
        agent = MockAgent(delay=2.0)

        result = await executor.execute(
            agent=agent,
            message="Hi",
            context={},
            history=[],
            timeout=0.1,  # 100ms timeout
        )

        assert not result.success
        assert result.timed_out
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_with_cancellation(self) -> None:
        """Test execution with pre-cancelled token."""
        executor = AgentExecutor()
        agent = MockAgent()
        token = CancellationToken()
        token.cancel("User cancelled")

        result = await executor.execute(
            agent=agent,
            message="Hi",
            context={},
            history=[],
            cancellation_token=token,
        )

        assert not result.success
        assert result.cancelled
        assert "User cancelled" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_with_error(self) -> None:
        """Test execution when agent raises an error."""
        executor = AgentExecutor()
        agent = MockAgent(should_raise=ValueError("Test error"))

        result = await executor.execute(
            agent=agent,
            message="Hi",
            context={},
            history=[],
        )

        assert not result.success
        assert "Test error" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_returns_fallback_on_timeout(self) -> None:
        """Test that timeout returns a fallback result."""
        executor = AgentExecutor(fallback_response="Fallback message")
        agent = MockAgent(delay=5.0)

        result = await executor.execute(
            agent=agent,
            message="Hi",
            context={},
            history=[],
            timeout=0.1,
        )

        assert result.result is not None
        assert result.result.response == "Fallback message"
        assert result.result.metadata.get("fallback") is True
        assert result.result.metadata.get("reason") == "timeout"

    @pytest.mark.asyncio
    async def test_execute_plan_step(self) -> None:
        """Test execute_plan_step convenience method."""
        executor = AgentExecutor()
        agent = MockAgent(response="Step result")

        result = await executor.execute_plan_step(
            agent=agent,
            message="Hi",
            context={},
            history=[],
        )

        assert isinstance(result, AgentResult)
        assert result.response == "Step result"

    @pytest.mark.asyncio
    async def test_execution_time_measured(self) -> None:
        """Test that execution time is measured."""
        executor = AgentExecutor()
        agent = MockAgent(delay=0.1)

        result = await executor.execute(
            agent=agent,
            message="Hi",
            context={},
            history=[],
        )

        assert result.execution_time_ms >= 100  # At least 100ms


class TestExecutionResult:
    """Tests for ExecutionResult class."""

    def test_default_values(self) -> None:
        """Test default values."""
        result = ExecutionResult()

        assert result.result is None
        assert result.success
        assert not result.timed_out
        assert not result.cancelled
        assert result.error_message is None

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        result = ExecutionResult(
            success=False,
            timed_out=True,
            error_message="Test error",
            execution_time_ms=150.5,
            timeout_seconds=30.0,
        )

        data = result.to_dict()

        assert data["success"] is False
        assert data["timed_out"] is True
        assert data["error_message"] == "Test error"
        assert data["execution_time_ms"] == 150.5
        assert data["timeout_seconds"] == 30.0
