"""Unit tests for Tool interface and ToolResult.

Tests follow TDD Red-Green-Refactor pattern.
"""

import pytest

from nergal.tools.base import Tool, ToolResult


class MockTool(Tool):
    """Mock tool for testing."""

    def __init__(self) -> None:
        self.name_value = "test_tool"
        self.description_value = "A test tool for unit tests"

    @property
    def name(self) -> str:
        return self.name_value

    @property
    def description(self) -> str:
        return self.description_value

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input parameter",
                }
            },
            "required": ["input"],
        }

    async def execute(self, args: dict) -> ToolResult:
        input_value = args.get("input", "")
        return ToolResult(
            success=True,
            output=f"Processed: {input_value}",
        )


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_result(self) -> None:
        """Test creating a successful ToolResult."""
        result = ToolResult(
            success=True,
            output="Hello, world!",
        )

        assert result.success is True
        assert result.output == "Hello, world!"
        assert result.error is None
        assert result.metadata is None

    def test_error_result(self) -> None:
        """Test creating an error ToolResult."""
        result = ToolResult(
            success=False,
            output="",
            error="Something went wrong",
        )

        assert result.success is False
        assert result.output == ""
        assert result.error == "Something went wrong"
        assert result.metadata is None

    def test_result_with_metadata(self) -> None:
        """Test creating a ToolResult with metadata."""
        metadata = {"execution_time": 0.5, "attempt": 1}
        result = ToolResult(
            success=True,
            output="Success",
            metadata=metadata,
        )

        assert result.success is True
        assert result.metadata == metadata
        assert result.metadata["execution_time"] == 0.5

    def test_result_with_output_and_error(self) -> None:
        """Test creating a ToolResult with both output and error."""
        result = ToolResult(
            success=False,
            output="Partial result",
            error="Failed to complete",
        )

        assert result.success is False
        assert result.output == "Partial result"
        assert result.error == "Failed to complete"


class TestToolInterface:
    """Tests for Tool abstract base class."""

    @pytest.mark.asyncio
    async def test_tool_properties(self) -> None:
        """Test that tool implements required properties."""
        tool = MockTool()

        assert tool.name == "test_tool"
        assert tool.description == "A test tool for unit tests"

        schema = tool.parameters_schema
        assert "type" in schema
        assert "properties" in schema
        assert "required" in schema

    @pytest.mark.asyncio
    async def test_tool_execute_success(self) -> None:
        """Test successful tool execution."""
        tool = MockTool()
        args = {"input": "test input"}

        result = await tool.execute(args)

        assert result.success is True
        assert "Processed: test input" in result.output
        assert result.error is None

    @pytest.mark.asyncio
    async def test_tool_execute_with_missing_args(self) -> None:
        """Test tool execution with missing arguments."""
        tool = MockTool()
        args = {}

        result = await tool.execute(args)

        # MockTool handles missing args gracefully
        assert result.success is True
        assert "Processed: " in result.output

    @pytest.mark.asyncio
    async def test_tool_is_abstract(self) -> None:
        """Test that Tool cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Tool()  # type: ignore

    def test_tool_name_is_property(self) -> None:
        """Test that name is a property, not a method."""
        tool = MockTool()
        # Should be able to access as property
        assert isinstance(getattr(type(tool), 'name'), property)

    def test_tool_description_is_property(self) -> None:
        """Test that description is a property, not a method."""
        tool = MockTool()
        # Should be able to access as property
        assert isinstance(getattr(type(tool), 'description'), property)

    def test_tool_parameters_schema_is_property(self) -> None:
        """Test that parameters_schema is a property, not a method."""
        tool = MockTool()
        # Should be able to access as property
        assert isinstance(getattr(type(tool), 'parameters_schema'), property)


class TestToolResultEdgeCases:
    """Edge case tests for ToolResult."""

    def test_empty_output(self) -> None:
        """Test ToolResult with empty output."""
        result = ToolResult(success=True, output="")

        assert result.success is True
        assert result.output == ""

    def test_empty_error_message(self) -> None:
        """Test ToolResult with empty error message."""
        result = ToolResult(success=False, output="", error="")

        assert result.success is False
        assert result.error == ""

    def test_metadata_none_explicit(self) -> None:
        """Test ToolResult with explicitly None metadata."""
        result = ToolResult(success=True, output="test", metadata=None)

        assert result.metadata is None

    def test_metadata_empty_dict(self) -> None:
        """Test ToolResult with empty metadata dict."""
        result = ToolResult(success=True, output="test", metadata={})

        assert result.metadata == {}
        assert isinstance(result.metadata, dict)

    def test_metadata_complex_values(self) -> None:
        """Test ToolResult with complex metadata values."""
        metadata = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "bool": True,
            "none": None,
        }
        result = ToolResult(success=True, output="test", metadata=metadata)

        assert result.metadata == metadata
        assert result.metadata["nested"]["key"] == "value"
        assert result.metadata["list"] == [1, 2, 3]
        assert result.metadata["bool"] is True
        assert result.metadata["none"] is None
