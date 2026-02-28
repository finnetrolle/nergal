"""Unit tests for NativeToolDispatcher.

Tests the dispatcher for LLM providers with native tool support.
"""

import pytest

from nergal.dispatcher.base import ParsedToolCall, ToolDispatcher
from nergal.dispatcher.native import NativeToolDispatcher
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


class TestNativeToolDispatcher:
    """Tests for NativeToolDispatcher."""

    def test_init_creates_dispatcher(self):
        """Test that dispatcher initializes correctly."""
        dispatcher = NativeToolDispatcher()
        assert isinstance(dispatcher, ToolDispatcher)

    def test_parse_response_no_tool_calls(self):
        """Test parsing response with no tool calls."""
        dispatcher = NativeToolDispatcher()
        response = LLMResponse(
            content="Hello, world!",
            model="test-model",
            tool_calls=None,
        )

        text, calls = dispatcher.parse_response(response)

        assert text == "Hello, world!"
        assert calls == []

    def test_parse_response_empty_content_no_tool_calls(self):
        """Test parsing response with empty content and no tool calls."""
        dispatcher = NativeToolDispatcher()
        response = LLMResponse(
            content="",
            model="test-model",
            tool_calls=None,
        )

        text, calls = dispatcher.parse_response(response)

        assert text == ""
        assert calls == []

    def test_parse_response_openai_style(self):
        """Test parsing OpenAI-style tool calls."""
        dispatcher = NativeToolDispatcher()
        response = LLMResponse(
            content="I'll help you with that.",
            model="test-model",
            tool_calls=[
                {
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "file_read",
                        "arguments": '{"path": "/tmp/file.txt"}',
                    },
                }
            ],
        )

        text, calls = dispatcher.parse_response(response)

        assert text == "I'll help you with that."
        assert len(calls) == 1
        assert calls[0].name == "file_read"
        assert calls[0].arguments == {"path": "/tmp/file.txt"}
        assert calls[0].tool_call_id == "call_abc123"

    def test_parse_response_anthropic_style(self):
        """Test parsing Anthropic-style tool calls."""
        dispatcher = NativeToolDispatcher()
        response = LLMResponse(
            content="Let me read that file.",
            model="test-model",
            tool_calls=[
                {
                    "id": "toolu_abc123",
                    "name": "file_write",
                    "input": {"path": "/tmp/output.txt", "content": "Hello"},
                }
            ],
        )

        text, calls = dispatcher.parse_response(response)

        assert text == "Let me read that file."
        assert len(calls) == 1
        assert calls[0].name == "file_write"
        assert calls[0].arguments == {"path": "/tmp/output.txt", "content": "Hello"}
        assert calls[0].tool_call_id == "toolu_abc123"

    def test_parse_response_multiple_tool_calls(self):
        """Test parsing multiple tool calls."""
        dispatcher = NativeToolDispatcher()
        response = LLMResponse(
            content="",
            model="test-model",
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "file_read",
                        "arguments": '{"path": "/tmp/file1.txt"}',
                    },
                },
                {
                    "id": "call_2",
                    "type": "function",
                    "function": {
                        "name": "file_read",
                        "arguments": '{"path": "/tmp/file2.txt"}',
                    },
                },
            ],
        )

        text, calls = dispatcher.parse_response(response)

        assert len(calls) == 2
        assert calls[0].tool_call_id == "call_1"
        assert calls[1].tool_call_id == "call_2"
        assert calls[0].arguments == {"path": "/tmp/file1.txt"}
        assert calls[1].arguments == {"path": "/tmp/file2.txt"}

    def test_format_results_empty(self):
        """Test formatting empty results list."""
        dispatcher = NativeToolDispatcher()
        formatted = dispatcher.format_results([])

        assert formatted == ""

    def test_format_results_success(self):
        """Test formatting successful tool results."""
        dispatcher = NativeToolDispatcher()
        results = [
            ToolResult(success=True, output="File read successfully"),
            ToolResult(success=True, output="Command executed"),
        ]

        formatted = dispatcher.format_results(results)

        assert "File read successfully" in formatted
        assert "Command executed" in formatted
        assert formatted.count("Tool result:") == 2

    def test_format_results_error(self):
        """Test formatting failed tool results."""
        dispatcher = NativeToolDispatcher()
        results = [
            ToolResult(success=False, output="", error="File not found"),
            ToolResult(success=True, output="Success"),
        ]

        formatted = dispatcher.format_results(results)

        assert "File not found" in formatted
        assert "Success" in formatted
        assert "Tool error:" in formatted
        assert "Tool result:" in formatted

    def test_prompt_instructions_returns_empty(self):
        """Test that prompt_instructions returns empty string."""
        dispatcher = NativeToolDispatcher()
        tool = MockTool()

        instructions = dispatcher.prompt_instructions([tool])

        assert instructions == ""

    def test_should_send_tool_specs_returns_true(self):
        """Test that should_send_tool_specs returns True."""
        dispatcher = NativeToolDispatcher()

        assert dispatcher.should_send_tool_specs() is True

    def test_parse_invalid_json_arguments(self):
        """Test parsing tool calls with invalid JSON arguments."""
        dispatcher = NativeToolDispatcher()
        response = LLMResponse(
            content="",
            model="test-model",
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "file_read",
                        "arguments": "invalid json {{{",
                    },
                }
            ],
        )

        text, calls = dispatcher.parse_response(response)

        # Should still parse the call, but with empty arguments
        assert len(calls) == 1
        assert calls[0].name == "file_read"
        assert calls[0].arguments == {}

    def test_parse_unknown_tool_call_format(self):
        """Test parsing tool calls with unknown format."""
        dispatcher = NativeToolDispatcher()
        response = LLMResponse(
            content="",
            model="test-model",
            tool_calls=[{"id": "call_1", "unknown_field": "value"}],
        )

        text, calls = dispatcher.parse_response(response)

        # Unknown format should be skipped
        assert len(calls) == 0
