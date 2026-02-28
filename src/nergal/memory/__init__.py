"""Memory system for persistent context storage and retrieval.

This package provides persistent memory capabilities for the agent,
including storage, retrieval, and RAG (Retrieval-Augmented Generation)
context building.

Components:
    - base: Memory interface and data structures
    - sqlite: SQLite backend with FTS5 full-text search
    - chunker: Text chunking for memory entries
    - rag: RAG context builder for system prompts
    - exceptions: Memory system exceptions
"""

from nergal.memory.base import Memory, MemoryCategory, MemoryEntry
from nergal.memory.chunker import TextChunker
from nergal.memory.exceptions import MemoryError
from nergal.memory.rag import RAGContextBuilder

__all__ = [
    "Memory",
    "MemoryCategory",
    "MemoryEntry",
    "RAGContextBuilder",
    "TextChunker",
    "MemoryError",
]
