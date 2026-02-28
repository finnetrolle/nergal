"""Text chunking for memory entries.

This module provides utilities for breaking up long text into
manageable chunks for storage and retrieval in the memory system.

Features:
    - Split on paragraphs, sentences, or character count
    - Preserve context overlap between chunks
    - Configurable chunk sizes

Example:
    >>> from nergal.memory.chunker import TextChunker
    >>>
    >>> chunker = TextChunker(chunk_size=500, overlap=50)
    >>> chunks = chunker.chunk(long_text)
    >>> for i, chunk in enumerate(chunks):
    ...     print(f"Chunk {i+1}: {chunk[:50]}...")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class Chunk:
    """A chunk of text.

    Attributes:
        text: The chunk's text content.
        index: The index of this chunk in the sequence.
        total_chunks: Total number of chunks.
    """

    text: str
    """The chunk's text content."""

    index: int
    """The index of this chunk in the sequence (0-based)."""

    total_chunks: int
    """Total number of chunks."""

    def __str__(self) -> str:
        return self.text

    def __len__(self) -> int:
        return len(self.text)


class TextChunker:
    """Text chunker for breaking up long text.

    Provides various strategies for splitting text into chunks,
    with configurable sizes and overlap.

    Args:
        chunk_size: Target size for chunks in characters.
        overlap: Number of characters to overlap between chunks.
        separator: Default separator to use (paragraph, sentence, etc.).
        preserve_newlines: Whether to preserve newlines in chunks.

    Example:
        >>> chunker = TextChunker(
        ...     chunk_size=500,
        ...     overlap=50,
        ...     separator="paragraph",
        ... )
        >>> chunks = chunker.chunk(long_document)
    """

    # Predefined separator strategies
    PARAGRAPH_SEPARATOR = "paragraph"
    SENTENCE_SEPARATOR = "sentence"
    WORD_SEPARATOR = "word"

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        separator: str = PARAGRAPH_SEPARATOR,
        preserve_newlines: bool = True,
    ) -> None:
        """Initialize the text chunker.

        Args:
            chunk_size: Target size for chunks in characters.
            overlap: Number of characters to overlap between chunks.
            separator: Separator strategy (paragraph, sentence, word).
            preserve_newlines: Whether to preserve newlines in chunks.
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separator = separator
        self.preserve_newlines = preserve_newlines

        # Validate parameters
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

    def chunk(self, text: str) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: The text to chunk.

        Returns:
            List of Chunk objects.

        Examples:
            >>> chunker = TextChunker(chunk_size=100)
            >>> chunks = chunker.chunk("A" * 200)
            >>> len(chunks)
            2
        """
        if not text or not text.strip():
            return []

        # Normalize text
        if not self.preserve_newlines:
            text = re.sub(r"\s+", " ", text).strip()

        # Split based on separator strategy
        segments = self._split_by_separator(text)

        # Combine segments into chunks
        chunks = self._create_chunks(segments)

        return chunks

    def _split_by_separator(self, text: str) -> list[str]:
        """Split text by the configured separator.

        Args:
            text: The text to split.

        Returns:
            List of text segments.
        """
        if self.separator == self.PARAGRAPH_SEPARATOR:
            # Split by double newlines
            segments = re.split(r"\n\s*\n", text)
            return [s.strip() for s in segments if s.strip()]
        elif self.separator == self.SENTENCE_SEPARATOR:
            # Split by sentence endings
            # This is a simple regex-based sentence splitter
            segments = re.split(r"(?<=[.!?])\s+", text)
            return [s.strip() for s in segments if s.strip()]
        elif self.separator == self.WORD_SEPARATOR:
            # Split into words and regroup in chunks
            words = text.split()
            words_per_chunk = self.chunk_size // 5
            segments = [
                " ".join(words[i : i + words_per_chunk])
                for i in range(0, len(words), words_per_chunk)
            ]
            return [s.strip() for s in segments if s.strip()]
        else:
            # Unknown separator, return whole text
            return [text]

    def _create_chunks(self, segments: list[str]) -> list[Chunk]:
        """Create chunks from segments with overlap.

        Args:
            segments: Text segments to combine.

        Returns:
            List of Chunk objects.
        """
        if not segments:
            return []

        chunks = []
        current_chunk = ""
        chunk_index = 0

        for segment in segments:
            # Check if adding this segment would exceed chunk size
            if len(current_chunk) + len(segment) + len("\n\n") <= self.chunk_size:
                # Add to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + segment
                else:
                    current_chunk = segment
            else:
                # Save current chunk and start a new one
                if current_chunk:
                    chunks.append(Chunk(
                        text=current_chunk,
                        index=chunk_index,
                        total_chunks=0,  # Will update at the end
                    ))
                    chunk_index += 1

                # Add overlap from previous chunk
                if current_chunk and self.overlap > 0:
                    overlap_text = current_chunk[-self.overlap :]
                    current_chunk = overlap_text + "\n\n" + segment
                else:
                    current_chunk = segment

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(Chunk(
                text=current_chunk,
                index=chunk_index,
                total_chunks=0,
            ))

        # Update total_chunks for all chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks

    def set_separator(self, separator: str) -> None:
        """Change the separator strategy.

        Args:
            separator: New separator strategy.
        """
        valid_separators = [
            self.PARAGRAPH_SEPARATOR,
            self.SENTENCE_SEPARATOR,
            self.WORD_SEPARATOR,
        ]
        if separator not in valid_separators:
            raise ValueError(f"Unknown separator: {separator}")
        self.separator = separator


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    separator: str = TextChunker.PARAGRAPH_SEPARATOR,
) -> list[str]:
    """Convenience function to chunk text.

    Args:
        text: The text to chunk.
        chunk_size: Target size for chunks.
        overlap: Character overlap between chunks.
        separator: Separator strategy.

    Returns:
        List of chunk strings.

    Example:
        >>> chunks = chunk_text(long_text, chunk_size=500, overlap=50)
        >>> for i, chunk in enumerate(chunks):
        ...     print(f"Chunk {i+1}/{len(chunks)}: {chunk[:50]}...")
    """
    chunker = TextChunker(
        chunk_size=chunk_size,
        overlap=overlap,
        separator=separator,
    )
    return [chunk.text for chunk in chunker.chunk(text)]
