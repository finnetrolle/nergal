"""Tool Call Loop implementation.

This module provides the core agentic logic for iteratively
calling LLM and tools until completion.

The tool call loop is the heart of agent behavior:
1. Call LLM with current context
2. Parse response for tool calls
3. If tool calls present:
   a. Execute tools (parallel or sequential)
   b. Format results
   c. Append to context
   d. Repeat from step 1
4. If no tool calls, return response

Example:
    >>> from nergal.agent.loop import run_tool_call_loop
    >>> result = await run_tool_call_loop(
    ...     provider=llm_provider,
    ...     tools=[file_read_tool, shell_tool],
    ...     dispatcher=native_dispatcher,
    ...     max_iterations=10,
    ... )
    >>> print(result)
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from nergal.agent.exceptions import MaxIterationsExceeded
from nergal.dispatcher.base import ParsedToolCall, ToolDispatcher
from nergal.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from nergal.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from nergal.tools.base import ToolResult


logger = logging.getLogger(__name__)


async def run_tool_call_loop(
    provider: BaseLLMProvider,
    tools: list[Tool],
    dispatcher: ToolDispatcher,
    max_iterations: int = 10,
    initial_messages: list[LLMMessage] | None = None,
    parallel_tools: bool = False,
    system_prompt: str | None = None,
) -> str:
    """Run agentic tool call loop until completion or max iterations.

    This is the core agentic loop that coordinates LLM calls and
    tool execution. It iteratively calls the LLM, checks for
    tool calls, executes tools, and feeds results back until the LLM
    provides a final response without tool calls.

    Args:
        provider: LLM provider for generating responses.
        tools: List of available tools.
        dispatcher: Tool dispatcher for parsing/formatting.
        max_iterations: Maximum number of iterations before giving up.
        initial_messages: Optional initial conversation history.
        parallel_tools: If True, execute tools in parallel.
        system_prompt: Optional system prompt for the LLM.

    Returns:
        The final text response from the LLM.

    Raises:
        MaxIterationsExceeded: If max_iterations is exceeded.

    Examples:
        >>> result = await run_tool_call_loop(
        ...     provider=llm_provider,
        ...     tools=[file_read_tool],
        ...     dispatcher=native_dispatcher,
        ...     max_iterations=10,
        ... )
        >>> print(f"Final result: {result}")
    """
    history = initial_messages or []

    # Add system prompt if provided
    if system_prompt:
        history.insert(0, LLMMessage(role=MessageRole.SYSTEM, content=system_prompt))

    for iteration in range(max_iterations):
        logger.debug(f"Tool call loop iteration {iteration + 1}/{max_iterations}")

        # 1. Prepare LLM request
        tool_specs = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                }
            }
            for tool in tools
        ] if dispatcher.should_send_tool_specs() else None

        # 2. Call LLM
        try:
            response = await provider.generate(
                messages=history,
                tools=tool_specs,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

        logger.debug(f"LLM response: {response.content[:100] if response.content else 'None'}...")

        # 3. Parse tool calls
        text, calls = dispatcher.parse_response(response)

        # 4. If no tool calls, return response
        if not calls:
            logger.debug("No tool calls in response, returning result")
            return text or response.content or ""

        # 5. Execute tools
        results = await _execute_tools(tools, calls, parallel=parallel_tools)

        # 6. Format results for next LLM call
        formatted_results = dispatcher.format_results(results)

        # 7. Add LLM response (as assistant) and tool results (as user)
        history.append(LLMMessage(role=MessageRole.ASSISTANT, content=response.content or ""))
        history.append(LLMMessage(role=MessageRole.USER, content=formatted_results))

        logger.debug(f"Executed {len(calls)} tool(s)")

    # Max iterations exceeded
    raise MaxIterationsExceeded(max_iterations)


async def _execute_tools(
    tools: list[Tool],
    calls: list[ParsedToolCall],
    parallel: bool = False,
) -> list[Any]:
    """Execute tools from parsed calls.

    Args:
        tools: List of available tools.
        calls: List of parsed tool calls to execute.
        parallel: If True, execute tools in parallel.

    Returns:
        List of tool execution results.
    """
    if not parallel or len(calls) <= 1:
        # Sequential execution
        results = []
        for call in calls:
            tool = next((t for t in tools if t.name == call.name), None)
            if tool:
                result = await tool.execute(call.arguments)
                results.append(result)
            else:
                logger.warning(f"Tool not found: {call.name}")
                results.append(ToolResult(
                    success=False,
                    output="",
                    error=f"Tool '{call.name}' not found in registry",
                ))
        return results

    # Parallel execution
    tasks = []
    not_found = []  # Track tools not found
    for call in calls:
        tool = next((t for t in tools if t.name == call.name), None)
        if tool:
            task = asyncio.create_task(tool.execute(call.arguments))
            tasks.append((task, call.name))
        else:
            logger.warning(f"Tool not found: {call.name}")
            not_found.append(call.name)

    # Execute all tasks in parallel
    completed, _ = await asyncio.wait(
        [task for task, _ in tasks],
        timeout=None,
    )

    results = []
    for task, name in tasks:
        try:
            result = task.result()
            results.append(result)
        except Exception as e:
            logger.error(f"Tool {name} execution failed: {e}")
            results.append(ToolResult(
                success=False,
                output="",
                error=str(e),
            ))

    # Add results for tools not found
    for name in not_found:
        results.append(ToolResult(
            success=False,
            output="",
            error=f"Tool '{name}' not found in registry",
        ))

    return results


def format_llm_request(
    messages: list[LLMMessage],
    tools: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """Format messages for LLM API request.

    Args:
        messages: List of conversation messages.
        tools: Optional list of tool specifications.

    Returns:
        List of formatted message dictionaries.
    """
    return [msg.to_dict() for msg in messages]
