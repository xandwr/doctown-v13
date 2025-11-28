"""Protocol for input source handlers."""

from pathlib import Path
from typing import Iterator, Protocol, runtime_checkable

from docpack.models import Document


@runtime_checkable
class Ingester(Protocol):
    """Protocol for input source handlers.

    Implementations handle different input formats (zip, folder, PDF, URL).
    Uses structural subtyping - no inheritance required.
    """

    @property
    def source_type(self) -> str:
        """Return identifier for this source type (e.g., 'zip', 'folder')."""
        ...

    def can_handle(self, source: Path) -> bool:
        """Check if this ingester can process the given source."""
        ...

    def ingest(self, source: Path) -> Iterator[Document]:
        """Yield documents from the source.

        For binary files, yield Document with content=None and metadata populated.
        """
        ...
