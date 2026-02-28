"""Tests for ExecutionContext and StepResult classes."""

from unittest.mock import MagicMock

from nergal.dialog.base import AgentType, StepResult
from nergal.dialog.context import ExecutionContext


class TestStepResult:
    """Tests for StepResult class."""

    def test_step_result_creation(self) -> None:
        """Test basic StepResult creation."""
        result = StepResult(
            step_index=0,
            agent_type=AgentType.WEB_SEARCH,
            output="Search results found",
            structured_data={"results": ["a", "b"]},
            confidence=0.95,
            execution_time_ms=150.5,
        )

        assert result.step_index == 0
        assert result.agent_type == AgentType.WEB_SEARCH
        assert result.output == "Search results found"
        assert result.structured_data == {"results": ["a", "b"]}
        assert result.confidence == 0.95
        assert result.execution_time_ms == 150.5
        assert result.success is True
        assert result.error_message is None

    def test_step_result_defaults(self) -> None:
        """Test StepResult default values."""
        result = StepResult(
            step_index=0,
            agent_type=AgentType.DEFAULT,
            output="Response",
        )

        assert result.structured_data == {}
        assert result.confidence == 1.0
        assert result.execution_time_ms == 0.0
        assert result.success is True
        assert result.error_message is None

    def test_step_result_failure(self) -> None:
        """Test StepResult for failed step."""
        result = StepResult(
            step_index=1,
            agent_type=AgentType.WEB_SEARCH,
            output="",
            success=False,
            error_message="API error",
        )

        assert result.success is False
        assert result.error_message == "API error"

    def test_to_context_string_short(self) -> None:
        """Test to_context_string with short output."""
        result = StepResult(
            step_index=0,
            agent_type=AgentType.WEB_SEARCH,
            output="Short output",
            structured_data={"key": "value"},
        )

        context = result.to_context_string()

        assert "[Step 0]" in context
        assert "web_search" in context
        assert "✓" in context
        assert "Short output" in context
        assert "Data: ['key']" in context

    def test_to_context_string_long(self) -> None:
        """Test to_context_string truncates long output."""
        long_output = "x" * 600
        result = StepResult(
            step_index=2,
            agent_type=AgentType.DEFAULT,
            output=long_output,
        )

        context = result.to_context_string()

        assert "..." in context
        assert len([line for line in context.split("\n") if "Output:" in line][0]) < 600

    def test_to_context_string_failed(self) -> None:
        """Test to_context_string for failed step."""
        result = StepResult(
            step_index=0,
            agent_type=AgentType.WEB_SEARCH,
            output="",
            success=False,
            error_message="Connection timeout",
        )

        context = result.to_context_string()

        assert "✗" in context
        assert "Error: Connection timeout" in context


class TestExecutionContext:
    """Tests for ExecutionContext class."""

    def test_execution_context_creation(self) -> None:
        """Test basic ExecutionContext creation."""
        context = ExecutionContext(
            original_message="What is Python?",
            user_context={"user_id": 123},
        )

        assert context.original_message == "What is Python?"
        assert context.user_context == {"user_id": 123}
        assert context.step_results == {}
        assert context.plan_id is None
        assert context.completed_step_count == 0

    def test_add_result(self) -> None:
        """Test adding step results."""
        context = ExecutionContext(original_message="Test")

        result1 = StepResult(
            step_index=0,
            agent_type=AgentType.WEB_SEARCH,
            output="Search result",
        )
        context.add_result(result1)

        assert context.completed_step_count == 1
        assert context.get_result(0) == result1

    def test_get_result(self) -> None:
        """Test getting result by step index."""
        context = ExecutionContext(original_message="Test")

        result = StepResult(
            step_index=1,
            agent_type=AgentType.DEFAULT,
            output="Response",
        )
        context.add_result(result)

        assert context.get_result(1) == result
        assert context.get_result(0) is None
        assert context.get_result(99) is None

    def test_get_result_by_agent(self) -> None:
        """Test getting result by agent type."""
        context = ExecutionContext(original_message="Test")

        result1 = StepResult(
            step_index=0,
            agent_type=AgentType.WEB_SEARCH,
            output="Search",
        )
        result2 = StepResult(
            step_index=1,
            agent_type=AgentType.DEFAULT,
            output="Final",
        )
        context.add_result(result1)
        context.add_result(result2)

        web_result = context.get_result_by_agent(AgentType.WEB_SEARCH)
        assert web_result == result1

        default_result = context.get_result_by_agent(AgentType.DEFAULT)
        assert default_result == result2

        # Non-existent agent - create a mock agent type for testing
        mock_agent_type = MagicMock()
        mock_agent_type.value = "non_existent_agent"
        assert context.get_result_by_agent(mock_agent_type) is None

    def test_get_result_by_agent_returns_most_recent(self) -> None:
        """Test that get_result_by_agent returns most recent result."""
        context = ExecutionContext(original_message="Test")

        result1 = StepResult(
            step_index=0,
            agent_type=AgentType.DEFAULT,
            output="First",
        )
        result2 = StepResult(
            step_index=2,
            agent_type=AgentType.DEFAULT,
            output="Second",
        )
        context.add_result(result1)
        context.add_result(result2)

        # Should return the most recent (step 2)
        result = context.get_result_by_agent(AgentType.DEFAULT)
        assert result == result2

    def test_get_all_results_by_agent(self) -> None:
        """Test getting all results for an agent type."""
        context = ExecutionContext(original_message="Test")

        result1 = StepResult(
            step_index=0,
            agent_type=AgentType.DEFAULT,
            output="First",
        )
        result2 = StepResult(
            step_index=1,
            agent_type=AgentType.WEB_SEARCH,
            output="Search",
        )
        result3 = StepResult(
            step_index=2,
            agent_type=AgentType.DEFAULT,
            output="Second",
        )
        context.add_result(result1)
        context.add_result(result2)
        context.add_result(result3)

        default_results = context.get_all_results_by_agent(AgentType.DEFAULT)
        assert len(default_results) == 2
        assert default_results[0] == result1
        assert default_results[1] == result3

        web_results = context.get_all_results_by_agent(AgentType.WEB_SEARCH)
        assert len(web_results) == 1

    def test_get_accumulated_context(self) -> None:
        """Test building accumulated context string."""
        context = ExecutionContext(original_message="Test message")

        result1 = StepResult(
            step_index=0,
            agent_type=AgentType.WEB_SEARCH,
            output="Found 5 results",
            structured_data={"count": 5},
        )
        result2 = StepResult(
            step_index=1,
            agent_type=AgentType.DEFAULT,
            output="Final answer",
        )
        context.add_result(result1)
        context.add_result(result2)

        accumulated = context.get_accumulated_context()

        assert "=== Previous Step Results ===" in accumulated
        assert "[Step 0]" in accumulated
        assert "web_search" in accumulated
        assert "Found 5 results" in accumulated
        assert "[Step 1]" in accumulated
        assert "default" in accumulated
        assert "Final answer" in accumulated

    def test_get_accumulated_context_empty(self) -> None:
        """Test accumulated context with no results."""
        context = ExecutionContext(original_message="Test")

        accumulated = context.get_accumulated_context()

        assert accumulated == ""

    def test_get_successful_results(self) -> None:
        """Test getting only successful results."""
        context = ExecutionContext(original_message="Test")

        result1 = StepResult(
            step_index=0,
            agent_type=AgentType.WEB_SEARCH,
            output="Success 1",
            success=True,
        )
        result2 = StepResult(
            step_index=1,
            agent_type=AgentType.WEB_SEARCH,
            output="",
            success=False,
            error_message="Failed",
        )
        result3 = StepResult(
            step_index=2,
            agent_type=AgentType.DEFAULT,
            output="Success 2",
            success=True,
        )
        context.add_result(result1)
        context.add_result(result2)
        context.add_result(result3)

        successful = context.get_successful_results()

        assert len(successful) == 2
        assert result1 in successful
        assert result3 in successful
        assert result2 not in successful

    def test_has_failures(self) -> None:
        """Test checking for failures."""
        context = ExecutionContext(original_message="Test")

        assert not context.has_failures()

        result1 = StepResult(
            step_index=0,
            agent_type=AgentType.DEFAULT,
            output="OK",
            success=True,
        )
        context.add_result(result1)

        assert not context.has_failures()

        result2 = StepResult(
            step_index=1,
            agent_type=AgentType.WEB_SEARCH,
            output="",
            success=False,
        )
        context.add_result(result2)

        assert context.has_failures()

    def test_get_failed_results(self) -> None:
        """Test getting failed results."""
        context = ExecutionContext(original_message="Test")

        result1 = StepResult(
            step_index=0,
            agent_type=AgentType.DEFAULT,
            output="OK",
            success=True,
        )
        result2 = StepResult(
            step_index=1,
            agent_type=AgentType.WEB_SEARCH,
            output="",
            success=False,
            error_message="Error 1",
        )
        result3 = StepResult(
            step_index=2,
            agent_type=AgentType.WEB_SEARCH,
            output="",
            success=False,
            error_message="Error 2",
        )
        context.add_result(result1)
        context.add_result(result2)
        context.add_result(result3)

        failed = context.get_failed_results()

        assert len(failed) == 2
        assert result2 in failed
        assert result3 in failed

    def test_completed_step_count(self) -> None:
        """Test completed_step_count property."""
        context = ExecutionContext(original_message="Test")

        assert context.completed_step_count == 0

        context.add_result(StepResult(step_index=0, agent_type=AgentType.DEFAULT, output="1"))
        assert context.completed_step_count == 1

        context.add_result(StepResult(step_index=1, agent_type=AgentType.DEFAULT, output="2"))
        assert context.completed_step_count == 2

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        context = ExecutionContext(
            original_message="Test message",
            user_context={"user_id": 123, "name": "User"},
            plan_id="plan-123",
        )

        result_dict = context.to_dict()

        assert result_dict["original_message"] == "Test message"
        assert result_dict["user_context"] == {"user_id": 123, "name": "User"}
        assert result_dict["plan_id"] == "plan-123"
        assert "started_at" in result_dict
        assert result_dict["completed_steps"] == 0
        assert result_dict["has_failures"] is False

    def test_to_dict_with_results(self) -> None:
        """Test to_dict includes result metadata."""
        context = ExecutionContext(original_message="Test")

        context.add_result(StepResult(
            step_index=0,
            agent_type=AgentType.DEFAULT,
            output="OK",
            success=True,
        ))
        context.add_result(StepResult(
            step_index=1,
            agent_type=AgentType.WEB_SEARCH,
            output="",
            success=False,
        ))

        result_dict = context.to_dict()

        assert result_dict["completed_steps"] == 2
        assert result_dict["has_failures"] is True


class TestExecutionContextIntegration:
    """Integration tests for ExecutionContext with multiple steps."""

    def test_multi_step_workflow(self) -> None:
        """Test a typical multi-step workflow."""
        context = ExecutionContext(
            original_message="What are the latest AI developments?",
            user_context={"user_id": 1, "language": "en"},
        )

        # Step 0: Web search
        search_result = StepResult(
            step_index=0,
            agent_type=AgentType.WEB_SEARCH,
            output="Found 10 articles about AI",
            structured_data={
                "sources": ["article1.com", "article2.com"],
                "result_count": 10,
            },
            confidence=0.9,
            execution_time_ms=250.0,
        )
        context.add_result(search_result)

        # Step 1: Additional processing
        analysis_result = StepResult(
            step_index=1,
            agent_type=AgentType.DEFAULT,
            output="Processed the search results",
            structured_data={
                "tasks": ["Buy groceries", "Call mom", "Finish project"],
                "completed": 1,
            },
            confidence=0.85,
            execution_time_ms=180.0,
        )
        context.add_result(analysis_result)

        # Step 2: Summary
        summary_result = StepResult(
            step_index=2,
            agent_type=AgentType.DEFAULT,
            output="Summary of AI developments...",
            confidence=0.95,
            execution_time_ms=100.0,
        )
        context.add_result(summary_result)

        # Verify state
        assert context.completed_step_count == 3
        assert not context.has_failures()

        # Get accumulated context
        accumulated = context.get_accumulated_context()
        assert "web_search" in accumulated
        assert "default" in accumulated

        # Get specific results
        web_result = context.get_result_by_agent(AgentType.WEB_SEARCH)
        assert web_result is not None
        assert web_result.structured_data["result_count"] == 10

    def test_workflow_with_partial_failure(self) -> None:
        """Test workflow where one step fails."""
        context = ExecutionContext(original_message="Create a task and search for info")

        # Step 0: Default agent succeeds
        task_result = StepResult(
            step_index=0,
            agent_type=AgentType.DEFAULT,
            output="Task created successfully",
            structured_data={"task_id": "12345"},
            success=True,
        )
        context.add_result(task_result)

        # Step 1: Web search fails
        search_result = StepResult(
            step_index=1,
            agent_type=AgentType.WEB_SEARCH,
            output="",
            success=False,
            error_message="Search API unavailable",
        )
        context.add_result(search_result)

        # Step 2: Default agent handles fallback
        default_result = StepResult(
            step_index=2,
            agent_type=AgentType.DEFAULT,
            output="I created your task but couldn't search for info",
            success=True,
        )
        context.add_result(default_result)

        # Verify state
        assert context.completed_step_count == 3
        assert context.has_failures()

        # Get failed results
        failed = context.get_failed_results()
        assert len(failed) == 1
        assert failed[0].agent_type == AgentType.WEB_SEARCH

        # Get successful results
        successful = context.get_successful_results()
        assert len(successful) == 2
