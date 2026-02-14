"""Dialog manager for handling user conversations.

This module provides the main DialogManager class that coordinates
between agents, manages context, and handles logging.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nergal.dialog.agents import (
    AgentRegistry,
    AgentResult,
    AgentType,
    BaseAgent,
    ExecutionPlan,
    PlanStep,
)
from nergal.dialog.context import ContextManager, DialogContext, UserInfo
from nergal.dialog.default_agent import DefaultAgent
from nergal.dialog.dispatcher_agent import DispatcherAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """Result of processing a user message."""

    response: str
    agent_type: AgentType
    confidence: float
    session_id: str
    processing_time_ms: float
    metadata: dict[str, Any]


@dataclass
class PlanExecutionResult:
    """Result of executing an execution plan."""

    success: bool
    final_response: str
    executed_steps: list[dict[str, Any]] = field(default_factory=list)
    skipped_steps: list[dict[str, Any]] = field(default_factory=list)
    missing_agents: list[str] = field(default_factory=list)
    missing_agents_reason: dict[str, str] = field(default_factory=dict)
    error: str | None = None


class DialogManager:
    """Main class for managing dialogs with users.

    This class coordinates between agents, manages conversation context,
    and provides logging for all dialog operations.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        max_history: int = 20,
        max_contexts: int = 1000,
        style_type: StyleType = StyleType.DEFAULT,
        use_dispatcher: bool = True,
    ) -> None:
        """Initialize the dialog manager.

        Args:
            llm_provider: LLM provider for generating responses.
            max_history: Maximum messages to keep in conversation history.
            max_contexts: Maximum number of user contexts to maintain.
            style_type: Response style to use for agents.
            use_dispatcher: Whether to use dispatcher for agent routing.
        """
        self.llm_provider = llm_provider
        self.agent_registry = AgentRegistry()
        self.context_manager = ContextManager(max_contexts=max_contexts)
        self._style_type = style_type
        self._use_dispatcher = use_dispatcher

        # Initialize dispatcher agent (will be configured with registry after agents are registered)
        self._dispatcher: DispatcherAgent | None = None
        if use_dispatcher:
            self._dispatcher = DispatcherAgent(llm_provider, style_type)

        # Register default agent
        self._register_default_agents()

        # Configure dispatcher with agent registry
        if self._dispatcher:
            self._dispatcher.set_agent_registry(self.agent_registry)

        logger.info(
            f"DialogManager initialized with provider: {llm_provider.provider_name}, "
            f"style: {style_type.value}, dispatcher: {use_dispatcher}"
        )

    def _register_default_agents(self) -> None:
        """Register the default set of agents."""
        default_agent = DefaultAgent(self.llm_provider, style_type=self._style_type)
        self.agent_registry.register(default_agent)
        logger.debug(f"Registered agent: {default_agent.agent_type}")

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a custom agent.

        Args:
            agent: Agent instance to register.
        """
        self.agent_registry.register(agent)
        logger.info(f"Registered custom agent: {agent.agent_type}")

    def get_or_create_context(
        self,
        user_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        language_code: str | None = None,
    ) -> DialogContext:
        """Get or create a dialog context for a user.

        Args:
            user_id: Telegram user ID.
            first_name: User's first name.
            last_name: User's last name.
            username: User's username.
            language_code: User's language code.

        Returns:
            DialogContext for the user.
        """
        return self.context_manager.get_or_create(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
        )

    async def process_message(
        self,
        user_id: int,
        message: str,
        user_info: dict[str, Any] | None = None,
    ) -> ProcessResult:
        """Process a user message and generate a response.

        This is the main entry point for handling user messages. It:
        1. Gets or creates a dialog context
        2. Creates an execution plan (if dispatcher is enabled)
        3. Executes the plan step by step
        4. Updates the context
        5. Logs the interaction

        Args:
            user_id: Telegram user ID.
            message: User's message text.
            user_info: Optional dict with user information
                      (first_name, last_name, username, language_code).

        Returns:
            ProcessResult containing the response and metadata.
        """
        start_time = datetime.utcnow()

        # Extract user info
        info = user_info or {}
        context = self.get_or_create_context(
            user_id=user_id,
            first_name=info.get("first_name"),
            last_name=info.get("last_name"),
            username=info.get("username"),
            language_code=info.get("language_code"),
        )

        # Log incoming message
        logger.info(
            f"Processing message from {context.user_info.display_name} "
            f"(ID: {user_id}): {message[:100]}..."
        )

        try:
            # Get context data for agent selection
            agent_context = context.get_context_for_agent()

            # Add user message to history
            context.add_user_message(message)

            # Get history for LLM
            history = context.get_history_for_llm()

            # Execute with plan or fallback to single agent
            if self._dispatcher:
                plan = await self._dispatcher.create_plan(message, agent_context)
                plan_result = await self._execute_plan(plan, message, agent_context, history)
                final_response = plan_result.final_response
                final_agent_type = AgentType.DISPATCHER
                confidence = 1.0

                # Log missing agents warning
                if plan_result.missing_agents:
                    logger.warning(
                        f"Missing agents for optimal plan execution: "
                        f"{', '.join(plan_result.missing_agents)}. "
                        f"Consider adding them to the system."
                    )
            else:
                # Fallback to single agent selection
                agent = await self.agent_registry.determine_agent(message, agent_context)
                logger.debug(f"Selected agent: {agent.agent_type}")

                context.set_current_agent(agent.agent_type.value)
                result = await agent.process(message, agent_context, history)
                final_response = result.response
                final_agent_type = result.agent_type
                confidence = result.confidence

            # Add assistant response to history
            context.add_assistant_message(final_response)

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Log successful processing
            logger.info(
                f"Processed message for {context.user_info.display_name} "
                f"(time: {processing_time:.0f}ms)"
            )

            return ProcessResult(
                response=final_response,
                agent_type=final_agent_type,
                confidence=confidence,
                session_id=context.session_id,
                processing_time_ms=processing_time,
                metadata={"plan_used": self._use_dispatcher},
            )

        except Exception as e:
            # Log error
            logger.error(
                f"Error processing message for {context.user_info.display_name}: {e}",
                exc_info=True,
            )

            # Return error response
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ProcessResult(
                response="Извините, произошла ошибка при обработке вашего сообщения. Попробуйте позже.",
                agent_type=AgentType.DEFAULT,
                confidence=0.0,
                session_id=context.session_id,
                processing_time_ms=processing_time,
                metadata={"error": str(e)},
            )

    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        original_message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> PlanExecutionResult:
        """Execute an execution plan step by step.

        Args:
            plan: The execution plan to execute.
            original_message: The original user message.
            context: Current dialog context.
            history: Message history for LLM.

        Returns:
            PlanExecutionResult with the final response and execution details.
        """
        result = PlanExecutionResult(
            success=False,
            final_response="",
            missing_agents=[a.value for a in plan.missing_agents],
            missing_agents_reason=plan.missing_agents_reason,
        )

        current_input = original_message
        accumulated_context = dict(context)

        for step in plan.steps:
            agent = self.agent_registry.get(step.agent_type)

            if agent is None:
                # Agent not available
                step_info = {
                    "agent": step.agent_type.value,
                    "description": step.description,
                    "status": "skipped",
                    "reason": "agent_not_available",
                }

                if step.is_optional:
                    result.skipped_steps.append(step_info)
                    logger.debug(f"Skipped optional step: {step.agent_type.value}")
                    continue
                else:
                    # Try to use default agent as fallback
                    default_agent = self.agent_registry.get(AgentType.DEFAULT)
                    if default_agent:
                        logger.warning(
                            f"Required agent {step.agent_type.value} not available, "
                            f"using default agent as fallback"
                        )
                        agent = default_agent
                        step_info["fallback"] = True
                    else:
                        result.skipped_steps.append(step_info)
                        result.error = f"Required agent {step.agent_type.value} not available"
                        return result

            try:
                # Prepare input for this step
                if step.input_transform == "previous" and result.executed_steps:
                    # Use output from previous step
                    prev_output = result.executed_steps[-1].get("response", current_input)
                    step_input = prev_output
                else:
                    step_input = current_input

                # Execute the step
                logger.debug(f"Executing step: {step.agent_type.value} - {step.description}")
                step_result = await agent.process(step_input, accumulated_context, history)

                # Record the step execution
                result.executed_steps.append({
                    "agent": step.agent_type.value,
                    "description": step.description,
                    "status": "success",
                    "confidence": step_result.confidence,
                    "response_preview": step_result.response[:200] if step_result.response else "",
                })

                # Update context with step result for next agent
                accumulated_context["previous_step_output"] = step_result.response
                accumulated_context["previous_agent"] = step.agent_type.value

                # Pass metadata from this step to subsequent agents
                if step_result.metadata:
                    # Store search results specifically for easy access
                    if "search_results" in step_result.metadata:
                        accumulated_context["search_results"] = step_result.metadata["search_results"]
                        accumulated_context["search_queries"] = step_result.metadata.get("search_queries", [])
                        accumulated_context["sources"] = step_result.metadata.get("sources", [])
                    # Also store full metadata for any other data
                    accumulated_context["previous_step_metadata"] = step_result.metadata

                # For the final response, use the last agent's output
                result.final_response = step_result.response
                result.success = True

            except Exception as e:
                logger.error(f"Error executing step {step.agent_type.value}: {e}")
                result.executed_steps.append({
                    "agent": step.agent_type.value,
                    "description": step.description,
                    "status": "error",
                    "error": str(e),
                })

                if not step.is_optional:
                    result.error = f"Step {step.agent_type.value} failed: {e}"
                    # Provide a user-friendly error message instead of empty response
                    result.final_response = (
                        "Извините, произошла ошибка при обработке вашего запроса. "
                        "Попробуйте позже или переформулируйте вопрос."
                    )
                    result.success = False
                    return result

        return result

    async def process_with_context(
        self,
        context: DialogContext,
        message: str,
    ) -> ProcessResult:
        """Process a message with an existing context.

        Args:
            context: Existing dialog context.
            message: User's message text.

        Returns:
            ProcessResult containing the response and metadata.
        """
        user_info = {
            "first_name": context.user_info.first_name,
            "last_name": context.user_info.last_name,
            "username": context.user_info.username,
            "language_code": context.user_info.language_code,
        }
        return await self.process_message(
            user_id=context.user_info.user_id,
            message=message,
            user_info=user_info,
        )

    def clear_user_context(self, user_id: int) -> bool:
        """Clear the dialog context for a user.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if context was cleared, False if not found.
        """
        result = self.context_manager.remove(user_id)
        if result:
            logger.info(f"Cleared context for user {user_id}")
        return result

    def get_context_stats(self) -> dict[str, Any]:
        """Get statistics about current contexts.

        Returns:
            Dictionary with context statistics.
        """
        return {
            "active_contexts": self.context_manager.context_count,
            "registered_agents": len(self.agent_registry.get_all()),
            "llm_provider": self.llm_provider.provider_name,
            "dispatcher_enabled": self._use_dispatcher,
        }
