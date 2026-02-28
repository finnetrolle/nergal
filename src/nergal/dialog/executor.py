"""Agent executor with timeout and cancellation support.

This module provides an executor for running agents with timeout
and cancellation capabilities.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.cancellation import (
    AgentCancelledError,
    CancellationToken,
)
from nergal.llm import LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class TimeoutSettings:
    """Settings for agent execution timeouts.

    Attributes:
        default_timeout: Default timeout in seconds for all agents.
        web_search_timeout: Timeout for web search agent.
        news_timeout: Timeout for news agent.
        default_agent_timeout: Timeout for default/conversation agent.
    """

    default_timeout: float = 30.0
    web_search_timeout: float = 45.0
    news_timeout: float = 40.0
    default_agent_timeout: float = 30.0

    def get_timeout_for_agent(self, agent_type: AgentType) -> float:
        """Get timeout for a specific agent type.

        Args:
            agent_type: The agent type to get timeout for.

        Returns:
            Timeout in seconds.
        """
        timeouts = {
            AgentType.WEB_SEARCH: self.web_search_timeout,
            AgentType.DEFAULT: self.default_agent_timeout,
        }
        return timeouts.get(agent_type, self.default_timeout)


@dataclass
class ExecutionResult:
    """Result of agent execution with metadata.

    Attributes:
        result: The agent result if successful.
        success: Whether execution was successful.
        timed_out: Whether the execution timed out.
        cancelled: Whether the execution was cancelled.
        error_message: Error message if execution failed.
        execution_time_ms: Time taken for execution in milliseconds.
        timeout_seconds: The timeout that was used.
    """

    result: AgentResult | None = None
    success: bool = True
    timed_out: bool = False
    cancelled: bool = False
    error_message: str | None = None
    execution_time_ms: float = 0.0
    timeout_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "success": self.success,
            "timed_out": self.timed_out,
            "cancelled": self.cancelled,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "timeout_seconds": self.timeout_seconds,
        }


class AgentExecutor:
    """Executor for running agents with timeout and cancellation support.

    This class provides methods to execute agents with configurable
    timeouts and cancellation tokens for graceful shutdown.
    """

    def __init__(
        self,
        timeout_settings: TimeoutSettings | None = None,
        fallback_response: str = "Извините, запрос занял слишком много времени. Попробуйте упростить вопрос.",
    ) -> None:
        """Initialize the executor.

        Args:
            timeout_settings: Settings for agent timeouts.
            fallback_response: Response to return on timeout/cancellation.
        """
        self._timeout_settings = timeout_settings or TimeoutSettings()
        self._fallback_response = fallback_response

    @property
    def timeout_settings(self) -> TimeoutSettings:
        """Get the timeout settings."""
        return self._timeout_settings

    async def execute(
        self,
        agent: BaseAgent,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
        timeout: float | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> ExecutionResult:
        """Execute an agent with optional timeout and cancellation.

        Args:
            agent: The agent to execute.
            message: The message to process.
            context: Execution context.
            history: Message history.
            timeout: Optional timeout override (seconds).
            cancellation_token: Optional cancellation token.

        Returns:
            ExecutionResult with the agent result or error info.
        """
        start_time = time.time()

        # Determine timeout
        effective_timeout = timeout or self._timeout_settings.get_timeout_for_agent(
            agent.agent_type
        )

        try:
            # Check for cancellation before starting
            if cancellation_token and cancellation_token.is_cancelled:
                return ExecutionResult(
                    success=False,
                    cancelled=True,
                    error_message=cancellation_token.cancel_reason or "Cancelled before execution",
                    execution_time_ms=0,
                    timeout_seconds=effective_timeout,
                )

            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_with_cancellation(
                    agent, message, context, history, cancellation_token
                ),
                timeout=effective_timeout,
            )

            execution_time_ms = (time.time() - start_time) * 1000

            return ExecutionResult(
                result=result,
                success=True,
                execution_time_ms=execution_time_ms,
                timeout_seconds=effective_timeout,
            )

        except TimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"Agent {agent.agent_type.value} timed out after {effective_timeout}s"
            )

            return ExecutionResult(
                result=self._create_fallback_result(agent.agent_type, "timeout"),
                success=False,
                timed_out=True,
                error_message=f"Execution timed out after {effective_timeout}s",
                execution_time_ms=execution_time_ms,
                timeout_seconds=effective_timeout,
            )

        except AgentCancelledError as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.info(f"Agent {agent.agent_type.value} execution cancelled: {e.message}")

            return ExecutionResult(
                result=self._create_fallback_result(agent.agent_type, "cancelled"),
                success=False,
                cancelled=True,
                error_message=e.message,
                execution_time_ms=execution_time_ms,
                timeout_seconds=effective_timeout,
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Agent {agent.agent_type.value} execution failed: {e}")

            return ExecutionResult(
                result=self._create_fallback_result(agent.agent_type, "error"),
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time_ms,
                timeout_seconds=effective_timeout,
            )

    async def _execute_with_cancellation(
        self,
        agent: BaseAgent,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
        cancellation_token: CancellationToken | None,
    ) -> AgentResult:
        """Execute agent with periodic cancellation checks.

        Args:
            agent: The agent to execute.
            message: The message to process.
            context: Execution context.
            history: Message history.
            cancellation_token: Optional cancellation token.

        Returns:
            AgentResult from the agent.

        Raises:
            AgentCancelledError: If cancellation is requested during execution.
        """
        # Check cancellation before starting
        if cancellation_token:
            cancellation_token.check_cancelled()

        # Execute the agent
        # Note: The actual agent execution doesn't support interruption,
        # so we can only check cancellation before/after
        result = await agent.process(message, context, history)

        # Check cancellation after completion
        if cancellation_token:
            cancellation_token.check_cancelled()

        return result

    def _create_fallback_result(
        self, agent_type: AgentType, reason: str
    ) -> AgentResult:
        """Create a fallback result for failed executions.

        Args:
            agent_type: The agent type that failed.
            reason: Reason for the fallback.

        Returns:
            AgentResult with fallback response.
        """
        return AgentResult(
            response=self._fallback_response,
            agent_type=agent_type,
            confidence=0.0,
            metadata={
                "fallback": True,
                "reason": reason,
            },
        )

    async def execute_plan_step(
        self,
        agent: BaseAgent,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
        cancellation_token: CancellationToken | None = None,
    ) -> AgentResult:
        """Execute a plan step with default timeout for the agent type.

        This is a convenience method that returns an AgentResult directly,
        using fallback responses for failures.

        Args:
            agent: The agent to execute.
            message: The message to process.
            context: Execution context.
            history: Message history.
            cancellation_token: Optional cancellation token.

        Returns:
            AgentResult (either from agent or fallback).
        """
        result = await self.execute(
            agent=agent,
            message=message,
            context=context,
            history=history,
            cancellation_token=cancellation_token,
        )

        # Return the result (either successful or fallback)
        if result.result is not None:
            return result.result

        # This shouldn't happen, but provide a safe fallback
        return self._create_fallback_result(agent.agent_type, "unknown_error")
