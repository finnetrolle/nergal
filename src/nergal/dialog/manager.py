"""Dialog manager for handling user conversations.

This module provides the main DialogManager class that coordinates
between agents, manages context, and handles logging.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from nergal.dialog.base import (
    AgentRegistry,
    AgentResult,
    AgentType,
    BaseAgent,
    ExecutionPlan,
    PlanStep,
    StepResult,
)
from nergal.dialog.cache import AgentResultCache
from nergal.dialog.context import ContextManager, DialogContext, ExecutionContext
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
        cache: AgentResultCache | None = None,
    ) -> None:
        """Initialize the dialog manager.

        Args:
            llm_provider: LLM provider for generating responses.
            max_history: Maximum messages to keep in conversation history.
            max_contexts: Maximum number of user contexts to maintain.
            style_type: Response style to use for agents.
            use_dispatcher: Whether to use dispatcher for agent routing.
            cache: Optional cache for agent results.
        """
        self.llm_provider = llm_provider
        self.agent_registry = AgentRegistry()
        self.context_manager = ContextManager(max_contexts=max_contexts)
        self._style_type = style_type
        self._use_dispatcher = use_dispatcher

        # Agent result cache
        self._cache = cache

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
            f"style: {style_type.value}, dispatcher: {use_dispatcher}, "
            f"cache_enabled: {cache is not None and cache.enabled}"
        )

    def set_cache(self, cache: AgentResultCache) -> None:
        """Set the cache for agent results.

        Args:
            cache: AgentResultCache instance.
        """
        self._cache = cache
        logger.info(f"Cache configured for DialogManager (enabled: {cache.enabled})")

    def get_cache_stats(self) -> dict[str, Any] | None:
        """Get cache statistics.

        Returns:
            Cache statistics dict or None if cache is not configured.
        """
        if self._cache is None:
            return None
        stats = self._cache.get_stats()
        return {
            "hits": stats.hits,
            "misses": stats.misses,
            "evictions": stats.evictions,
            "size": stats.size,
            "max_size": stats.max_size,
            "hit_rate": stats.hit_rate,
        }

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
        start_time = datetime.now(UTC)

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
            total_tokens_used = 0
            if self._dispatcher:
                plan = await self._dispatcher.create_plan(message, agent_context)
                plan_result = await self._execute_plan(plan, message, agent_context, history)
                final_response = plan_result.final_response
                final_agent_type = AgentType.DISPATCHER
                confidence = 1.0
                # Sum tokens from all executed steps
                for step in plan_result.executed_steps:
                    total_tokens_used += step.get("tokens_used", 0) or 0

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
                total_tokens_used = result.tokens_used or 0

            # Add assistant response to history
            context.add_assistant_message(final_response)

            # Calculate processing time
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

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
                metadata={
                    "plan_used": self._use_dispatcher,
                },
            )

        except Exception as e:
            # Log error
            logger.error(
                f"Error processing message for {context.user_info.display_name}: {e}",
                exc_info=True,
            )

            # Return error response
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
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
        """Execute an execution plan with parallel execution support.

        This method supports two execution modes:
        1. Sequential: Steps are executed one after another (default)
        2. Parallel: Independent steps (depends_on=None) are executed concurrently

        The execution strategy:
        - Group steps by dependency level
        - Execute independent steps in parallel using asyncio.gather
        - Aggregate results before executing dependent steps

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

        # Create execution context for sharing data between agents
        exec_context = ExecutionContext(
            original_message=original_message,
            user_context=dict(context),
        )

        accumulated_context = dict(context)
        step_results: dict[int, AgentResult] = {}  # step_index -> result

        # Identify execution groups (steps that can run in parallel)
        execution_groups = self._group_steps_by_dependency(plan.steps)
        
        logger.debug(f"Execution plan has {len(plan.steps)} steps in {len(execution_groups)} groups")
        for i, step in enumerate(plan.steps):
            logger.debug(f"  Step {i}: {step.agent_type.value} - {step.description}")

        for group in execution_groups:
            if len(group) == 1:
                # Single step - execute normally
                step_idx = group[0]
                step = plan.steps[step_idx]
                step_result = await self._execute_single_step(
                    step=step,
                    step_index=step_idx,
                    original_message=original_message,
                    accumulated_context=accumulated_context,
                    step_results=step_results,
                    history=history,
                    result=result,
                    exec_context=exec_context,
                )
                if step_result:
                    step_results[step_idx] = step_result
                    self._update_context_from_result(accumulated_context, step, step_result)
                    
            else:
                # Multiple independent steps - execute in parallel
                logger.debug(f"Executing {len(group)} steps in parallel: {group}")
                
                # Create a copy of context for each parallel task to avoid race conditions
                # Each parallel step gets its own context copy to prevent concurrent modifications
                tasks = [
                    self._execute_single_step(
                        step=plan.steps[idx],
                        step_index=idx,
                        original_message=original_message,
                        accumulated_context=dict(accumulated_context),  # Copy context for each task
                        step_results=step_results,
                        history=history,
                        result=result,
                        exec_context=exec_context,
                    )
                    for idx in group
                ]
                
                # Execute all tasks concurrently
                parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for idx, step_result in zip(group, parallel_results):
                    if isinstance(step_result, Exception):
                        logger.error(f"Parallel step {idx} failed: {step_result}")
                        # Error already logged in _execute_single_step
                    elif step_result:
                        step_results[idx] = step_result
                        self._update_context_from_result(
                            accumulated_context, plan.steps[idx], step_result
                        )

        # Determine final response from the last executed step
        if step_results:
            last_idx = max(step_results.keys())
            result.final_response = step_results[last_idx].response
            result.success = True
            logger.info(f"Plan execution complete: {len(step_results)} steps executed, final step: {last_idx}")
        else:
            logger.warning("Plan execution complete but no steps were executed!")

        return result

    def _group_steps_by_dependency(self, steps: list[PlanStep]) -> list[list[int]]:
        """Group steps by their dependency level for parallel execution.

        Steps are grouped based on their dependencies:
        - Steps with no dependencies can run in the first group
        - Steps with satisfied dependencies can run in subsequent groups
        - Steps in the same parallel_group are executed together

        This ensures proper context passing between agents (e.g., web_search results
        are available to default agent).

        Args:
            steps: List of PlanStep objects.

        Returns:
            List of groups, where each group contains step indices that can run in parallel.
        """
        groups: list[list[int]] = []
        assigned: set[int] = set()

        # First, group steps by parallel_group if specified
        parallel_groups: dict[int, list[int]] = {}
        for i, step in enumerate(steps):
            if step.parallel_group is not None:
                if step.parallel_group not in parallel_groups:
                    parallel_groups[step.parallel_group] = []
                parallel_groups[step.parallel_group].append(i)

        # Find steps with no dependencies (can start immediately)
        initial_steps = []
        for i, step in enumerate(steps):
            if not step.depends_on:  # Empty list means no dependencies
                initial_steps.append(i)

        # If we have parallel_group members with no dependencies, group them
        if parallel_groups:
            # Process parallel groups first
            used_parallel_groups: set[int] = set()
            for step_idx in initial_steps:
                step = steps[step_idx]
                if step.parallel_group is not None and step.parallel_group not in used_parallel_groups:
                    # Add all steps in this parallel group that have no dependencies
                    group_members = []
                    for member_idx in parallel_groups[step.parallel_group]:
                        if not steps[member_idx].depends_on:
                            group_members.append(member_idx)
                            assigned.add(member_idx)
                    if group_members:
                        groups.append(group_members)
                        used_parallel_groups.add(step.parallel_group)
                    continue
                elif step.parallel_group is None and step_idx not in assigned:
                    # Standalone step with no dependencies
                    groups.append([step_idx])
                    assigned.add(step_idx)
        else:
            # No parallel groups, use simple dependency-based grouping
            for step_idx in initial_steps:
                groups.append([step_idx])
                assigned.add(step_idx)

        # If no steps were assigned (all have dependencies), start with first step
        if not assigned and steps:
            groups.append([0])
            assigned.add(0)

        # Subsequent groups: steps whose dependencies are satisfied
        max_iterations = len(steps) * 2  # Prevent infinite loops
        iteration = 0
        while len(assigned) < len(steps) and iteration < max_iterations:
            iteration += 1
            next_group = []
            
            for i, step in enumerate(steps):
                if i in assigned:
                    continue
                    
                # A step can run if all its dependencies are satisfied
                if step.depends_on:
                    # Check if all dependencies are satisfied
                    if all(dep in assigned for dep in step.depends_on):
                        next_group.append(i)
                        assigned.add(i)
                else:
                    # No explicit dependencies - can run if previous step is done (sequential default)
                    # But only if not already in a parallel group
                    if step.parallel_group is None and (i - 1) in assigned:
                        next_group.append(i)
                        assigned.add(i)
                    elif step.parallel_group is not None:
                        # Check if all parallel group members' dependencies are satisfied
                        can_run = True
                        for member_idx in parallel_groups.get(step.parallel_group, []):
                            for dep in steps[member_idx].depends_on:
                                if dep not in assigned:
                                    can_run = False
                                    break
                            if not can_run:
                                break
                        if can_run:
                            # Add all members of this parallel group
                            for member_idx in parallel_groups.get(step.parallel_group, []):
                                if member_idx not in assigned:
                                    next_group.append(member_idx)
                                    assigned.add(member_idx)
            
            if not next_group:
                # No progress - add remaining steps sequentially
                remaining = [i for i in range(len(steps)) if i not in assigned]
                for i in remaining:
                    groups.append([i])
                    assigned.add(i)
                break
            
            if next_group:
                groups.append(next_group)

        return groups

    async def _execute_single_step(
        self,
        step: PlanStep,
        step_index: int,
        original_message: str,
        accumulated_context: dict[str, Any],
        step_results: dict[int, AgentResult],
        history: list[LLMMessage],
        result: PlanExecutionResult,
        exec_context: ExecutionContext | None = None,
    ) -> AgentResult | None:
        """Execute a single plan step.

        Args:
            step: The PlanStep to execute.
            step_index: Index of this step in the plan.
            original_message: The original user message.
            accumulated_context: Context accumulated from previous steps.
            step_results: Results from previously executed steps.
            history: Message history for LLM.
            result: PlanExecutionResult to update with execution info.
            exec_context: Optional ExecutionContext for sharing data between agents.

        Returns:
            AgentResult if successful, None otherwise.
        """
        agent = self.agent_registry.get(step.agent_type)
        start_time = time.time()

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
                return None
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
                    return None

        try:
            # Prepare input for this step
            if step.input_transform == "previous" and step_results:
                # Use output from previous step
                prev_idx = max(step_results.keys())
                step_input = step_results[prev_idx].response
            elif step.depends_on:
                # Use output from the steps this depends on (combine if multiple)
                if len(step.depends_on) == 1:
                    # Single dependency
                    dep_idx = step.depends_on[0]
                    if dep_idx in step_results:
                        step_input = step_results[dep_idx].response
                    else:
                        step_input = original_message
                else:
                    # Multiple dependencies - combine outputs
                    combined_inputs = []
                    for dep_idx in step.depends_on:
                        if dep_idx in step_results:
                            combined_inputs.append(step_results[dep_idx].response)
                    if combined_inputs:
                        step_input = "\n\n".join(combined_inputs)
                    else:
                        step_input = original_message
            else:
                step_input = original_message

            # Check cache before executing
            step_result = None
            cache_hit = False
            if self._cache is not None:
                step_result = self._cache.get(step.agent_type, step_input)
                if step_result is not None:
                    cache_hit = True
                    logger.info(
                        f"Cache hit for step: {step.agent_type.value} - {step.description}"
                    )

            # Execute the step if not in cache
            if step_result is None:
                logger.info(f"Executing step: {step.agent_type.value} - {step.description}")
                logger.debug(f"Step input: {step_input[:100]}..." if len(step_input) > 100 else f"Step input: {step_input}")
                logger.debug(f"Context has search_results: {'search_results' in accumulated_context}")
                
                # Add execution context to accumulated context if available
                if exec_context is not None:
                    accumulated_context["exec_context"] = exec_context
                
                step_result = await agent.process(step_input, accumulated_context, history)

                # Store result in cache
                if self._cache is not None:
                    self._cache.set(step.agent_type, step_input, step_result)
                    logger.debug(f"Cached result for step: {step.agent_type.value}")

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # Create StepResult and add to ExecutionContext
            if exec_context is not None:
                step_result_obj = StepResult(
                    step_index=step_index,
                    agent_type=step.agent_type,
                    output=step_result.response,
                    structured_data=step_result.metadata,
                    confidence=step_result.confidence,
                    execution_time_ms=execution_time_ms,
                    success=True,
                )
                exec_context.add_result(step_result_obj)

            # Record the step execution
            result.executed_steps.append({
                "agent": step.agent_type.value,
                "description": step.description,
                "status": "success",
                "confidence": step_result.confidence,
                "response_preview": step_result.response[:200] if step_result.response else "",
                "tokens_used": step_result.tokens_used,
                "cache_hit": cache_hit,
                "execution_time_ms": execution_time_ms,
            })

            return step_result

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Error executing step {step.agent_type.value}: {e}")
            
            # Create failed StepResult
            if exec_context is not None:
                failed_result = StepResult(
                    step_index=step_index,
                    agent_type=step.agent_type,
                    output="",
                    structured_data={},
                    confidence=0.0,
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error_message=str(e),
                )
                exec_context.add_result(failed_result)
            
            result.executed_steps.append({
                "agent": step.agent_type.value,
                "description": step.description,
                "status": "error",
                "error": str(e),
                "execution_time_ms": execution_time_ms,
            })

            if not step.is_optional:
                result.error = f"Step {step.agent_type.value} failed: {e}"
                result.final_response = (
                    "Извините, произошла ошибка при обработке вашего запроса. "
                    "Попробуйте позже или переформулируйте вопрос."
                )
                result.success = False

            return None

    def _update_context_from_result(
        self,
        accumulated_context: dict[str, Any],
        step: PlanStep,
        step_result: AgentResult,
    ) -> None:
        """Update accumulated context from a step result.

        Args:
            accumulated_context: Context to update.
            step: The step that was executed.
            step_result: Result from the step execution.
        """
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
                logger.info(
                    f"Stored search results for next agent: "
                    f"{len(step_result.metadata['search_results'])} chars, "
                    f"queries: {step_result.metadata.get('search_queries', [])}"
                )
            # Also store full metadata for any other data
            accumulated_context["previous_step_metadata"] = step_result.metadata

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
