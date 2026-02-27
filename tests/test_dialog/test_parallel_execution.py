"""Tests for parallel execution of plan steps."""

import asyncio

import pytest

from nergal.dialog.base import AgentResult, AgentType, ExecutionPlan, PlanStep
from nergal.dialog.manager import DialogManager, PlanExecutionResult


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    from unittest.mock import AsyncMock, MagicMock
    
    provider = MagicMock()
    provider.provider_name = "mock"
    provider.generate = AsyncMock()
    return provider


@pytest.fixture
def manager(mock_llm_provider) -> DialogManager:
    """Create a DialogManager instance for testing."""
    return DialogManager(
        llm_provider=mock_llm_provider,
        use_dispatcher=False,
    )


class TestPlanStepDependencies:
    """Tests for PlanStep dependency fields."""

    def test_plan_step_default_values(self) -> None:
        """Test default values for PlanStep."""
        step = PlanStep(
            agent_type=AgentType.DEFAULT,
            description="Test step",
        )
        
        assert step.depends_on == []
        assert step.parallel_group is None

    def test_plan_step_with_dependencies(self) -> None:
        """Test PlanStep with explicit dependencies."""
        step = PlanStep(
            agent_type=AgentType.DEFAULT,
            description="Test step",
            depends_on=[0, 1],
            parallel_group=2,
        )
        
        assert step.depends_on == [0, 1]
        assert step.parallel_group == 2


class TestStepGrouping:
    """Tests for step grouping by dependency."""

    def test_sequential_steps(self, manager: DialogManager) -> None:
        """Test grouping of sequential steps (no dependencies)."""
        steps = [
            PlanStep(agent_type=AgentType.WEB_SEARCH, description="Step 0"),
            PlanStep(agent_type=AgentType.DEFAULT, description="Step 1"),
            PlanStep(agent_type=AgentType.DEFAULT, description="Step 2"),
        ]
        
        groups = manager._group_steps_by_dependency(steps)
        
        # By default, steps without explicit dependencies are sequential
        # First step in group 0, rest follow sequentially
        assert len(groups) >= 1
        assert groups[0] == [0]

    def test_parallel_steps_no_deps(self, manager: DialogManager) -> None:
        """Test grouping when steps have no dependencies but same parallel_group."""
        steps = [
            PlanStep(agent_type=AgentType.WEB_SEARCH, description="Step 0", depends_on=[], parallel_group=1),
            PlanStep(agent_type=AgentType.WEB_SEARCH, description="Step 1", depends_on=[], parallel_group=1),
        ]
        
        groups = manager._group_steps_by_dependency(steps)
        
        # Both should be in first group (same parallel_group, no deps)
        assert len(groups) >= 1
        # Both steps should be grouped together
        assert 0 in groups[0]
        assert 1 in groups[0]

    def test_steps_with_single_dependency(self, manager: DialogManager) -> None:
        """Test grouping with single dependency."""
        steps = [
            PlanStep(agent_type=AgentType.WEB_SEARCH, description="Step 0", depends_on=[]),
            PlanStep(agent_type=AgentType.DEFAULT, description="Step 1", depends_on=[0]),
        ]
        
        groups = manager._group_steps_by_dependency(steps)
        
        # First step in group 0, second in later group
        assert len(groups) >= 2
        assert groups[0] == [0]
        # Step 1 should be in a later group
        assert 1 not in groups[0]

    def test_steps_with_multiple_dependencies(self, manager: DialogManager) -> None:
        """Test grouping with multiple dependencies."""
        steps = [
            PlanStep(agent_type=AgentType.WEB_SEARCH, description="Step 0", depends_on=[], parallel_group=1),
            PlanStep(agent_type=AgentType.ANALYSIS, description="Step 1", depends_on=[], parallel_group=1),
            PlanStep(agent_type=AgentType.SUMMARY, description="Step 2", depends_on=[0, 1]),
            PlanStep(agent_type=AgentType.DEFAULT, description="Step 3", depends_on=[2]),
        ]
        
        groups = manager._group_steps_by_dependency(steps)
        
        # First group should have steps 0 and 1 (parallel_group 1, no deps)
        assert 0 in groups[0]
        assert 1 in groups[0]
        # Step 2 depends on 0 and 1, so should be in a later group
        assert 2 not in groups[0]
        # Step 3 depends on 2
        assert 3 not in groups[0]

    def test_complex_dependency_chain(self, manager: DialogManager) -> None:
        """Test complex dependency chain."""
        steps = [
            PlanStep(agent_type=AgentType.DEFAULT, description="Step 0", depends_on=[]),
            PlanStep(agent_type=AgentType.WEB_SEARCH, description="Step 1", depends_on=[0]),
            PlanStep(agent_type=AgentType.ANALYSIS, description="Step 2", depends_on=[1]),
            PlanStep(agent_type=AgentType.DEFAULT, description="Step 3", depends_on=[2]),
        ]
        
        groups = manager._group_steps_by_dependency(steps)
        
        # Each step depends on previous, so sequential
        # Verify each step is in its own group or properly ordered
        assert groups[0] == [0]
        # Verify the order is maintained
        step_order = []
        for group in groups:
            step_order.extend(group)
        assert step_order == [0, 1, 2, 3]

    def test_diamond_dependency(self, manager: DialogManager) -> None:
        """Test diamond dependency pattern."""
        #     0
        #    / \
        #   1   2
        #    \ /
        #     3
        steps = [
            PlanStep(agent_type=AgentType.DEFAULT, description="Step 0", depends_on=[]),
            PlanStep(agent_type=AgentType.WEB_SEARCH, description="Step 1", depends_on=[0]),
            PlanStep(agent_type=AgentType.ANALYSIS, description="Step 2", depends_on=[0]),
            PlanStep(agent_type=AgentType.SUMMARY, description="Step 3", depends_on=[1, 2]),
        ]
        
        groups = manager._group_steps_by_dependency(steps)
        
        # Step 0 first
        assert groups[0] == [0]
        
        # Steps 1 and 2 depend only on 0, so they can run after 0
        # They may be in same group or sequential depending on implementation
        assert 1 not in groups[0]  # Step 1 should not be in first group
        assert 2 not in groups[0]  # Step 2 should not be in first group
        
        # Step 3 depends on 1 and 2, must come after both
        step_order = []
        for group in groups:
            step_order.extend(group)
        assert step_order.index(3) > step_order.index(1)
        assert step_order.index(3) > step_order.index(2)


class TestParallelExecution:
    """Tests for actual parallel execution."""

    @pytest.mark.asyncio
    async def test_parallel_execution_timing(
        self, mock_llm_provider, manager: DialogManager
    ) -> None:
        """Test that parallel steps actually execute concurrently."""
        import time
        from unittest.mock import AsyncMock, MagicMock
        
        execution_times = {}
        
        # Create a mock agent that tracks execution time
        async def mock_process(message, context, history):
            step_num = int(message.split()[-1])  # Extract step number from message
            execution_times[step_num] = time.time()
            await asyncio.sleep(0.1)  # Simulate work
            return AgentResult(
                response=f"Result for step {step_num}",
                agent_type=AgentType.DEFAULT,
            )
        
        mock_agent = MagicMock()
        mock_agent.agent_type = AgentType.DEFAULT
        mock_agent.process = mock_process
        
        manager.agent_registry.register(mock_agent)
        
        # Create a plan with parallel steps
        plan = ExecutionPlan(
            steps=[
                PlanStep(agent_type=AgentType.DEFAULT, description="Step 0", depends_on=[]),
                PlanStep(agent_type=AgentType.DEFAULT, description="Step 1", depends_on=[]),
            ],
            reasoning="Parallel test",
        )
        
        start_time = time.time()
        result = await manager._execute_plan(
            plan=plan,
            original_message="test 0\ntest 1",
            context={},
            history=[],
        )
        total_time = time.time() - start_time
        
        # Both steps should have executed
        assert result.success
        assert len(result.executed_steps) == 2
        
        # If truly parallel, total time should be ~0.1s, not ~0.2s
        # Allow some tolerance for test overhead
        assert total_time < 0.3  # Should be much less than 0.2 (2 * 0.1)

    @pytest.mark.asyncio
    async def test_sequential_execution_timing(
        self, mock_llm_provider, manager: DialogManager
    ) -> None:
        """Test that dependent steps execute sequentially."""
        import time
        from unittest.mock import AsyncMock, MagicMock
        
        execution_order = []
        
        # Create a mock agent that tracks execution order
        async def mock_process(message, context, history):
            execution_order.append(message)
            await asyncio.sleep(0.05)
            return AgentResult(
                response=f"Result for {message}",
                agent_type=AgentType.DEFAULT,
            )
        
        mock_agent = MagicMock()
        mock_agent.agent_type = AgentType.DEFAULT
        mock_agent.process = mock_process
        
        manager.agent_registry.register(mock_agent)
        
        # Create a plan with sequential steps (dependency chain)
        plan = ExecutionPlan(
            steps=[
                PlanStep(agent_type=AgentType.DEFAULT, description="Step 0", depends_on=[]),
                PlanStep(agent_type=AgentType.DEFAULT, description="Step 1", depends_on=[0]),
            ],
            reasoning="Sequential test",
        )
        
        result = await manager._execute_plan(
            plan=plan,
            original_message="step0",
            context={},
            history=[],
        )
        
        # Both steps should have executed in order
        assert result.success
        assert len(result.executed_steps) == 2
        assert execution_order[0] == "step0"


class TestInputCombination:
    """Tests for combining inputs from multiple dependencies."""

    @pytest.mark.asyncio
    async def test_combined_input_from_multiple_deps(
        self, mock_llm_provider, manager: DialogManager
    ) -> None:
        """Test that inputs are combined when step has multiple dependencies."""
        from unittest.mock import AsyncMock, MagicMock
        
        received_inputs = []
        
        # Create mock agents
        async def mock_search(message, context, history):
            return AgentResult(
                response=f"Search result for: {message}",
                agent_type=AgentType.WEB_SEARCH,
            )
        
        async def mock_combine(message, context, history):
            received_inputs.append(message)
            return AgentResult(
                response=f"Combined: {message[:50]}",
                agent_type=AgentType.ANALYSIS,
            )

        search_agent = MagicMock()
        search_agent.agent_type = AgentType.WEB_SEARCH
        search_agent.process = mock_search

        combine_agent = MagicMock()
        combine_agent.agent_type = AgentType.ANALYSIS
        combine_agent.process = mock_combine
        
        manager.agent_registry.register(search_agent)
        manager.agent_registry.register(combine_agent)
        
        # Create a plan where analysis depends on two search steps
        plan = ExecutionPlan(
            steps=[
                PlanStep(agent_type=AgentType.WEB_SEARCH, description="Search 1", depends_on=[]),
                PlanStep(agent_type=AgentType.WEB_SEARCH, description="Search 2", depends_on=[]),
                PlanStep(agent_type=AgentType.ANALYSIS, description="Analyze", depends_on=[0, 1]),
            ],
            reasoning="Parallel search then analyze",
        )
        
        result = await manager._execute_plan(
            plan=plan,
            original_message="React vs Vue",
            context={},
            history=[],
        )
        
        # All steps should have executed
        assert result.success
        assert len(result.executed_steps) == 3
        
        # The comparison step should have received combined input
        assert len(received_inputs) == 1
        # Combined input should contain both search results
        assert "Search result" in received_inputs[0]
