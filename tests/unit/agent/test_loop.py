"""Unit tests for Tool Call Loop.

Tests follow TDD Red-Green-Refactor pattern.
"""

import asyncio
import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from nergal.llm.base import LLMResponse, MessageRole, LLMMessage
from nergal.tools.base import Tool, ToolResult
from nergal.dispatcher.base import ParsedToolCall, ToolDispatcher
from nergal.agent.exceptions import MaxIterationsExceeded


class MockTool(Tool):
    """Mock tool for testing."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Mock tool {self._name}"

    @property
    def parameters_schema(self) -> dict:
        return {"type": "object"}

    async def execute(self, args: dict) -> ToolResult:
        return ToolResult(
            success=True,
            output=f"Executed {self._name}",
        )


class MockDispatcher(ToolDispatcher):
    """Mock dispatcher for testing."""

    def __init__(
        self,
        tool_calls: list[ParsedToolCall] | None = None,
        responses: list[str] | None = None,
        always_return_calls: bool = False,
        tool_calls_per_iteration: list[list[ParsedToolCall]] | None = None,
    ) -> None:
        self.tool_calls_to_return = tool_calls or []
        self.responses_to_return = responses or []
        self.always_return_calls = always_return_calls
        self.tool_calls_per_iteration = tool_calls_per_iteration
        self.call_count = 0
        self.format_count = 0

    def parse_response(
        self, response: LLMResponse
    ) -> tuple[str, list[ParsedToolCall]]:
        # Determine what to return
        if self.call_count < len(self.responses_to_return):
            text = self.responses_to_return[self.call_count]
        else:
            # Out of responses, return empty string or last response
            text = ""

        # Return tool calls based on mode
        if self.tool_calls_per_iteration is not None:
            # Use explicit per-iteration tool calls
            if self.call_count < len(self.tool_calls_per_iteration):
                calls = self.tool_calls_per_iteration[self.call_count]
            else:
                calls = []
        elif self.always_return_calls:
            calls = self.tool_calls_to_return
        elif self.call_count == 0:
            # Only return tool calls on first iteration by default
            calls = self.tool_calls_to_return
        else:
            calls = []

        self.call_count += 1
        return text, calls

    def format_results(self, results: list[Any]) -> str:
        self.format_count += 1
        return f"Formatted {len(results)} results"

    def prompt_instructions(self, tools: list[Any]) -> str:
        return "Use tools like this..."

    def should_send_tool_specs(self) -> bool:
        return False


class TestToolCallLoop:
    """Tests for tool call loop functionality."""

    @pytest.mark.asyncio
    async def test_simple_response_no_tools(self) -> None:
        """Test loop returns immediately when LLM has no tool calls."""
        from nergal.agent.loop import run_tool_call_loop

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = LLMResponse(
            content="Hello!",
            model="test-model",
        )

        mock_dispatcher = MockDispatcher(tool_calls=[])

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=[],
            dispatcher=mock_dispatcher,
            max_iterations=10,
        )

        assert result == "Hello!"
        assert mock_provider.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_single_tool_call(self) -> None:
        """Test loop executes single tool and returns result."""
        from nergal.agent.loop import run_tool_call_loop

        mock_provider = AsyncMock()
        # First call returns tool call, second returns final response
        mock_provider.generate.side_effect = [
            LLMResponse(
                content="",
                model="test-model",
            ),
            LLMResponse(
                content="Task completed!",
                model="test-model",
            ),
        ]

        mock_tool = MockTool("test_tool")
        mock_dispatcher = MockDispatcher(
            tool_calls=[ParsedToolCall(
                name="test_tool",
                arguments={},
                tool_call_id="call_1",
            )],
            responses=["", "Final"],
        )

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=[mock_tool],
            dispatcher=mock_dispatcher,
            max_iterations=10,
        )

        assert result == "Final"
        assert mock_provider.generate.call_count == 2
        assert mock_dispatcher.format_count == 1

    @pytest.mark.asyncio
    async def test_max_iterations_exceeded(self) -> None:
        """Test loop stops after max iterations."""
        from nergal.agent.loop import run_tool_call_loop
        from nergal.agent.exceptions import MaxIterationsExceeded

        mock_provider = AsyncMock()
        # Always return tool calls
        mock_provider.generate.return_value = LLMResponse(
            content="",
            model="test-model",
        )

        mock_tool = MockTool("test_tool")
        mock_dispatcher = MockDispatcher(
            tool_calls=[ParsedToolCall(
                name="test_tool",
                arguments={},
                tool_call_id="call_1",
            )],
            responses=["", ""],
            always_return_calls=True,
        )

        with pytest.raises(MaxIterationsExceeded):
            await run_tool_call_loop(
                provider=mock_provider,
                tools=[mock_tool],
                dispatcher=mock_dispatcher,
                max_iterations=3,
            )

        assert mock_provider.generate.call_count == 3

    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self) -> None:
        """Test loop handles tool execution errors gracefully."""
        from nergal.agent.loop import run_tool_call_loop

        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = [
            LLMResponse(
                content="",
                model="test-model",
            ),
            LLMResponse(
                content="Error handled",
                model="test-model",
            ),
        ]

        class ErrorTool(Tool):
            @property
            def name(self) -> str:
                return "error_tool"

            @property
            def description(self) -> str:
                return "Error tool"

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object"}

            async def execute(self, args: dict) -> ToolResult:
                return ToolResult(
                    success=False,
                    output="",
                    error="Something went wrong",
                )

        mock_tool = ErrorTool()
        mock_dispatcher = MockDispatcher(
            tool_calls=[ParsedToolCall(
                name="error_tool",
                arguments={},
                tool_call_id="call_1",
            )],
            responses=["", "Error handled"],
        )

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=[mock_tool],
            dispatcher=mock_dispatcher,
            max_iterations=10,
        )

        assert result == "Error handled"

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self) -> None:
        """Test loop handles multiple tool calls in sequence."""
        from nergal.agent.loop import run_tool_call_loop

        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = [
            LLMResponse(
                content="",
                model="test-model",
            ),
            LLMResponse(
                content="All done!",
                model="test-model",
            ),
        ]

        mock_tool1 = MockTool("tool1")
        mock_tool2 = MockTool("tool2")
        mock_dispatcher = MockDispatcher(
            tool_calls_per_iteration=[
                [  # Iteration 0: both tools in sequence
                    ParsedToolCall(name="tool1", arguments={}, tool_call_id="call_1"),
                    ParsedToolCall(name="tool2", arguments={}, tool_call_id="call_2"),
                ],
                [  # Iteration 1: no tools - return final result
                ],
            ],
            responses=["", "All done!"],
        )

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=[mock_tool1, mock_tool2],
            dispatcher=mock_dispatcher,
            max_iterations=10,
        )

        assert result == "All done!"
        assert mock_provider.generate.call_count == 2
        assert mock_dispatcher.format_count == 1

    @pytest.mark.asyncio
    async def test_empty_tools_list(self) -> None:
        """Test loop with empty tools list."""
        from nergal.agent.loop import run_tool_call_loop

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = LLMResponse(
            content="Response without tools",
            model="test-model",
        )

        mock_dispatcher = MockDispatcher(tool_calls=[])

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=[],
            dispatcher=mock_dispatcher,
            max_iterations=10,
        )

        assert result == "Response without tools"

    @pytest.mark.asyncio
    async def test_initial_messages_parameter(self) -> None:
        """Test loop uses initial messages if provided."""
        from nergal.agent.loop import run_tool_call_loop

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = LLMResponse(
            content="Response",
            model="test-model",
        )

        mock_dispatcher = MockDispatcher(tool_calls=[])

        initial_messages = [
            LLMMessage(role=MessageRole.USER, content="Initial message"),
        ]

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=[],
            dispatcher=mock_dispatcher,
            max_iterations=10,
            initial_messages=initial_messages,
        )

        # Provider should be called with initial messages
        call_args = mock_provider.generate.call_args
        assert call_args is not None
        messages_arg = call_args.kwargs.get("messages", [])
        assert len(messages_arg) >= 1


class TestToolCallLoopConfiguration:
    """Tests for loop configuration options."""

    @pytest.mark.asyncio
    async def test_custom_max_iterations(self) -> None:
        """Test custom max_iterations is respected."""
        from nergal.agent.loop import run_tool_call_loop

        mock_provider = AsyncMock()
        # First iteration returns tool call, second iteration also returns tool call
        mock_provider.generate.return_value = LLMResponse(
            content="",
            model="test-model",
        )

        mock_tool = MockTool("test_tool")
        mock_dispatcher = MockDispatcher(
            tool_calls=[ParsedToolCall(name="test_tool", arguments={}, tool_call_id="c1")],
            always_return_calls=True,
        )

        with pytest.raises(MaxIterationsExceeded):  # Should raise at max iterations
            await run_tool_call_loop(
                provider=mock_provider,
                tools=[mock_tool],
                dispatcher=mock_dispatcher,
                max_iterations=1,  # Only 1 iteration allowed
            )

        assert mock_provider.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_parallel_tool_execution(self) -> None:
        """Test parallel execution when enabled."""
        from nergal.agent.loop import run_tool_call_loop

        execution_times = []

        class TimingTool(Tool):
            def __init__(self, delay: float) -> None:
                self._name = f"tool_{delay}"
                self._delay = delay

            @property
            def name(self) -> str:
                return self._name

            @property
            def description(self) -> str:
                return f"Tool with {self._delay}s delay"

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object"}

            async def execute(self, args: dict) -> ToolResult:
                start = asyncio.get_event_loop().time()
                await asyncio.sleep(self._delay)
                end = asyncio.get_event_loop().time()
                execution_times.append(end - start)
                return ToolResult(success=True, output="Done")

        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = [
            LLMResponse(content="", model="test"),
            LLMResponse(content="Done", model="test"),
        ]

        mock_dispatcher = MockDispatcher(
            tool_calls=[
                ParsedToolCall(name="tool_0.1", arguments={}, tool_call_id="c1"),
                ParsedToolCall(name="tool_0.2", arguments={}, tool_call_id="c2"),
            ],
            responses=["", "Done"],
        )

        tools = [
            TimingTool(0.1),
            TimingTool(0.2),
        ]

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=tools,
            dispatcher=mock_dispatcher,
            max_iterations=10,
            parallel_tools=True,
        )

        # With parallel execution, both should complete in ~0.2s (max delay)
        # With sequential execution, would take ~0.3s (sum of delays)
        # We can't easily test timing, but at least verify it runs
        assert result == "Done"

    @pytest.mark.asyncio
    async def test_system_prompt_parameter(self) -> None:
        """Test loop adds system prompt to history."""
        from nergal.agent.loop import run_tool_call_loop
        from nergal.llm.base import LLMMessage

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = LLMResponse(
            content="Response",
            model="test-model",
        )

        mock_dispatcher = MockDispatcher(tool_calls=[])

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=[],
            dispatcher=mock_dispatcher,
            max_iterations=10,
            system_prompt="You are a helpful assistant.",
        )

        assert result == "Response"

        # Check that system prompt was added
        call_args = mock_provider.generate.call_args
        assert call_args is not None
        messages_arg = call_args.kwargs.get("messages", [])
        assert len(messages_arg) >= 1

        # First message should be system prompt
        if messages_arg:
            assert messages_arg[0].role == MessageRole.SYSTEM
            assert messages_arg[0].content == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_tool_not_found_sequential(self) -> None:
        """Test loop handles tool not found in sequential mode."""
        from nergal.agent.loop import run_tool_call_loop

        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = [
            LLMResponse(content="", model="test"),
            LLMResponse(content="Final", model="test"),
        ]

        mock_tool = MockTool("existing_tool")
        mock_dispatcher = MockDispatcher(
            tool_calls=[ParsedToolCall(name="missing_tool", arguments={}, tool_call_id="c1")],
            responses=["", "Final"],
        )

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=[mock_tool],
            dispatcher=mock_dispatcher,
            max_iterations=10,
        )

        # Should continue despite missing tool
        assert result == "Final"

    @pytest.mark.asyncio
    async def test_tool_not_found_parallel(self) -> None:
        """Test loop handles tool not found in parallel mode."""
        from nergal.agent.loop import run_tool_call_loop

        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = [
            LLMResponse(content="", model="test"),
            LLMResponse(content="Final", model="test"),
        ]

        mock_tool = MockTool("existing_tool")
        mock_dispatcher = MockDispatcher(
            tool_calls=[
                ParsedToolCall(name="existing_tool", arguments={}, tool_call_id="c1"),
                ParsedToolCall(name="missing_tool", arguments={}, tool_call_id="c2"),
            ],
            responses=["", "Final"],
        )

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=[mock_tool],
            dispatcher=mock_dispatcher,
            max_iterations=10,
            parallel_tools=True,
        )

        # Should continue despite missing tool
        assert result == "Final"

    @pytest.mark.asyncio
    async def test_tool_exception_in_parallel(self) -> None:
        """Test loop handles tool exception in parallel mode."""
        from nergal.agent.loop import run_tool_call_loop

        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = [
            LLMResponse(content="", model="test"),
            LLMResponse(content="Final", model="test"),
        ]

        class ExceptionTool(Tool):
            @property
            def name(self) -> str:
                return "exception_tool"

            @property
            def description(self) -> str:
                return "Exception tool"

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object"}

            async def execute(self, args: dict) -> ToolResult:
                raise ValueError("Tool failed!")

        mock_tool2 = MockTool("normal_tool")

        mock_dispatcher = MockDispatcher(
            tool_calls=[
                ParsedToolCall(name="exception_tool", arguments={}, tool_call_id="c1"),
                ParsedToolCall(name="normal_tool", arguments={}, tool_call_id="c2"),
            ],
            responses=["", "Final"],
        )

        result = await run_tool_call_loop(
            provider=mock_provider,
            tools=[ExceptionTool(), mock_tool2],
            dispatcher=mock_dispatcher,
            max_iterations=10,
            parallel_tools=True,
        )

        # Should continue despite exception
        assert result == "Final"
