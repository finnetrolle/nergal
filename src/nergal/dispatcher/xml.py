"""XML tool dispatcher for text-only LLM providers.

This dispatcher handles tool calls from LLM providers that don't
support native tool calling (Ollama, local models, etc.).

Tool calls are embedded in the response text using XML-style tags
that need to be parsed out.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from nergal.dispatcher.base import ParsedToolCall, ToolDispatcher
from nergal.llm.base import LLMResponse
from nergal.tools.base import ToolResult

logger = logging.getLogger(__name__)

# Regex pattern for matching XML-style tool calls
# Pattern: <tool_name>arg1="value1" arg2="value2"</tool_name>
# or <tool_name>{"key": "value"}</tool_name>
TOOL_CALL_PATTERN = re.compile(
    r'<(?P<name>\w+)(?:\s+[^>]*)?>\s*(?P<content>.*?)\s*</\1>',
    re.DOTALL
)


class XmlToolDispatcher(ToolDispatcher):
    """Dispatcher for LLM providers without native tool support.

    XML tool dispatchers work with text-only providers like Ollama
    or local models. Tool calls are embedded in the response using
    XML-style tags that need to be parsed.

    Supported formats:
    1. XML attributes: <tool_name arg1="value1" arg2="value2"></tool_name>
    2. JSON content: <tool_name>{"arg1": "value1"}</tool_name>

    Examples:
        >>> dispatcher = XmlToolDispatcher()
        >>> text, calls = dispatcher.parse_response(llm_response)
        >>> formatted = dispatcher.format_results(tool_results)
        >>> instructions = dispatcher.prompt_tools(tools)
    """

    def __init__(self, tool_tags: list[str] | None = None) -> None:
        """Initialize the XML tool dispatcher.

        Args:
            tool_tags: Optional list of valid tool tag names to accept.
                      If None, all tool-like tags are accepted.
        """
        self.tool_tags = set(tool_tags) if tool_tags else None

    def parse_response(
        self, response: LLMResponse
    ) -> tuple[str, list[ParsedToolCall]]:
        """Parse LLM response to extract text and tool calls.

        For XML dispatchers, tool calls are embedded in the text
        using XML-style tags.

        Args:
            response: The LLMResponse to parse.

        Returns:
            A tuple of (text, tool_calls):
                - text: The text portion with tool calls removed
                - tool_calls: List of parsed tool calls
        """
        content = response.content or ""
        calls: list[ParsedToolCall] = []

        # Find all tool call tags
        for match in TOOL_CALL_PATTERN.finditer(content):
            try:
                name = match.group("name")
                inner_content = match.group("content")

                # Skip if tool_tags is set and name not in allowed list
                if self.tool_tags and name not in self.tool_tags:
                    continue

                # Try to parse as JSON first, then as attributes
                arguments = self._parse_tool_arguments(inner_content)

                calls.append(ParsedToolCall(
                    name=name,
                    arguments=arguments,
                    tool_call_id=None,  # XML dispatchers don't have IDs
                ))
            except Exception as e:
                logger.error(f"Failed to parse tool call from XML: {e}")
                continue

        # Remove tool calls from text for cleaner output
        clean_text = TOOL_CALL_PATTERN.sub("", content).strip()

        logger.debug(f"Parsed {len(calls)} tool call(s) from XML response")

        return clean_text, calls

    def format_results(self, results: list[Any]) -> str:
        """Format tool execution results for next LLM call.

        For XML dispatchers, results are formatted using XML tags
        that the LLM can recognize.

        Args:
            results: List of tool execution results.

        Returns:
            A formatted string containing the tool results.
        """
        if not results:
            return ""

        formatted_parts = []

        for i, result in enumerate(results):
            if not isinstance(result, ToolResult):
                logger.warning(f"Unexpected result type: {type(result)}")
                continue

            # Format with XML tags
            if result.success:
                output_escaped = result.output.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                formatted_parts.append(f"<tool_result index=\"{i}\">{output_escaped}</tool_result>")
            else:
                error_escaped = (result.error or "Unknown error").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                formatted_parts.append(f"<tool_error index=\"{i}\">{error_escaped}</tool_error>")

        return "\n\n".join(formatted_parts)

    def prompt_instructions(self, tools: list[Any]) -> str:
        """Generate prompt instructions for using tools.

        For XML dispatchers, we need to tell the LLM how to format
        tool calls in its response.

        Args:
            tools: List of available tools.

        Returns:
            A string with instructions for using tools via XML tags.
        """
        instructions = [
            "\n\n## Available Tools\n",
            "You can use the following tools to help complete tasks:",
        ]

        for tool in tools:
            tool_name = getattr(tool, "name", "unknown")
            tool_desc = getattr(tool, "description", "No description")
            instructions.append(f"\n**{tool_name}**: {tool_desc}")

        instructions.extend([
            "\n\n## Tool Usage",
            "To use a tool, format your tool call as follows:",
            "\n```xml",
            "<tool_name>",
            '  {"key": "value"}',
            "</tool_name>",
            "```",
            "\nOr with XML attributes:",
            "\n```xml",
            '<tool_name key="value" />',
            "```",
            "\nTool results will be returned as:",
            "\n```xml",
            '<tool_result index="0">Result output</tool_result>',
            "```",
        ])

        return "\n".join(instructions)

    def should_send_tool_specs(self) -> bool:
        """Check if tool specifications should be sent to LLM.

        XML dispatchers don't send tool specs to the LLM API since
        the LLM doesn't support native tools.

        Returns:
            False - don't send tool specs to LLM API.
        """
        return False

    def _parse_tool_arguments(self, content: str) -> dict[str, Any]:
        """Parse tool arguments from XML tag content.

        Tries JSON first, then falls back to XML attribute parsing.

        Args:
            content: The inner content of the tool call tag.

        Returns:
            Dictionary of parsed arguments.
        """
        content = content.strip()

        # Try JSON first
        if content.startswith("{") or content.startswith("["):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass  # Fall through to attribute parsing

        # Try XML attribute format: key="value" key2="value2"
        attr_pattern = re.compile(r'(\w+)=(["\'])(.*?)\2')
        arguments = {}
        for match in attr_pattern.finditer(content):
            key = match.group(1)
            value = match.group(3)
            arguments[key] = value

        # If no attributes found, treat entire content as a single value
        if not arguments and content:
            arguments = {"value": content}

        return arguments

    def set_allowed_tools(self, tool_names: list[str]) -> None:
        """Set the list of allowed tool tag names.

        Args:
            tool_names: List of tool names to accept.
        """
        self.tool_tags = set(tool_names)

    def clear_allowed_tools(self) -> None:
        """Clear the list of allowed tool tag names.

        After calling this, any tool-like tag will be parsed.
        """
        self.tool_tags = None
