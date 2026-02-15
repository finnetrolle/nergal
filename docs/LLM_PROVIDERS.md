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

## Current Implementation Status

| Provider | Status | Notes |
|----------|--------|-------|
| Z.ai (GLM) | ✅ Implemented | Default provider |
| OpenAI | 🔜 Planned | GPT-4, GPT-3.5 |
| Anthropic | 🔜 Planned | Claude 3 |
| Minimax | 🔜 Planned | Chinese LLM |

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

**Features:**
- OpenAI-compatible API format
- JWT token authentication
- Supports streaming responses
- Function calling support

**Available Models:**
| Model | Description | Context |
|-------|-------------|---------|
| `glm-4-flash` | Fast, cost-effective | 128K |
| `glm-4` | Standard model | 128K |
| `glm-4-plus` | Enhanced capabilities | 128K |
| `glm-4-long` | Long context | 1M tokens |

## Base Class Reference

### BaseLLMProvider

Located in [`src/nergal/llm/base.py`](src/nergal/llm/base.py:40):

```python
class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize provider with credentials and configuration."""
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.config = kwargs

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
        pass

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
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name for logging/errors."""
        pass

    def validate_config(self) -> None:
        """Override to add provider-specific validation."""
        if not self.api_key:
            raise ValueError(f"{self.provider_name}: API key is required")
        if not self.model:
            raise ValueError(f"{self.provider_name}: Model name is required")
```

### Data Classes

Located in [`src/nergal/llm/base.py`](src/nergal/llm/base.py):

```python
class MessageRole(str, Enum):
    """Role of a message in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

@dataclass
class LLMMessage:
    """Represents a message in an LLM conversation."""
    role: MessageRole
    content: str
    
    def to_dict(self) -> dict[str, str]:
        """Convert message to dictionary format for API calls."""
        return {"role": self.role.value, "content": self.content}

@dataclass
class LLMResponse:
    """Represents a response from an LLM provider."""
    content: str
    model: str
    usage: dict[str, int] | None = None  # {"prompt_tokens": N, "completion_tokens": M}
    finish_reason: str | None = None
    raw_response: dict[str, Any] | None = None
```

### Exception Classes

Located in [`src/nergal/llm/base.py`](src/nergal/llm/base.py:137):

```python
class LLMError(Exception):
    """Base exception for all LLM errors."""
    
    def __init__(self, message: str, provider: str | None = None) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}" if provider else message)

class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded (429)."""
    pass

class LLMAuthenticationError(LLMError):
    """Raised when authentication fails (401)."""
    pass

class LLMModelNotFoundError(LLMError):
    """Raised when the specified model is not found (404)."""
    pass
```

## Factory Function

Located in [`src/nergal/llm/factory.py`](src/nergal/llm/factory.py:30):

```python
def create_llm_provider(
    provider_type: str | LLMProviderType,
    api_key: str,
    model: str,
    base_url: str | None = None,
    **kwargs: Any,
) -> BaseLLMProvider:
    """Create an LLM provider instance.
    
    Args:
        provider_type: Type of provider ('zai', 'openai', 'anthropic').
        api_key: API key for authentication.
        model: Model identifier to use.
        base_url: Optional custom API endpoint.
        **kwargs: Additional provider-specific configuration.
    
    Returns:
        Configured LLM provider instance.
    
    Raises:
        LLMError: If the provider type is not supported.
    """
```

### Supported Provider Types

```python
class LLMProviderType(str, Enum):
    """Supported LLM provider types."""
    ZAI = "zai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MINIMAX = "minimax"
```

### Dynamic Provider Registration

```python
from nergal.llm.factory import register_provider
from my_custom_provider import CustomProvider

# Register a custom provider
register_provider("custom", CustomProvider)

# Now you can use it
provider = create_llm_provider(
    provider_type="custom",
    api_key="...",
    model="...",
)
```

### Get Supported Providers

```python
from nergal.llm.factory import get_supported_providers

providers = get_supported_providers()
# Returns: ['zai']  # Currently only Z.ai is implemented
```

## Usage Examples

### Basic Generation

```python
from nergal.llm import create_llm_provider, LLMMessage, MessageRole
from nergal.config import get_settings

settings = get_settings()

# Create provider
provider = create_llm_provider(
    provider_type=settings.llm.provider,
    api_key=settings.llm.api_key,
    model=settings.llm.model,
)

# Build messages
messages = [
    LLMMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
    LLMMessage(role=MessageRole.USER, content="Hello!"),
]

# Generate response
response = await provider.generate(messages)
print(response.content)
```

### Streaming Generation

```python
# Stream response chunks
async for chunk in provider.generate_stream(messages):
    print(chunk, end="", flush=True)
```

### With Custom Parameters

```python
response = await provider.generate(
    messages,
    temperature=0.5,      # Lower temperature for more focused output
    max_tokens=1000,      # Limit response length
)
```

### Error Handling

```python
from nergal.llm.base import LLMError, LLMRateLimitError, LLMAuthenticationError

try:
    response = await provider.generate(messages)
except LLMAuthenticationError as e:
    print(f"Authentication failed: {e}")
except LLMRateLimitError as e:
    print(f"Rate limit exceeded: {e}")
except LLMError as e:
    print(f"LLM error: {e}")
```

## Adding a New Provider

### Step 1: Create the Provider Class

Create a new file in `src/nergal/llm/providers/` (e.g., `anthropic.py`):

```python
"""Anthropic LLM provider implementation."""

import httpx
from typing import Any
from collections.abc import AsyncGenerator

from nergal.llm.base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMError,
    LLMMessage,
    LLMRateLimitError,
    LLMResponse,
    MessageRole,
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
        self._client = httpx.AsyncClient(timeout=timeout)

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
        # 1. Convert messages to Anthropic format
        # Note: Anthropic uses separate 'system' parameter
        system_message = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        # 2. Build request body
        request_body = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 4096,  # Required for Anthropic
            "temperature": temperature,
        }
        if system_message:
            request_body["system"] = system_message
        
        # 3. Make API call
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        response = await self._client.post(
            f"{self.base_url}/messages",
            json=request_body,
            headers=headers,
        )
        
        # 4. Handle errors
        if response.status_code == 401:
            raise LLMAuthenticationError("Invalid API key", provider=self.provider_name)
        if response.status_code == 429:
            raise LLMRateLimitError("Rate limit exceeded", provider=self.provider_name)
        if response.status_code != 200:
            raise LLMError(f"API error: {response.text}", provider=self.provider_name)
        
        # 5. Parse response
        data = response.json()
        return LLMResponse(
            content=data["content"][0]["text"],
            model=data["model"],
            usage=data.get("usage"),
            finish_reason=data.get("stop_reason"),
            raw_response=data,
        )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from Anthropic."""
        # Implement streaming logic here
        raise NotImplementedError("Streaming not yet implemented for Anthropic")
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
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
}
```

### Step 3: Update Configuration

The configuration in `src/nergal/config.py` already supports any provider through environment variables. Document the new provider's default model:

```python
class LLMSettings(BaseSettings):
    # ...
    model: str = Field(
        default="glm-4-flash",  # Default for Z.ai
        description="Model identifier (glm-4-flash, claude-3-sonnet, gpt-4, etc.)"
    )
```

### Step 4: Update .env.example

```env
# LLM Provider Configuration
# Supported providers: zai, openai, anthropic, minimax
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-3-sonnet-20240229
```

### Step 5: Add Tests

Create tests in `tests/llm/providers/`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from nergal.llm import LLMMessage, MessageRole
from nergal.llm.providers.anthropic import AnthropicProvider


@pytest.fixture
def provider():
    return AnthropicProvider(api_key="test-key", model="claude-3-sonnet")


@pytest.mark.asyncio
async def test_generate(provider):
    messages = [
        LLMMessage(role=MessageRole.SYSTEM, content="You are helpful."),
        LLMMessage(role=MessageRole.USER, content="Hello"),
    ]
    
    # Mock the HTTP client
    with patch.object(provider, '_client') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Hello! How can I help?"}],
            "model": "claude-3-sonnet",
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "stop_reason": "end_turn",
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        
        response = await provider.generate(messages)
        
        assert response.content == "Hello! How can I help?"
        assert response.model == "claude-3-sonnet"
```

## Provider-Specific Considerations

### OpenAI
- Uses `Authorization: Bearer` header
- Supports function calling and tools
- Models: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- Native streaming support

### Anthropic
- Uses `x-api-key` header and `anthropic-version` header
- **Requires** `max_tokens` parameter
- System message is separate from messages array
- Models: claude-3-opus, claude-3-sonnet, claude-3-haiku

### Minimax
- Chinese LLM provider
- Uses different authentication scheme (API ID + API Key)
- Models: abab5.5-chat, abab5.5s-chat

### Z.ai (Zhipu)
- Uses JWT token authentication
- OpenAI-compatible API format
- Models: glm-4, glm-4-flash, glm-4-plus, glm-4-long

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | Provider type | `zai` |
| `LLM_API_KEY` | API key | Required |
| `LLM_MODEL` | Model name | `glm-4-flash` |
| `LLM_BASE_URL` | Custom API URL | Provider default |
| `LLM_TEMPERATURE` | Sampling temperature | `0.7` |
| `LLM_MAX_TOKENS` | Max tokens | None |
| `LLM_TIMEOUT` | Request timeout (seconds) | `120.0` |

### Example Configurations

#### Z.ai (Default)
```env
LLM_PROVIDER=zai
LLM_API_KEY=your_jwt_token
LLM_MODEL=glm-4-flash
LLM_TEMPERATURE=0.7
```

#### OpenAI (When implemented)
```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxxxx
LLM_MODEL=gpt-4-turbo
LLM_TEMPERATURE=0.7
```

#### Anthropic (When implemented)
```env
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-3-sonnet-20240229
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7
```

## Best Practices

1. **Error Handling**: Always wrap LLM calls in try-except blocks
2. **Timeouts**: Set appropriate timeouts for your use case
3. **Rate Limiting**: Implement backoff for rate limit errors
4. **Token Counting**: Monitor token usage for cost control
5. **Streaming**: Use streaming for long responses to improve UX

## Monitoring

LLM calls are automatically monitored when `MONITORING_ENABLED=true`:

- `bot_llm_requests_total` - Request count by provider, model, status
- `bot_llm_request_duration_seconds` - Request latency histogram
- `bot_llm_tokens_total` - Token usage by provider, model, type

See [MONITORING.md](MONITORING.md) for details.
