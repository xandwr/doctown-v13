"""Protocol for text chunking strategies."""

from typing import Protocol, runtime_checkable

from docpack.models import Chunk


@runtime_checkable
class ChunkingStrategy(Protocol):
    """Protocol for text chunking strategies.

    Different strategies can be used for different content types.
    """

    def chunk(self, text: str, file_path: str) -> list[Chunk]:
        """Split text into chunks with metadata."""
        ...
