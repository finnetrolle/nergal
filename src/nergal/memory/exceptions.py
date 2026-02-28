"""Memory system exceptions."""


class MemoryError(Exception):
    """Base exception for memory system errors."""

    pass


class MemoryInitializationError(MemoryError):
    """Raised when memory backend fails to initialize."""

    pass


class MemoryStorageError(MemoryError):
    """Raised when memory storage operation fails."""

    pass


class MemoryRetrievalError(MemoryError):
    """Raised when memory retrieval operation fails."""

    pass
