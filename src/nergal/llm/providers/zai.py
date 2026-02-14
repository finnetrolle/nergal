"""Z.ai (GLM) LLM provider implementation."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from nergal.llm.base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMError,
    LLMMessage,
    LLMModelNotFoundError,
    LLMRateLimitError,
    LLMResponse,
)

logger = logging.getLogger(__name__)

# Z.ai API configuration
ZAI_DEFAULT_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
ZAI_DEFAULT_MODEL = "GLM-4.7"


class ZaiProvider(BaseLLMProvider):
    """Z.ai (Zhipu/GLM) LLM provider.

    Supports GLM-4 and other models from Zhipu AI.
    Uses OpenAI-compatible chat completions API.

    Attributes:
        DEFAULT_BASE_URL: Default API endpoint.
        DEFAULT_MODEL: Default model to use.
    """

    DEFAULT_BASE_URL = ZAI_DEFAULT_BASE_URL
    DEFAULT_MODEL = ZAI_DEFAULT_MODEL

    def __init__(
        self,
        api_key: str,
        model: str = ZAI_DEFAULT_MODEL,
        base_url: str | None = None,
        timeout: float = 120.0,
        **kwargs: Any,
    ) -> None:
        """Initialize Z.ai provider.

        Args:
            api_key: Z.ai API key (JWT token).
            model: Model to use (e.g., 'glm-4', 'glm-4-flash', 'glm-4-plus').
            base_url: Optional custom API endpoint.
            timeout: Request timeout in seconds.
            **kwargs: Additional configuration options.
        """
        super().__init__(api_key, model, base_url or self.DEFAULT_BASE_URL, **kwargs)
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "Z.ai"

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _build_request_body(
        self,
        messages: list[LLMMessage],
        temperature: float,
        max_tokens: int | None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build the request body for the API call."""
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        # Add any additional parameters
        for key, value in kwargs.items():
            if key not in body:
                body[key] = value

        return body

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
            error_code = error_data.get("error", {}).get("code", "unknown")
        except (json.JSONDecodeError, KeyError):
            error_message = response.text or "Unknown error"
            error_code = "unknown"

        if response.status_code == 401:
            raise LLMAuthenticationError(error_message, provider=self.provider_name)
        elif response.status_code == 429:
            raise LLMRateLimitError(error_message, provider=self.provider_name)
        elif response.status_code == 404:
            raise LLMModelNotFoundError(error_message, provider=self.provider_name)
        else:
            raise LLMError(
                f"API error (code={error_code}): {error_message}",
                provider=self.provider_name,
            )

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from Z.ai.

        Args:
            messages: List of messages in the conversation.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters (top_p, stop, etc.).

        Returns:
            LLMResponse with the generated content.

        Raises:
            LLMAuthenticationError: If API key is invalid.
            LLMRateLimitError: If rate limit is exceeded.
            LLMModelNotFoundError: If model is not found.
            LLMError: For other API errors.
        """
        client = self._get_client()
        url = f"{self.base_url}/chat/completions"
        body = self._build_request_body(
            messages, temperature, max_tokens, stream=False, **kwargs
        )

        logger.debug(f"Sending request to Z.ai: {url}")

        response = await client.post(url, json=body)

        if response.status_code != 200:
            self._handle_error_response(response)

        data = response.json()

        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
            usage = data.get("usage")
            model = data.get("model", self.model)

            return LLMResponse(
                content=content,
                model=model,
                usage=usage,
                finish_reason=finish_reason,
                raw_response=data,
            )
        except (KeyError, IndexError) as e:
            raise LLMError(
                f"Invalid response format: {e}", provider=self.provider_name
            ) from e

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from Z.ai.

        Args:
            messages: List of messages in the conversation.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters.

        Yields:
            Chunks of the generated response.

        Raises:
            LLMAuthenticationError: If API key is invalid.
            LLMRateLimitError: If rate limit is exceeded.
            LLMError: For other API errors.
        """
        client = self._get_client()
        url = f"{self.base_url}/chat/completions"
        body = self._build_request_body(
            messages, temperature, max_tokens, stream=True, **kwargs
        )

        logger.debug(f"Sending streaming request to Z.ai: {url}")

        async with client.stream("POST", url, json=body) as response:
            if response.status_code != 200:
                self._handle_error_response(response)

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix

                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        logger.warning(f"Error parsing streaming response: {e}")
                        continue

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ZaiProvider(model={self.model!r})"
