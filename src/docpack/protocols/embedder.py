"""Protocol for embedding model providers."""

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding model providers.

    Allows swapping between local models (sentence-transformers),
    API-based models (OpenAI), or custom implementations.
    """

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...

    @property
    def model_name(self) -> str:
        """Return identifier for the model used."""
        ...

    def embed(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a batch of texts.

        Returns: numpy array of shape (len(texts), embedding_dim)
        """
        ...
