# LLM Providers Guide

This document describes how to work with LLM providers in Nergal and how to add new providers.

## Architecture Overview

The LLM service follows a provider pattern that allows easy extension for different LLM backends:

```
src/nergal/llm/
├── __init__.py          # Public API
├── base.py              # Abstract base class (BaseLLMProvider)
├── factory.py           # Provider factory
└── providers/
    ├── __init__.py
    └── zai.py           # Z.ai implementation
```

## Existing Providers

### Z.ai (GLM)

Z.ai is the default provider, supporting GLM-4 models from Zhipu AI.

**Configuration:**
```env
LLM_PROVIDER=zai
LLM_API_KEY=your_jwt_token
LLM_MODEL=glm-4-flash  # Options: glm-4, glm-4-flash, glm-4-plus
```

**API Endpoint:** `https://open.bigmodel.cn/api/paas/v4`

## Adding a New Provider

### Step 1: Create the Provider Class

Create a new file in `src/nergal/llm/providers/` (e.g., `anthropic.py`):

```python
"""Anthropic LLM provider implementation."""

from typing import Any
from collections.abc import AsyncGenerator

from nergal.llm.base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMError,
    LLMMessage,
    LLMRateLimitError,
    LLMResponse,
)

ANTHROPIC_DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_DEFAULT_MODEL = "claude-3-sonnet-20240229"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider."""

    DEFAULT_BASE_URL = ANTHROPIC_DEFAULT_BASE_URL
    DEFAULT_MODEL = ANTHROPIC_DEFAULT_MODEL

    def __init__(
        self,
        api_key: str,
        model: str = ANTHROPIC_DEFAULT_MODEL,
        base_url: str | None = None,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key, model, base_url or self.DEFAULT_BASE_URL, **kwargs)
        self.timeout = timeout
        # Initialize HTTP client, etc.

    @property
    def provider_name(self) -> str:
        return "Anthropic"

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from Anthropic."""
        # 1. Build request body in provider-specific format
        # 2. Make API call
        # 3. Handle errors (raise appropriate LLMError subclasses)
        # 4. Parse response and return LLMResponse
        raise NotImplementedError("Implement this method")

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from Anthropic."""
        # 1. Build request body with stream=True
        # 2. Make streaming API call
        # 3. Yield content chunks
        raise NotImplementedError("Implement this method")
```

### Step 2: Register the Provider

Add the provider to `src/nergal/llm/providers/__init__.py`:

```python
from nergal.llm.providers.zai import ZaiProvider
from nergal.llm.providers.anthropic import AnthropicProvider  # Add import

__all__ = [
    "ZaiProvider",
    "AnthropicProvider",  # Add to exports
]
```

Update `src/nergal/llm/factory.py`:

```python
from nergal.llm.providers.zai import ZaiProvider
from nergal.llm.providers.anthropic import AnthropicProvider  # Add import

_PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {
    LLMProviderType.ZAI: ZaiProvider,
    LLMProviderType.ANTHROPIC: AnthropicProvider,  # Add to registry
    # Add more providers here...
}
```

Add the provider type to the enum in `factory.py`:

```python
class LLMProviderType(str, Enum):
    ZAI = "zai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"  # Add this
    MINIMAX = "minimax"
```

### Step 3: Update Configuration

The configuration in `src/nergal/config.py` already supports any provider through environment variables. Just document the new provider's default model in the code or update the default:

```python
class LLMSettings(BaseSettings):
    # ...
    model: str = Field(
        default="glm-4-flash",  # Change or document per-provider defaults
        description="Model identifier (glm-4-flash, claude-3-sonnet, gpt-4, etc.)"
    )
```

### Step 4: Update Documentation

Update `.env.example` with provider-specific examples:

```env
# LLM Provider Configuration
# Supported providers: zai, openai, anthropic, minimax
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-3-sonnet-20240229
```

## Base Class Reference

### BaseLLMProvider

```python
class BaseLLMProvider(ABC):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize provider with credentials and configuration."""

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a complete response."""

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name for logging/errors."""

    def validate_config(self) -> None:
        """Override to add provider-specific validation."""
```

### Data Classes

```python
@dataclass
class LLMMessage:
    role: MessageRole  # SYSTEM, USER, ASSISTANT
    content: str

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int] | None = None  # {"prompt_tokens": N, "completion_tokens": M}
    finish_reason: str | None = None
    raw_response: dict[str, Any] | None = None
```

### Exception Classes

- `LLMError` — Base exception for all LLM errors
- `LLMAuthenticationError` — Invalid API key (401)
- `LLMRateLimitError` — Rate limit exceeded (429)
- `LLMModelNotFoundError` — Model not found (404)

## Usage Examples

### Basic Generation

```python
from nergal.llm import create_llm_provider, LLMMessage, MessageRole
from nergal.config import get_settings

settings = get_settings()

provider = create_llm_provider(
    provider_type=settings.llm.provider,
    api_key=settings.llm.api_key,
    model=settings.llm.model,
    temperature=settings.llm.temperature,
)

messages = [
    LLMMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
    LLMMessage(role=MessageRole.USER, content="Hello!"),
]

response = await provider.generate(messages)
print(response.content)
```

### Streaming Generation

```python
async for chunk in provider.generate_stream(messages):
    print(chunk, end="", flush=True)
```

### Dynamic Provider Registration

```python
from nergal.llm.factory import register_provider
from my_custom_provider import CustomProvider

register_provider("custom", CustomProvider)

provider = create_llm_provider(
    provider_type="custom",
    api_key="...",
    model="...",
)
```

## Testing Providers

When adding a new provider, create tests in `tests/llm/providers/`:

```python
import pytest
from unittest.mock import AsyncMock, patch

from nergal.llm import LLMMessage, MessageRole
from nergal.llm.providers.anthropic import AnthropicProvider


@pytest.fixture
def provider():
    return AnthropicProvider(api_key="test-key", model="claude-3-sonnet")


@pytest.mark.asyncio
async def test_generate(provider):
    messages = [LLMMessage(role=MessageRole.USER, content="Hello")]

    with patch.object(provider, "_get_client") as mock_client:
        # Mock the HTTP response
        # Assert correct request format
        # Assert correct response parsing
        pass
```

## Provider-Specific Considerations

### OpenAI
- Uses `Authorization: Bearer` header
- Supports function calling and tools
- Models: gpt-4, gpt-4-turbo, gpt-3.5-turbo

### Anthropic
- Uses `x-api-key` header and `anthropic-version` header
- Requires `max_tokens` parameter
- System message is separate from messages array
- Models: claude-3-opus, claude-3-sonnet, claude-3-haiku

### Minimax
- Chinese LLM provider
- Uses different authentication scheme
- Models: abab5.5-chat, abab5.5s-chat

### Z.ai (Zhipu)
- Uses JWT token authentication
- OpenAI-compatible API format
- Models: glm-4, glm-4-flash, glm-4-plus
