"""Protocol definitions for dependency injection.

This module defines Protocol classes that specify the interfaces
for various components in the system. Using protocols allows for:
- Easy mocking in tests
- Loose coupling between components
- Better documentation of interfaces
- Type checking with structural subtyping
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """Protocol for LLM providers.
    
    Any class that implements these methods and properties
    can be used as an LLM provider, enabling easy substitution
    for testing or different implementations.
    """
    
    @property
    def provider_name(self) -> str:
        """Return the name of this provider."""
        ...
    
    async def generate(
        self,
        messages: list[Any],
        **kwargs: Any,
    ) -> Any:
        """Generate a response from the LLM.
        
        Args:
            messages: List of message objects.
            **kwargs: Additional provider-specific parameters.
            
        Returns:
            LLMResponse object with generated content.
        """
        ...


@runtime_checkable
class SearchProviderProtocol(Protocol):
    """Protocol for web search providers.
    
    Defines the interface for search providers that can
    query the web for information.
    """
    
    async def search(self, request: Any) -> Any:
        """Execute a search request.
        
        Args:
            request: SearchRequest object with query parameters.
            
        Returns:
            SearchResponse object with results.
        """
        ...


@runtime_checkable
class STTProviderProtocol(Protocol):
    """Protocol for Speech-to-Text providers.
    
    Defines the interface for providers that can transcribe
    audio data to text.
    """
    
    @property
    def provider_name(self) -> str:
        """Return the name of this provider."""
        ...
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: str | None = None,
    ) -> str:
        """Transcribe audio data to text.
        
        Args:
            audio_data: Audio bytes to transcribe.
            language: Optional language code (e.g., 'ru', 'en').
            
        Returns:
            Transcribed text.
        """
        ...


@runtime_checkable
class AgentProtocol(Protocol):
    """Protocol for dialog agents.
    
    Defines the interface that all agents must implement
    to be used in the dialog system.
    """
    
    @property
    def agent_type(self) -> Any:
        """Return the type identifier for this agent."""
        ...
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        ...
    
    async def can_handle(
        self,
        message: str,
        context: dict[str, Any],
    ) -> float:
        """Determine if this agent can handle the message.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        ...
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[Any],
    ) -> Any:
        """Process the message and generate a response.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with response and metadata.
        """
        ...


@runtime_checkable
class ContextManagerProtocol(Protocol):
    """Protocol for context managers.
    
    Defines the interface for managing user dialog contexts.
    """
    
    def get_or_create(
        self,
        user_id: int,
        **kwargs: Any,
    ) -> Any:
        """Get or create a context for a user.
        
        Args:
            user_id: User identifier.
            **kwargs: Additional context parameters.
            
        Returns:
            DialogContext for the user.
        """
        ...
    
    def remove(self, user_id: int) -> bool:
        """Remove context for a user.
        
        Args:
            user_id: User identifier.
            
        Returns:
            True if context was removed, False if not found.
        """
        ...
    
    @property
    def context_count(self) -> int:
        """Return the number of active contexts."""
        ...


@runtime_checkable
class AgentRegistryProtocol(Protocol):
    """Protocol for agent registries.
    
    Defines the interface for managing available agents.
    """
    
    def register(self, agent: AgentProtocol) -> None:
        """Register an agent.
        
        Args:
            agent: Agent instance to register.
        """
        ...
    
    def get(self, agent_type: Any) -> AgentProtocol | None:
        """Get an agent by type.
        
        Args:
            agent_type: Type of agent to retrieve.
            
        Returns:
            Agent instance or None if not found.
        """
        ...
    
    def get_all(self) -> list[AgentProtocol]:
        """Get all registered agents.
        
        Returns:
            List of all registered agents.
        """
        ...
