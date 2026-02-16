"""Custom exceptions for the Nergal application.

This module defines a hierarchy of exceptions for better error handling
and more informative error messages throughout the application.

Exception Hierarchy:
    NergalError (base)
    ├── ConfigurationError
    ├── AgentError
    │   ├── AgentNotFoundError
    │   └── AgentExecutionError
    ├── LLMError
    │   ├── LLMConnectionError
    │   ├── LLMTimeoutError
    │   └── LLMResponseError
    ├── SearchError
    │   ├── SearchConnectionError
    │   └── SearchTimeoutError
    └── STTError
        ├── STTConnectionError
        └── STTUnsupportedFormatError
"""


class NergalError(Exception):
    """Base exception for all Nergal errors.
    
    All custom exceptions in the application should inherit from this class.
    This allows catching all application-specific errors with a single except clause.
    
    Attributes:
        message: Human-readable error description.
        cause: Optional underlying exception that caused this error.
    """
    
    def __init__(
        self,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error description.
            cause: Optional underlying exception that caused this error.
        """
        self.message = message
        self.cause = cause
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class ConfigurationError(NergalError):
    """Error in application configuration.
    
    Raised when configuration is missing, invalid, or cannot be loaded.
    """
    
    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the configuration error.
        
        Args:
            message: Human-readable error description.
            config_key: The configuration key that caused the error.
            cause: Optional underlying exception.
        """
        self.config_key = config_key
        if config_key:
            message = f"{message} (key: {config_key})"
        super().__init__(message, cause)


class AgentError(NergalError):
    """Base error for agent-related issues.
    
    Attributes:
        agent_type: The type of agent that encountered the error.
    """
    
    def __init__(
        self,
        message: str,
        agent_type: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the agent error.
        
        Args:
            message: Human-readable error description.
            agent_type: The type of agent that encountered the error.
            cause: Optional underlying exception.
        """
        self.agent_type = agent_type
        if agent_type:
            message = f"[{agent_type}] {message}"
        super().__init__(message, cause)


class AgentNotFoundError(AgentError):
    """Error when a requested agent is not registered.
    
    Raised when trying to get an agent that doesn't exist in the registry.
    """
    
    def __init__(
        self,
        agent_type: str,
        available_agents: list[str] | None = None,
    ) -> None:
        """Initialize the agent not found error.
        
        Args:
            agent_type: The type of agent that was requested.
            available_agents: List of available agent types.
        """
        message = f"Agent '{agent_type}' not found in registry"
        if available_agents:
            message += f". Available agents: {', '.join(available_agents)}"
        super().__init__(message, agent_type)


class AgentExecutionError(AgentError):
    """Error during agent execution.
    
    Raised when an agent fails to process a message.
    """
    
    def __init__(
        self,
        message: str,
        agent_type: str,
        step_description: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the agent execution error.
        
        Args:
            message: Human-readable error description.
            agent_type: The type of agent that failed.
            step_description: Description of the step that failed.
            cause: Optional underlying exception.
        """
        self.step_description = step_description
        if step_description:
            message = f"{message} (step: {step_description})"
        super().__init__(message, agent_type, cause)


class LLMError(NergalError):
    """Base error for LLM provider issues.
    
    Attributes:
        provider_name: Name of the LLM provider that encountered the error.
    """
    
    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the LLM error.
        
        Args:
            message: Human-readable error description.
            provider_name: Name of the LLM provider.
            cause: Optional underlying exception.
        """
        self.provider_name = provider_name
        if provider_name:
            message = f"[{provider_name}] {message}"
        super().__init__(message, cause)


class LLMConnectionError(LLMError):
    """Error connecting to LLM provider.
    
    Raised when network or connection issues prevent reaching the LLM API.
    """
    pass


class LLMTimeoutError(LLMError):
    """Error when LLM request times out.
    
    Raised when the LLM provider takes too long to respond.
    
    Attributes:
        timeout_seconds: The timeout duration that was exceeded.
    """
    
    def __init__(
        self,
        message: str = "LLM request timed out",
        provider_name: str | None = None,
        timeout_seconds: float | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the timeout error.
        
        Args:
            message: Human-readable error description.
            provider_name: Name of the LLM provider.
            timeout_seconds: The timeout duration that was exceeded.
            cause: Optional underlying exception.
        """
        self.timeout_seconds = timeout_seconds
        if timeout_seconds:
            message = f"{message} (timeout: {timeout_seconds}s)"
        super().__init__(message, provider_name, cause)


class LLMResponseError(LLMError):
    """Error when LLM response is invalid.
    
    Raised when the LLM returns an unexpected or malformed response.
    """
    pass


class SearchError(NergalError):
    """Base error for web search issues.
    
    Attributes:
        query: The search query that caused the error.
    """
    
    def __init__(
        self,
        message: str,
        query: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the search error.
        
        Args:
            message: Human-readable error description.
            query: The search query that caused the error.
            cause: Optional underlying exception.
        """
        self.query = query
        if query:
            # Truncate long queries in error message
            query_preview = query[:50] + "..." if len(query) > 50 else query
            message = f"{message} (query: '{query_preview}')"
        super().__init__(message, cause)


class SearchConnectionError(SearchError):
    """Error connecting to search provider.
    
    Raised when network issues prevent reaching the search API.
    """
    pass


class SearchTimeoutError(SearchError):
    """Error when search request times out.
    
    Attributes:
        timeout_seconds: The timeout duration that was exceeded.
    """
    
    def __init__(
        self,
        message: str = "Search request timed out",
        query: str | None = None,
        timeout_seconds: float | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the timeout error.
        
        Args:
            message: Human-readable error description.
            query: The search query.
            timeout_seconds: The timeout duration that was exceeded.
            cause: Optional underlying exception.
        """
        self.timeout_seconds = timeout_seconds
        if timeout_seconds:
            message = f"{message} (timeout: {timeout_seconds}s)"
        super().__init__(message, query, cause)


class SearchRateLimitError(SearchError):
    """Error when search rate limit is exceeded.
    
    Raised when too many requests are made to the search API.
    """
    pass


class STTError(NergalError):
    """Base error for Speech-to-Text issues.
    
    Attributes:
        provider_name: Name of the STT provider.
    """
    
    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the STT error.
        
        Args:
            message: Human-readable error description.
            provider_name: Name of the STT provider.
            cause: Optional underlying exception.
        """
        self.provider_name = provider_name
        if provider_name:
            message = f"[{provider_name}] {message}"
        super().__init__(message, cause)


class STTConnectionError(STTError):
    """Error connecting to STT provider.
    
    Raised when network issues prevent reaching the STT API.
    """
    pass


class STTUnsupportedFormatError(STTError):
    """Error when audio format is not supported.
    
    Attributes:
        format: The unsupported audio format.
    """
    
    def __init__(
        self,
        message: str = "Unsupported audio format",
        format: str | None = None,
        provider_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the unsupported format error.
        
        Args:
            message: Human-readable error description.
            format: The unsupported audio format.
            provider_name: Name of the STT provider.
            cause: Optional underlying exception.
        """
        self.format = format
        if format:
            message = f"{message}: {format}"
        super().__init__(message, provider_name, cause)


class AudioTooLongError(STTError):
    """Error when audio duration exceeds maximum allowed.
    
    Attributes:
        duration_seconds: Actual duration of the audio.
        max_seconds: Maximum allowed duration.
    """
    
    def __init__(
        self,
        duration_seconds: float,
        max_seconds: int,
        provider_name: str | None = None,
    ) -> None:
        """Initialize the audio too long error.
        
        Args:
            duration_seconds: Actual duration of the audio.
            max_seconds: Maximum allowed duration.
            provider_name: Name of the STT provider.
        """
        self.duration_seconds = duration_seconds
        self.max_seconds = max_seconds
        message = (
            f"Audio duration ({duration_seconds:.1f}s) exceeds "
            f"maximum allowed ({max_seconds}s)"
        )
        super().__init__(message, provider_name)
