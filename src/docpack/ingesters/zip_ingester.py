"""Ingester for ZIP archive files."""

import zipfile
from pathlib import Path
from typing import Iterator

from docpack.models import Document, FileMetadata
from docpack.utils.binary import detect_binary


class ZipIngester:
    """Ingester for ZIP archive files."""

    source_type = "zip"

    def can_handle(self, source: Path) -> bool:
        """Check if this is a zip file."""
        return source.suffix.lower() == ".zip" and source.exists()

    def ingest(self, source: Path) -> Iterator[Document]:
        """Yield documents from a ZIP archive.

        Args:
            source: Path to the ZIP file

        Yields:
            Document objects for each file in the archive
        """
        with zipfile.ZipFile(source, "r") as zf:
            for info in zf.infolist():
                # Skip directories
                if info.is_dir():
                    continue

                # Read file content
                raw_content = zf.read(info.filename)

                # Check if binary
                is_binary = detect_binary(info.filename, raw_content)

                # Build metadata
                metadata = FileMetadata(
                    path=info.filename,
                    size_bytes=info.file_size,
                    extension=Path(info.filename).suffix.lower(),
                    is_binary=is_binary,
                )

                # Decode content if text, otherwise None
                content = None
                if not is_binary:
                    content = raw_content.decode("utf-8", errors="replace")

                yield Document(metadata=metadata, content=content)
