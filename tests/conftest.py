"""Pytest configuration and fixtures for Nergal tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any

from nergal.dialog.base import BaseAgent, AgentType, AgentRegistry
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMResponse, LLMMessage, MessageRole


# =============================================================================
# LLM Provider Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_response() -> LLMResponse:
    """Create a mock LLM response."""
    return LLMResponse(
        content="This is a test response.",
        model="test-model",
        tokens_used=100,
        finish_reason="stop",
    )


@pytest.fixture
def mock_llm_provider(mock_llm_response: LLMResponse) -> BaseLLMProvider:
    """Create a mock LLM provider."""
    provider = MagicMock(spec=BaseLLMProvider)
    provider.provider_name = "mock-provider"
    provider.generate = AsyncMock(return_value=mock_llm_response)
    return provider


@pytest.fixture
def mock_llm_provider_with_response() -> callable:
    """Factory fixture to create a mock LLM provider with custom response."""
    def _create_provider(response_content: str) -> BaseLLMProvider:
        response = LLMResponse(
            content=response_content,
            model="test-model",
            tokens_used=100,
            finish_reason="stop",
        )
        provider = MagicMock(spec=BaseLLMProvider)
        provider.provider_name = "mock-provider"
        provider.generate = AsyncMock(return_value=response)
        return provider
    return _create_provider


# =============================================================================
# Agent Fixtures
# =============================================================================

@pytest.fixture
def mock_agent() -> BaseAgent:
    """Create a mock agent for testing."""
    agent = MagicMock(spec=BaseAgent)
    agent.agent_type = AgentType.DEFAULT
    agent.system_prompt = "You are a test agent."
    agent.can_handle = AsyncMock(return_value=0.8)
    agent.process = AsyncMock(return_value=MagicMock(
        response="Test response",
        agent_type=AgentType.DEFAULT,
        confidence=0.9,
    ))
    return agent


@pytest.fixture
def agent_registry(mock_agent: BaseAgent) -> AgentRegistry:
    """Create an agent registry with a mock agent."""
    registry = AgentRegistry()
    registry.register(mock_agent)
    return registry


# =============================================================================
# Context Fixtures
# =============================================================================

@pytest.fixture
def empty_context() -> dict[str, Any]:
    """Create an empty dialog context."""
    return {}


@pytest.fixture
def context_with_search_results() -> dict[str, Any]:
    """Create a context with mock search results."""
    return {
        "search_results": "Test search result content about Python programming.",
        "sources": ["https://example.com/article1", "https://example.com/article2"],
        "search_queries": ["python test"],
    }


@pytest.fixture
def context_with_previous_step() -> dict[str, Any]:
    """Create a context with previous step output."""
    return {
        "previous_step_output": "Previous agent output content.",
        "previous_agent": "web_search",
    }


# =============================================================================
# Message Fixtures
# =============================================================================

@pytest.fixture
def user_message() -> LLMMessage:
    """Create a user message."""
    return LLMMessage(role=MessageRole.USER, content="Hello, how are you?")


@pytest.fixture
def assistant_message() -> LLMMessage:
    """Create an assistant message."""
    return LLMMessage(role=MessageRole.ASSISTANT, content="I'm doing well, thank you!")


@pytest.fixture
def conversation_history(user_message: LLMMessage, assistant_message: LLMMessage) -> list[LLMMessage]:
    """Create a conversation history."""
    return [user_message, assistant_message]


# =============================================================================
# Async Test Helpers
# =============================================================================

@pytest.fixture
def async_return():
    """Helper to create an async function that returns a value."""
    def _async_return(value):
        f = AsyncMock()
        f.return_value = value
        return f
    return _async_return
