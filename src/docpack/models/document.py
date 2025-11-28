"""Core data models for documents and chunks."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class FileMetadata:
    """Metadata for any file (text or binary)."""

    path: str
    size_bytes: int
    extension: str
    is_binary: bool


@dataclass
class Chunk:
    """A chunk of text with its context."""

    text: str
    file_path: str
    chunk_index: int
    start_char: int
    end_char: int


@dataclass
class Document:
    """A document extracted from an input source."""

    metadata: FileMetadata
    content: Optional[str] = None  # None for binary files
    chunks: list[Chunk] = field(default_factory=list)
