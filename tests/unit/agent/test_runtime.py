"""Tests for agent runtime."""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from nergal.agent.runtime import AgentRuntime
from nergal.dispatcher.native import NativeToolDispatcher
from nergal.llm.base import BaseLLMProvider, LLMMessage, LLMResponse, MessageRole
from nergal.memory.base import Memory, MemoryCategory, MemoryEntry
from nergal.security.policy import SecurityPolicy
from nergal.tools.base import Tool, ToolResult
from nergal.tools.exceptions import ToolError


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = AsyncMock(spec=BaseLLMProvider)
    provider.provider_name = "test_provider"
    provider.model = "test_model"
    return provider


@pytest.fixture
def mock_memory():
    """Create a mock memory backend."""
    memory = AsyncMock(spec=Memory)
    return memory


@pytest.fixture
def mock_security_policy():
    """Create a mock security policy."""
    policy = Mock(spec=SecurityPolicy)
    policy.is_tool_allowed.return_value = (True, None)
    return policy


@pytest.fixture
def mock_tool():
    """Create a mock tool."""
    tool = Mock(spec=Tool)
    tool.name = "test_tool"
    tool.description = "Test tool"
    tool.parameters = {}
    return tool


@pytest.fixture
def agent_runtime(mock_llm_provider, mock_memory, mock_security_policy, mock_tool):
    """Create an agent runtime instance."""
    return AgentRuntime(
        llm_provider=mock_llm_provider,
        tools=[mock_tool],
        memory=mock_memory,
        security_policy=mock_security_policy,
        max_history=20,
    )


class TestAgentRuntimeInitialization:
    """Tests for AgentRuntime initialization."""

    def test_init_creates_runtime(
        self, agent_runtime, mock_llm_provider, mock_memory, mock_security_policy
    ):
        """Test that init creates runtime with all dependencies."""
        assert agent_runtime.llm_provider == mock_llm_provider
        assert agent_runtime.memory == mock_memory
        assert agent_runtime.security_policy == mock_security_policy
        assert len(agent_runtime.tools) == 1
        assert agent_runtime.max_history == 20
        assert agent_runtime.dispatcher is not None

    def test_init_default_max_history(
        self, mock_llm_provider, mock_memory, mock_security_policy, mock_tool
    ):
        """Test that default max_history is used."""
        runtime = AgentRuntime(
            llm_provider=mock_llm_provider,
            tools=[mock_tool],
            memory=mock_memory,
            security_policy=mock_security_policy,
        )
        assert runtime.max_history == 20

    def test_init_with_multiple_tools(self, mock_llm_provider, mock_memory, mock_security_policy):
        """Test initialization with multiple tools."""
        tool1 = Mock(spec=Tool)
        tool1.name = "tool1"
        tool2 = Mock(spec=Tool)
        tool2.name = "tool2"

        runtime = AgentRuntime(
            llm_provider=mock_llm_provider,
            tools=[tool1, tool2],
            memory=mock_memory,
            security_policy=mock_security_policy,
        )
        assert len(runtime.tools) == 2


class TestAgentRuntimeProcessMessage:
    """Tests for process_message method."""

    @pytest.mark.asyncio
    async def test_process_message_simple(self, agent_runtime, mock_memory):
        """Test processing a simple message without memory."""
        mock_memory.recall.return_value = []

        with patch("nergal.agent.runtime.run_tool_call_loop", return_value="Hello!") as mock_loop:
            response = await agent_runtime.process_message(123, "Hello!")

            assert response == "Hello!"
            mock_memory.recall.assert_called_once_with(query="Hello!", limit=3)
            mock_loop.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_with_memory(self, agent_runtime, mock_memory):
        """Test processing message with memory entries."""
        entry = MemoryEntry(
            key="test",
            content="User prefers dark mode",
            category=MemoryCategory.USER,
        )
        mock_memory.recall.return_value = [entry]

        with patch(
            "nergal.agent.runtime.run_tool_call_loop", return_value="I'll use dark mode."
        ) as mock_loop:
            response = await agent_runtime.process_message(123, "Configure my UI.")

            assert response == "I'll use dark mode."

    @pytest.mark.asyncio
    async def test_process_message_with_conversation_history(self, agent_runtime, mock_memory):
        """Test processing with conversation history."""
        mock_memory.recall.return_value = []
        history = [
            LLMMessage(role=MessageRole.USER, content="Previous message"),
        ]

        with patch("nergal.agent.runtime.run_tool_call_loop", return_value="Response") as mock_loop:
            response = await agent_runtime.process_message(
                123, "New message", conversation_history=history
            )

            assert response == "Response"

    @pytest.mark.asyncio
    async def test_process_message_memory_error(self, agent_runtime, mock_memory):
        """Test handling memory recall errors."""
        mock_memory.recall.side_effect = Exception("Memory error")

        with patch("nergal.agent.runtime.run_tool_call_loop", return_value="Response") as mock_loop:
            response = await agent_runtime.process_message(123, "Test")

            # Should not raise, should log warning and continue
            assert response == "Response"

    @pytest.mark.asyncio
    async def test_process_message_tool_loop_error(
        self, agent_runtime, mock_memory, mock_llm_provider
    ):
        """Test handling tool call loop errors."""
        mock_memory.recall.return_value = []
        mock_llm_provider.generate.side_effect = Exception("LLM error")

        response = await agent_runtime.process_message(123, "Test")

        assert "error" in response.lower()
        assert "llm error" in response.lower()


class TestAgentRuntimeBuildSystemPrompt:
    """Tests for _build_system_prompt method."""

    @pytest.mark.asyncio
    async def test_build_system_prompt_no_memory(self, agent_runtime):
        """Test building system prompt without memory entries."""
        prompt = await agent_runtime._build_system_prompt([])

        assert "## Instructions" in prompt
        assert "AI assistant" in prompt
        assert "tools" in prompt.lower()

    @pytest.mark.asyncio
    async def test_build_system_prompt_with_memory(self, agent_runtime):
        """Test building system prompt with memory entries."""
        entries = [
            MemoryEntry(
                key="pref1",
                content="User likes red",
                category=MemoryCategory.USER,
            ),
            MemoryEntry(
                key="pref2",
                content="System uses Python",
                category=MemoryCategory.SYSTEM,
            ),
        ]
        prompt = await agent_runtime._build_system_prompt(entries)

        assert "## Context from Memory" in prompt
        assert "[user] User likes red" in prompt
        assert "[system] System uses Python" in prompt
        assert "## Instructions" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_multiple_memory_entries(self, agent_runtime):
        """Test building system prompt with multiple entries."""
        entries = [
            MemoryEntry(
                key=f"entry{i}",
                content=f"Content {i}",
                category=MemoryCategory.USER,
            )
            for i in range(5)
        ]
        prompt = await agent_runtime._build_system_prompt(entries)

        # Should contain all entries
        for i in range(5):
            assert f"Content {i}" in prompt


class TestAgentRuntimeGetAvailableToolsInfo:
    """Tests for get_available_tools_info method."""

    @pytest.mark.asyncio
    async def test_get_available_tools_info_with_tools(self, agent_runtime):
        """Test getting info with available tools."""
        info = await agent_runtime.get_available_tools_info()

        assert "## Available Tools" in info
        assert "test_tool" in info
        assert "✓" in info

    @pytest.mark.asyncio
    async def test_get_available_tools_info_no_tools(self, agent_runtime):
        """Test getting info with no tools."""
        agent_runtime.tools = []

        info = await agent_runtime.get_available_tools_info()

        assert info == "No tools available."

    @pytest.mark.asyncio
    async def test_get_available_tools_info_blocked_tool(self, agent_runtime, mock_security_policy):
        """Test getting info when tool is blocked."""
        mock_security_policy.is_tool_allowed.return_value = (False, "Dangerous tool")

        info = await agent_runtime.get_available_tools_info()

        assert "✗" in info
        assert "Reason: Dangerous tool" in info

    @pytest.mark.asyncio
    async def test_get_available_tools_info_multiple_tools(
        self, agent_runtime, mock_security_policy
    ):
        """Test getting info with multiple tools."""
        tool2 = Mock(spec=Tool)
        tool2.name = "tool2"
        tool2.description = "Second tool"

        agent_runtime.tools = [agent_runtime.tools[0], tool2]

        info = await agent_runtime.get_available_tools_info()

        assert "test_tool" in info
        assert "tool2" in info


class TestAgentRuntimeIntegration:
    """Integration tests for AgentRuntime."""

    @pytest.mark.asyncio
    async def test_full_message_flow(self, agent_runtime, mock_memory):
        """Test complete message processing flow."""
        # Setup memory
        entry = MemoryEntry(
            key="context",
            content="User context",
            category=MemoryCategory.USER,
        )
        mock_memory.recall.return_value = [entry]

        # Mock the tool call loop
        with patch(
            "nergal.agent.runtime.run_tool_call_loop", return_value="Final response"
        ) as mock_loop:
            response = await agent_runtime.process_message(456, "What can you do?")

            assert response == "Final response"
            mock_memory.recall.assert_called_once()
            mock_loop.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_allowed_check(self, agent_runtime, mock_security_policy):
        """Test that security policy is consulted."""
        await agent_runtime.get_available_tools_info()

        mock_security_policy.is_tool_allowed.assert_called_once_with("test_tool")
