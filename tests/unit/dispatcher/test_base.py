"""Unit tests for ToolDispatcher base interface.

Tests follow TDD Red-Green-Refactor pattern.
"""

import pytest
from dataclasses import dataclass
from unittest.mock import Mock


# Mock data structures needed for tests
@dataclass
class MockToolCall:
    """Mock tool call structure."""
    id: str
    name: str
    arguments: dict


@dataclass
class MockChatResponse:
    """Mock LLM response."""
    text: str | None = None
    tool_calls: list[MockToolCall] | None = None


class TestParsedToolCall:
    """Tests for ParsedToolCall dataclass."""

    def test_parsed_tool_call_creation(self) -> None:
        """Test creating a ParsedToolCall."""
        from nergal.dispatcher.base import ParsedToolCall

        call = ParsedToolCall(
            name="test_tool",
            arguments={"key": "value"},
            tool_call_id="call_123",
        )

        assert call.name == "test_tool"
        assert call.arguments == {"key": "value"}
        assert call.tool_call_id == "call_123"

    def test_parsed_tool_call_without_id(self) -> None:
        """Test creating ParsedToolCall without tool_call_id."""
        from nergal.dispatcher.base import ParsedToolCall

        call = ParsedToolCall(
            name="test_tool",
            arguments={"key": "value"},
            tool_call_id=None,
        )

        assert call.name == "test_tool"
        assert call.arguments == {"key": "value"}
        assert call.tool_call_id is None

    def test_parsed_tool_call_empty_args(self) -> None:
        """Test creating ParsedToolCall with empty arguments."""
        from nergal.dispatcher.base import ParsedToolCall

        call = ParsedToolCall(
            name="test_tool",
            arguments={},
            tool_call_id=None,
        )

        assert call.name == "test_tool"
        assert call.arguments == {}


class TestToolDispatcherInterface:
    """Tests for ToolDispatcher abstract interface."""

    def test_dispatcher_is_abstract(self) -> None:
        """Test that ToolDispatcher cannot be instantiated directly."""
        from nergal.dispatcher.base import ToolDispatcher

        with pytest.raises(TypeError):
            ToolDispatcher()  # type: ignore

    def test_parse_response_is_abstract(self) -> None:
        """Test that parse_response is an abstract method."""
        from nergal.dispatcher.base import ToolDispatcher

        assert ToolDispatcher.parse_response.__isabstractmethod__

    def test_format_results_is_abstract(self) -> None:
        """Test that format_results is an abstract method."""
        from nergal.dispatcher.base import ToolDispatcher

        assert ToolDispatcher.format_results.__isabstractmethod__

    def test_prompt_instructions_is_abstract(self) -> None:
        """Test that prompt_instructions is an abstract method."""
        from nergal.dispatcher.base import ToolDispatcher

        assert ToolDispatcher.prompt_instructions.__isabstractmethod__

    def test_should_send_tool_specs_is_abstract(self) -> None:
        """Test that should_send_tool_specs is an abstract method."""
        from nergal.dispatcher.base import ToolDispatcher

        assert ToolDispatcher.should_send_tool_specs.__isabstractmethod__


class TestToolDispatcherDefaultBehavior:
    """Tests for default behavior of dispatcher methods."""

    def test_dispatcher_parse_response_signature(self) -> None:
        """Test parse_response method signature."""
        from nergal.dispatcher.base import ToolDispatcher
        from inspect import signature

        sig = signature(ToolDispatcher.parse_response)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "response" in params

    def test_dispatcher_format_results_signature(self) -> None:
        """Test format_results method signature."""
        from nergal.dispatcher.base import ToolDispatcher
        from inspect import signature

        sig = signature(ToolDispatcher.format_results)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "results" in params

    def test_dispatcher_prompt_instructions_signature(self) -> None:
        """Test prompt_instructions method signature."""
        from nergal.dispatcher.base import ToolDispatcher
        from inspect import signature

        sig = signature(ToolDispatcher.prompt_instructions)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "tools" in params

    def test_dispatcher_should_send_tool_specs_signature(self) -> None:
        """Test should_send_tool_specs method signature."""
        from nergal.dispatcher.base import ToolDispatcher
        from inspect import signature

        sig = signature(ToolDispatcher.should_send_tool_specs)
        params = list(sig.parameters.keys())

        assert "self" in params
        # Should have no additional parameters besides self
        assert len(params) == 1


class TestParsedToolCallEdgeCases:
    """Edge case tests for ParsedToolCall."""

    def test_empty_name(self) -> None:
        """Test ParsedToolCall with empty name."""
        from nergal.dispatcher.base import ParsedToolCall

        call = ParsedToolCall(
            name="",
            arguments={},
            tool_call_id=None,
        )

        assert call.name == ""

    def test_complex_arguments(self) -> None:
        """Test ParsedToolCall with complex arguments."""
        from nergal.dispatcher.base import ParsedToolCall

        args = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "nested": {"key": "value"},
        }
        call = ParsedToolCall(
            name="test_tool",
            arguments=args,
            tool_call_id="call_456",
        )

        assert call.arguments == args
        assert call.arguments["array"] == [1, 2, 3]
        assert call.arguments["nested"]["key"] == "value"

    def test_special_characters_in_tool_call_id(self) -> None:
        """Test ParsedToolCall with special characters in tool_call_id."""
        from nergal.dispatcher.base import ParsedToolCall

        call = ParsedToolCall(
            name="test_tool",
            arguments={},
            tool_call_id="call_abc123-def_456",
        )

        assert call.tool_call_id == "call_abc123-def_456"

    def test_unicode_in_name(self) -> None:
        """Test ParsedToolCall with Unicode in name."""
        from nergal.dispatcher.base import ParsedToolCall

        call = ParsedToolCall(
            name="тестовый_инструмент",
            arguments={},
            tool_call_id=None,
        )

        assert call.name == "тестовый_инструмент"

    def test_unicode_in_arguments(self) -> None:
        """Test ParsedToolCall with Unicode in arguments."""
        from nergal.dispatcher.base import ParsedToolCall

        call = ParsedToolCall(
            name="test_tool",
            arguments={"message": "Привет мир!"},
            tool_call_id=None,
        )

        assert call.arguments["message"] == "Привет мир!"


class TestGetDispatcher:
    """Tests for get_dispatcher factory function."""

    def test_get_dispatcher_default(self) -> None:
        """Test get_dispatcher with no provider returns XmlToolDispatcher."""
        from nergal.dispatcher.base import get_dispatcher
        from nergal.dispatcher.xml import XmlToolDispatcher

        dispatcher = get_dispatcher()

        assert isinstance(dispatcher, XmlToolDispatcher)

    def test_get_dispatcher_force_xml(self) -> None:
        """Test get_dispatcher with force_xml=True returns XmlToolDispatcher."""
        from nergal.dispatcher.base import get_dispatcher
        from nergal.dispatcher.xml import XmlToolDispatcher

        dispatcher = get_dispatcher(force_xml=True)

        assert isinstance(dispatcher, XmlToolDispatcher)

    def test_get_dispatcher_openai_provider(self) -> None:
        """Test get_detector with OpenAI provider."""
        from nergal.dispatcher.base import get_dispatcher
        from nergal.dispatcher.native import NativeToolDispatcher

        provider = Mock()
        provider.provider_name = "OpenAI"

        dispatcher = get_dispatcher(provider)

        assert isinstance(dispatcher, NativeToolDispatcher)

    def test_get_dispatcher_anthropic_provider(self) -> None:
        """Test get_detector with Anthropic provider."""
        from nergal.dispatcher.base import get_dispatcher
        from nergal.dispatcher.native import NativeToolDispatcher

        provider = Mock()
        provider.provider_name = "Anthropic"

        dispatcher = get_dispatcher(provider)

        assert isinstance(dispatcher, NativeToolDispatcher)

    def test_get_dispatcher_claude_provider(self) -> None:
        """Test get_detector with Claude provider."""
        from nergal.dispatcher.base import get_dispatcher
        from nergal.dispatcher.native import NativeToolDispatcher

        provider = Mock()
        provider.provider_name = "Claude"

        dispatcher = get_dispatcher(provider)

        assert isinstance(dispatcher, NativeToolDispatcher)

    def test_get_dispatcher_unknown_provider(self) -> None:
        """Test get_detector with unknown provider returns XmlToolDispatcher."""
        from nergal.dispatcher.base import get_dispatcher
        from nergal.dispatcher.xml import XmlToolDispatcher

        provider = Mock()
        provider.provider_name = "UnknownProvider"

        dispatcher = get_dispatcher(provider)

        assert isinstance(dispatcher, XmlToolDispatcher)

    def test_get_dispatcher_case_insensitive(self) -> None:
        """Test get_dispatcher is case insensitive for provider names."""
        from nergal.dispatcher.base import get_dispatcher
        from nergal.dispatcher.native import NativeToolDispatcher

        provider = Mock()
        provider.provider_name = "OPENAI"

        dispatcher = get_dispatcher(provider)

        assert isinstance(dispatcher, NativeToolDispatcher)
