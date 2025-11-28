"""Ingester for local folders."""

import os
from pathlib import Path
from typing import Iterator

from docpack.models import Document, FileMetadata
from docpack.utils.binary import detect_binary


class FolderIngester:
    """Ingester for local filesystem folders."""

    source_type = "folder"

    def can_handle(self, source: Path) -> bool:
        """Check if this is an existing directory."""
        return source.is_dir()

    def ingest(self, source: Path) -> Iterator[Document]:
        """Yield documents from a folder recursively.

        Args:
            source: Path to the folder

        Yields:
            Document objects for each file in the folder
        """
        for root, _, files in os.walk(source):
            for filename in files:
                full_path = Path(root) / filename
                rel_path = full_path.relative_to(source)

                # Skip hidden files and common ignore patterns
                if self._should_skip(rel_path):
                    continue

                # Read file content
                try:
                    raw_content = full_path.read_bytes()
                except (PermissionError, OSError):
                    continue

                # Check if binary
                is_binary = detect_binary(str(rel_path), raw_content)

                # Build metadata
                metadata = FileMetadata(
                    path=str(rel_path),
                    size_bytes=len(raw_content),
                    extension=full_path.suffix.lower(),
                    is_binary=is_binary,
                )

                # Decode content if text, otherwise None
                content = None
                if not is_binary:
                    content = raw_content.decode("utf-8", errors="replace")

                yield Document(metadata=metadata, content=content)

    def _should_skip(self, path: Path) -> bool:
        """Check if a file should be skipped.

        Skips hidden files, common build artifacts, and version control.
        """
        parts = path.parts

        # Skip hidden files/folders
        if any(part.startswith(".") for part in parts):
            return True

        # Skip common artifacts
        skip_patterns = {
            "__pycache__",
            "node_modules",
            ".git",
            ".svn",
            ".hg",
            "venv",
            ".venv",
            "env",
            ".env",
            "dist",
            "build",
            ".tox",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "*.egg-info",
        }

        return any(part in skip_patterns for part in parts)
