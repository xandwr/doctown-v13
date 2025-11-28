"""Protocol definitions for extensible components."""

from docpack.protocols.chunker import ChunkingStrategy
from docpack.protocols.embedder import EmbeddingProvider
from docpack.protocols.ingester import Ingester

__all__ = ["Ingester", "EmbeddingProvider", "ChunkingStrategy"]
