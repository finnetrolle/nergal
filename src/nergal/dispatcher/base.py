"""Base classes and interfaces for Tool Dispatcher system.

This module provides the core abstractions for the dispatcher system,
including the ToolDispatcher interface and ParsedToolCall dataclass.

The dispatcher is responsible for:
1. Parsing LLM responses to extract tool calls
2. Formatting tool execution results for the next LLM call
3. Generating prompt instructions for tool usage

Example:
    >>> from nergal.dispatcher.base import ToolDispatcher
    >>> from nergal.tools import Tool
    >>>
    >>> class MyDispatcher(ToolDispatcher):
    ...     def parse_response(self, response):
    ...         # Parse LLM response
    ...         pass
    ...
    ...     def format_results(self, results):
    ...         # Format tool results
    ...         pass
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nergal.llm.base import LLMResponse

if TYPE_CHECKING:
    from nergal.llm.base import BaseLLMProvider


@dataclass
class ParsedToolCall:
    """Represents a parsed tool call from LLM response.

    This dataclass holds the information extracted from an LLM's
    tool call, including the tool name, arguments, and
    optional tool call ID (for native tool support).

    Attributes:
        name: The name of the tool to execute.
        arguments: Dictionary of arguments for the tool.
        tool_call_id: Optional ID for native tool calls.
                      None for XML-style tool calls.

    Examples:
        >>> call = ParsedToolCall(
        ...     name="file_read",
        ...     arguments={"path": "/tmp/file.txt"},
        ...     tool_call_id="call_123"
        ... )
    """

    name: str
    """The name of the tool to execute."""

    arguments: dict[str, Any]
    """Dictionary of arguments for the tool."""

    tool_call_id: str | None = None
    """Optional ID for native tool calls. None for XML-style calls."""


class ToolDispatcher(ABC):
    """Abstract base class for tool dispatchers.

    ToolDispatcher bridges the gap between LLM responses and
    tool execution. Different LLM providers have different
    formats for tool calls:

    - Native: Structured tool calls with IDs (OpenAI, Anthropic)
    - XML: Tool calls embedded in text tags (Ollama, custom)

    Implementations must handle their specific format.

    Required methods:
        - parse_response: Extract text and tool calls from LLM response
        - format_results: Format tool results for next LLM call
        - prompt_instructions: Generate instructions for using tools
        - should_send_tool_specs: Whether to send tool schemas to LLM

    Examples:
        >>> dispatcher = NativeToolDispatcher()
        >>> text, calls = dispatcher.parse_response(llm_response)
        >>> formatted = dispatcher.format_results(execution_results)
    """

    @abstractmethod
    def parse_response(self, response: LLMResponse) -> tuple[str, list[ParsedToolCall]]:
        """Parse LLM response to extract text and tool calls.

        This method processes the LLM response and separates:
        1. The text response (if any)
        2. Any tool calls the LLM made

        Args:
            response: The LLMResponse to parse.

        Returns:
            A tuple of (text, tool_calls):
                - text: The text portion of the response (may be empty)
                - tool_calls: List of parsed tool calls (may be empty)

        Examples:
            >>> text, calls = dispatcher.parse_response(llm_response)
            >>> if calls:
            ...     for call in calls:
            ...         print(f"Tool: {call.name}")
        """
        pass

    @abstractmethod
    def format_results(self, results: list[Any]) -> str:
        """Format tool execution results for next LLM call.

        This method takes the results of executing tools and formats
        them in a way that the LLM can understand. The format
        depends on the dispatcher type (native vs XML).

        Args:
            results: List of tool execution results. The exact type
                     depends on the dispatcher implementation.

        Returns:
            A formatted string containing the tool results.

        Examples:
            >>> formatted = dispatcher.format_results(tool_results)
            >>> # Returns something like:
            >>> # "Tool returned: <tool_result name='file_read'>..."
        """
        pass

    @abstractmethod
    def prompt_instructions(self, tools: list[Any]) -> str:
        """Generate prompt instructions for using tools.

        This method creates instructions that tell the LLM how and
        when to use the available tools. For native tool dispatchers,
        this may return an empty string since tool schemas are sent
        directly. For XML dispatchers, this returns detailed
        formatting instructions.

        Args:
            tools: List of available tools.

        Returns:
            A string with instructions for using tools.

        Examples:
            >>> instructions = dispatcher.prompt_tools(tools)
            >>> # Returns something like:
            >>> # "To use a tool, wrap a JSON object in <call> tags..."
        """
        pass

    @abstractmethod
    def should_send_tool_specs(self) -> bool:
        """Check if tool specifications should be sent to LLM.

        Native tool dispatchers (OpenAI, Anthropic) typically
        send tool specifications directly to the LLM API. XML
        dispatchers (Ollama, text-only models) need to include
        tool information in the prompt itself.

        Returns:
            True if tool specs should be sent to LLM API, False otherwise.

        Examples:
            >>> if dispatcher.should_send_tool_specs():
            ...     # Send tool specs in API call
            ...     pass
            >>> else:
            ...     # Include tool info in prompt
            ...     prompt += dispatcher.prompt_instructions(tools)
        """
        pass


def get_dispatcher(
    provider: BaseLLMProvider | None = None,
    force_xml: bool = False,
) -> ToolDispatcher:
    """Get the appropriate dispatcher for the given provider.

    This factory function automatically detects which dispatcher to use
    based on the LLM provider's capabilities. If force_xml is True,
    the XML dispatcher will be used regardless of provider capabilities.

    Providers with native tool support (OpenAI, Anthropic) will use
    NativeToolDispatcher. Text-only providers (Ollama, local models)
    will use XmlToolDispatcher.

    Args:
        provider: The LLM provider instance. If None, defaults to
                  NativeToolDispatcher (best practice is to provide
                  the provider for accurate detection).
        force_xml: If True, force use of XmlToolDispatcher.

    Returns:
        The appropriate ToolDispatcher instance.

    Examples:
        >>> from nergal.dispatcher.base import get_dispatcher
        >>> from nergal.llm.providers import ZaiProvider
        >>>
        >>> provider = ZaiProvider(api_key="key", model="model")
        >>> dispatcher = get_dispatcher(provider)

        Force XML dispatcher:
        >>> dispatcher = get_dispatcher(force_xml=True)
    """
    if force_xml:
        from nergal.dispatcher.xml import XmlToolDispatcher

        return XmlToolDispatcher()

    # Try to detect based on provider
    if provider is not None:
        provider_name = provider.provider_name.lower()

        # Providers known to support native tool calls
        native_providers = {
            "openai",
            "anthropic",
            "claude",
        }

        if provider_name in native_providers:
            from nergal.dispatcher.native import NativeToolDispatcher

            return NativeToolDispatcher()

    # Default to XML dispatcher for unknown providers
    from nergal.dispatcher.xml import XmlToolDispatcher

    return XmlToolDispatcher()
