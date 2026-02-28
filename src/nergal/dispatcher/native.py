"""Native tool dispatcher for providers with built-in tool support.

This dispatcher handles tool calls from LLM providers that support
native tool calling (OpenAI, Anthropic, etc.).

These providers return tool calls in a structured format with IDs,
allowing for proper response formatting and result tracking.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from nergal.dispatcher.base import ParsedToolCall, ToolDispatcher
from nergal.llm.base import LLMResponse
from nergal.tools.base import ToolResult

logger = logging.getLogger(__name__)


class NativeToolDispatcher(ToolDispatcher):
    """Dispatcher for LLM providers with native tool support.

    Native tool dispatchers work with providers like OpenAI and Anthropic
    that return tool calls in a structured format with unique IDs.

    Tool call format (OpenAI-style):
    {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "file_read",
            "arguments": '{"path": "/tmp/file.txt"}'
        }
    }

    Examples:
        >>> dispatcher = NativeToolDispatcher()
        >>> text, calls = dispatcher.parse_response(llm_response)
        >>> formatted = dispatcher.format_results(tool_results)
    """

    def parse_response(
        self, response: LLMResponse
    ) -> tuple[str, list[ParsedToolCall]]:
        """Parse LLM response to extract text and tool calls.

        For native providers, tool calls are in the tool_calls field.
        Text content may be mixed with tool calls.

        Args:
            response: The LLMResponse to parse.

        Returns:
            A tuple of (text, tool_calls):
                - text: The text portion of the response
                - tool_calls: List of parsed tool calls
        """
        text = response.content or ""
        calls: list[ParsedToolCall] = []

        if not response.tool_calls:
            return text, calls

        # Parse tool calls from native format
        for tool_call in response.tool_calls:
            try:
                call_data = self._parse_native_tool_call(tool_call)
                if call_data:
                    calls.append(call_data)
            except Exception as e:
                logger.error(f"Failed to parse tool call: {e}")
                continue

        logger.debug(f"Parsed {len(calls)} tool call(s) from native response")

        return text, calls

    def format_results(self, results: list[Any]) -> str:
        """Format tool execution results for next LLM call.

        For native tool calls, results are formatted as tool responses
        that can be sent back to the LLM.

        Args:
            results: List of tool execution results.

        Returns:
            A formatted string containing the tool results.
        """
        if not results:
            return ""

        formatted_parts = []

        for result in results:
            if not isinstance(result, ToolResult):
                logger.warning(f"Unexpected result type: {type(result)}")
                continue

            # Format based on success/failure
            if result.success:
                formatted_parts.append(f"Tool result: {result.output}")
            else:
                error_msg = result.error or "Unknown error"
                formatted_parts.append(f"Tool error: {error_msg}")

        return "\n\n".join(formatted_parts)

    def prompt_instructions(self, tools: list[Any]) -> str:
        """Generate prompt instructions for using tools.

        For native dispatchers, tool schemas are sent directly to the
        LLM API, so we don't need detailed instructions in the prompt.

        Args:
            tools: List of available tools.

        Returns:
            Empty string (instructions not needed for native tools).
        """
        return ""

    def should_send_tool_specs(self) -> bool:
        """Check if tool specifications should be sent to LLM.

        Native providers expect tool specifications in the API call.

        Returns:
            True - send tool specs to LLM API.
        """
        return True

    def _parse_native_tool_call(self, tool_call: dict[str, Any]) -> ParsedToolCall | None:
        """Parse a single native tool call.

        Handles different provider formats (OpenAI, Anthropic, etc.).

        Args:
            tool_call: Raw tool call data from LLM.

        Returns:
            ParsedToolCall if successful, None otherwise.
        """
        # OpenAI-style format
        if "function" in tool_call:
            return self._parse_openai_style(tool_call)

        # Anthropic-style format
        if "input" in tool_call and "name" in tool_call:
            return self._parse_anthropic_style(tool_call)

        # Generic fallback
        logger.warning(f"Unknown tool call format: {tool_call}")
        return None

    def _parse_openai_style(self, tool_call: dict[str, Any]) -> ParsedToolCall:
        """Parse OpenAI-style tool call.

        Format:
        {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "tool_name",
                "arguments": '{"key": "value"}'
            }
        }

        Args:
            tool_call: OpenAI-style tool call.

        Returns:
            ParsedToolCall with extracted data.
        """
        tool_call_id = tool_call.get("id")
        function = tool_call.get("function", {})

        name = function.get("name", "")
        arguments_str = function.get("arguments", "{}")

        # Parse JSON arguments
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tool arguments: {e}")
            arguments = {}

        return ParsedToolCall(
            name=name,
            arguments=arguments,
            tool_call_id=tool_call_id,
        )

    def _parse_anthropic_style(self, tool_call: dict[str, Any]) -> ParsedToolCall:
        """Parse Anthropic-style tool call.

        Format:
        {
            "id": "toolu_abc123",
            "name": "tool_name",
            "input": {"key": "value"}
        }

        Args:
            tool_call: Anthropic-style tool call.

        Returns:
            ParsedToolCall with extracted data.
        """
        tool_call_id = tool_call.get("id")
        name = tool_call.get("name", "")
        arguments = tool_call.get("input", {})

        return ParsedToolCall(
            name=name,
            arguments=arguments,
            tool_call_id=tool_call_id,
        )
