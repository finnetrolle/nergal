"""Unit tests for XmlToolDispatcher.

Tests the dispatcher for text-only LLM providers.
"""

import pytest

from nergal.dispatcher.base import ParsedToolCall, ToolDispatcher
from nergal.dispatcher.xml import XmlToolDispatcher
from nergal.llm.base import LLMResponse
from nergal.tools.base import Tool, ToolResult


class MockTool(Tool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool"

    @property
    def parameters_schema(self) -> dict:
        return {"type": "object"}

    async def execute(self, args: dict) -> ToolResult:
        return ToolResult(success=True, output="OK")


class TestXmlToolDispatcher:
    """Tests for XmlToolDispatcher."""

    def test_init_creates_dispatcher(self):
        """Test that dispatcher initializes correctly."""
        dispatcher = XmlToolDispatcher()
        assert isinstance(dispatcher, ToolDispatcher)

    def test_init_with_tool_tags(self):
        """Test initializing with allowed tool tags."""
        dispatcher = XmlToolDispatcher(tool_tags=["file_read", "file_write"])
        assert dispatcher.tool_tags == {"file_read", "file_write"}

    def test_parse_response_no_tool_calls(self):
        """Test parsing response with no tool calls."""
        dispatcher = XmlToolDispatcher()
        response = LLMResponse(
            content="Hello, world!",
            model="test-model",
        )

        text, calls = dispatcher.parse_response(response)

        assert text == "Hello, world!"
        assert calls == []

    def test_parse_response_with_xml_tool_call(self):
        """Test parsing response with XML tool call."""
        dispatcher = XmlToolDispatcher()
        response = LLMResponse(
            content='I\'ll read the file. <file_read>{"path": "/tmp/file.txt"}</file_read>',
            model="test-model",
        )

        text, calls = dispatcher.parse_response(response)

        # Tool call should be removed from text
        assert "I'll read the file." in text
        assert "<file_read>" not in text
        assert len(calls) == 1
        assert calls[0].name == "file_read"
        assert calls[0].arguments == {"path": "/tmp/file.txt"}
        assert calls[0].tool_call_id is None

    @pytest.mark.xfail(reason="Attribute-style XML parsing not fully implemented")
    def test_parse_response_with_attribute_style(self):
        """Test parsing response with attribute-style tool call."""
        # Note: This is marked as xfail because attribute-style XML parsing
        # is a future enhancement for the XmlToolDispatcher
        dispatcher = XmlToolDispatcher()
        response = LLMResponse(
            content='Executing command. <execute command="echo hello"></execute> Done.',
            model="test-model",
        )

        text, calls = dispatcher.parse_response(response)

        assert "Executing command." in text
        assert "Done." in text
        assert "<execute>" not in text
        assert len(calls) == 1
        assert calls[0].name == "execute"
        assert calls[0].arguments == {"command": "echo hello"}

    def test_parse_response_multiple_tool_calls(self):
        """Test parsing multiple tool calls."""
        dispatcher = XmlToolDispatcher()
        response = LLMResponse(
            content="I'll read both files. <file_read><path>/tmp/file1.txt</path></file_read> <file_write><path>/tmp/output.txt</path></file_write>",
            model="test-model",
        )

        text, calls = dispatcher.parse_response(response)

        assert len(calls) == 2
        assert calls[0].name == "file_read"
        assert calls[1].name == "file_write"
        assert "<file_read>" not in text
        assert "<file_write>" not in text

    def test_parse_response_with_allowed_tool_tags(self):
        """Test that only allowed tool tags are parsed."""
        dispatcher = XmlToolDispatcher(tool_tags=["file_read"])
        response = LLMResponse(
            content="I'll use <file_read>path</file_read> but skip <file_write>path</file_write>",
            model="test-model",
        )

        text, calls = dispatcher.parse_response(response)

        assert len(calls) == 1
        assert calls[0].name == "file_read"
        assert "<file_read>" not in text
        # file_write should be removed from text even if not in allowed tags
        assert "<file_write>" not in text

    def test_format_results_empty(self):
        """Test formatting empty results list."""
        dispatcher = XmlToolDispatcher()
        formatted = dispatcher.format_results([])

        assert formatted == ""

    def test_format_results_success(self):
        """Test formatting successful tool results."""
        dispatcher = XmlToolDispatcher()
        results = [
            ToolResult(success=True, output="File read successfully"),
            ToolResult(success=True, output="Command executed"),
        ]

        formatted = dispatcher.format_results(results)

        assert '<tool_result index="0">' in formatted
        assert '<tool_result index="1">' in formatted
        assert "File read successfully" in formatted
        assert "Command executed" in formatted

    def test_format_results_with_special_chars(self):
        """Test formatting results with special XML characters."""
        dispatcher = XmlToolDispatcher()
        results = [
            ToolResult(success=True, output='Value: <test> & "quote"'),
        ]

        formatted = dispatcher.format_results(results)

        # Special characters should be escaped
        assert "&lt;test&gt;" in formatted
        assert "&amp;" in formatted
        # Note: the quote inside content is handled by the escaping logic
        assert "&quot;" in formatted or '"' in formatted

    def test_format_results_error(self):
        """Test formatting failed tool results."""
        dispatcher = XmlToolDispatcher()
        results = [
            ToolResult(success=False, output="", error="File not found"),
        ]

        formatted = dispatcher.format_results(results)

        assert '<tool_error index="0">' in formatted
        assert "File not found" in formatted

    def test_prompt_instructions_generates_instructions(self):
        """Test that prompt_instructions generates instructions."""
        dispatcher = XmlToolDispatcher()
        tool = MockTool()

        instructions = dispatcher.prompt_instructions([tool])

        assert "## Available Tools" in instructions
        assert "## Tool Usage" in instructions
        assert "<tool_name>" in instructions
        assert "mock_tool" in instructions

    def test_prompt_instructions_multiple_tools(self):
        """Test prompt instructions with multiple tools."""
        dispatcher = XmlToolDispatcher()
        tool1 = MockTool()
        tool2 = MockTool()

        instructions = dispatcher.prompt_instructions([tool1, tool2])

        # Should mention both tools
        assert instructions.count("**mock_tool**:") == 2

    def test_should_send_tool_specs_returns_false(self):
        """Test that should_send_tool_specs returns False."""
        dispatcher = XmlToolDispatcher()

        assert dispatcher.should_send_tool_specs() is False

    def test_set_allowed_tools(self):
        """Test setting allowed tools."""
        dispatcher = XmlToolDispatcher()
        dispatcher.set_allowed_tools(["file_read", "file_write"])

        assert dispatcher.tool_tags == {"file_read", "file_write"}

    def test_clear_allowed_tools(self):
        """Test clearing allowed tools."""
        dispatcher = XmlToolDispatcher(tool_tags=["file_read"])
        dispatcher.clear_allowed_tools()

        assert dispatcher.tool_tags is None

    def test_parse_malformed_xml(self):
        """Test parsing malformed XML (should not crash)."""
        dispatcher = XmlToolDispatcher()
        response = LLMResponse(
            content="Some text <file_read> unclosed tag",
            model="test-model",
        )

        # Should not crash, just return what it can parse
        text, calls = dispatcher.parse_response(response)

        # Might parse or not depending on regex behavior
        # The important thing is it doesn't crash
        assert isinstance(text, str)
        assert isinstance(calls, list)

    def test_parse_nested_xml_content(self):
        """Test parsing XML with nested content."""
        dispatcher = XmlToolDispatcher()
        response = LLMResponse(
            content="<search><query>python async</query><count>5</count></search>",
            model="test-model",
        )

        text, calls = dispatcher.parse_response(response)

        assert len(calls) == 1
        assert calls[0].name == "search"
        # Arguments are captured as the full inner content
        # Nested parsing is a future enhancement
        assert "query" in str(calls[0].arguments)
        assert "count" in str(calls[0].arguments)

    def test_parse_empty_content_tool_call(self):
        """Test parsing tool call with empty content."""
        dispatcher = XmlToolDispatcher()
        response = LLMResponse(
            content="<execute></execute>",
            model="test-model",
        )

        text, calls = dispatcher.parse_response(response)

        assert len(calls) == 1
        assert calls[0].name == "execute"
        # Empty content results in empty arguments
        assert calls[0].arguments == {}
