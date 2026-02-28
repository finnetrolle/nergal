"""Pytest configuration and fixtures for Nergal tests."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lib import BaseLLMProvider, LLMMessage, LLMResponse, MessageRole


# =============================================================================
# LLM Provider Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_response() -> LLMResponse:
    """Create a mock LLM response."""
    return LLMResponse(
        content="This is a test response.",
        model="test-model",
        usage={"prompt_tokens": 50, "completion_tokens": 50, "total_tokens": 100},
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
            usage={"prompt_tokens": 50, "completion_tokens": 50, "total_tokens": 100},
            finish_reason="stop",
        )
        provider = MagicMock(spec=BaseLLMProvider)
        provider.provider_name = "mock-provider"
        provider.generate = AsyncMock(return_value=response)
        return provider

    return _create_provider


# =============================================================================
# Context Fixtures
# =============================================================================


@pytest.fixture
def empty_context() -> dict[str, Any]:
    """Create an empty dialog context."""
    return {}


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
def conversation_history(
    user_message: LLMMessage, assistant_message: LLMMessage
) -> list[LLMMessage]:
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
