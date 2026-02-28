"""Unit tests for tool base classes and exceptions."""

import pytest

from nergal.tools.base import Tool, ToolResult
from nergal.tools.exceptions import (
    SecurityPolicyViolationError,
    ToolExecutionError,
    ToolError,
    ToolTimeoutError,
    ToolValidationError,
)


class MockTool(Tool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"},
            },
        }

    async def execute(self, args: dict) -> ToolResult:
        return ToolResult(success=True, output=f"Executed with: {args}")


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_result(self):
        """Test creating a successful result."""
        result = ToolResult(success=True, output="File written successfully")
        assert result.success is True
        assert result.output == "File written successfully"
        assert result.error is None
        assert result.metadata is None

    def test_error_result(self):
        """Test creating an error result."""
        result = ToolResult(
            success=False,
            output="",
            error="Permission denied",
        )
        assert result.success is False
        assert result.output == ""
        assert result.error == "Permission denied"

    def test_result_with_metadata(self):
        """Test creating a result with metadata."""
        result = ToolResult(
            success=True,
            output="Done",
            metadata={"execution_time": 0.5, "attempts": 1},
        )
        assert result.success is True
        assert result.metadata == {"execution_time": 0.5, "attempts": 1}


class TestToolError:
    """Tests for ToolError exception hierarchy."""

    def test_tool_error(self):
        """Test base ToolError."""
        error = ToolError("Something went wrong")
        assert error.message == "Something went wrong"
        assert str(error) == "Something went wrong"

    def test_tool_execution_error(self):
        """Test ToolExecutionError."""
        error = ToolExecutionError(tool_name="file_read", message="File not found")
        assert error.tool_name == "file_read"
        assert error.message == "File not found"
        assert str(error) == "[file_read] File not found"

    def test_tool_timeout_error(self):
        """Test ToolTimeoutError."""
        error = ToolTimeoutError(tool_name="shell_execute", timeout=30.0)
        assert error.tool_name == "shell_execute"
        assert error.timeout == 30.0
        assert str(error) == "[shell_execute] Execution timed out after 30.0 seconds"

    def test_tool_validation_error_with_field(self):
        """Test ToolValidationError with field specified."""
        error = ToolValidationError(tool_name="my_tool", field="count", message="must be positive")
        assert error.tool_name == "my_tool"
        assert error.field == "count"
        assert "count" in str(error)
        assert "must be positive" in str(error)

    def test_tool_validation_error_without_field(self):
        """Test ToolValidationError without field."""
        error = ToolValidationError(tool_name="my_tool", message="Invalid arguments")
        assert error.field is None
        assert str(error) == "[my_tool] Validation failed: Invalid arguments"

    def test_security_policy_violation_error(self):
        """Test SecurityPolicyViolationError."""
        error = SecurityPolicyViolationError(
            tool_name="file_read",
            reason="Path is outside workspace directory",
        )
        assert error.tool_name == "file_read"
        assert error.reason == "Path is outside workspace directory"
        assert "Security policy violation" in str(error)

    def test_tool_error_catch_base(self):
        """Test that all tool errors can be caught as ToolError."""
        errors = [
            ToolError("base"),
            ToolExecutionError("tool", "msg"),
            ToolTimeoutError("tool", 10),
            ToolValidationError("tool", message="msg"),
            SecurityPolicyViolationError("tool", "reason"),
        ]

        for error in errors:
            assert isinstance(error, ToolError)
