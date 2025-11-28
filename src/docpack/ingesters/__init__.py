"""Input source handlers (ingesters) for DocPack."""

from pathlib import Path
from typing import Optional

from docpack.ingesters.folder_ingester import FolderIngester
from docpack.ingesters.zip_ingester import ZipIngester
from docpack.protocols import Ingester

# Registry of available ingesters
_INGESTERS: list[Ingester] = [
    ZipIngester(),
    FolderIngester(),
]


def get_ingester(source: Path | str) -> Optional[Ingester]:
    """Find an ingester that can handle the given source.

    Args:
        source: Path to the input source (folder or zip file)

    Returns:
        An Ingester instance that can handle the source, or None
    """
    source_path = Path(source)
    for ingester in _INGESTERS:
        if ingester.can_handle(source_path):
            return ingester
    return None


def register_ingester(ingester: Ingester) -> None:
    """Register a custom ingester (for plugins/extensions).

    Args:
        ingester: An object implementing the Ingester protocol
    """
    _INGESTERS.append(ingester)


__all__ = ["get_ingester", "register_ingester", "ZipIngester", "FolderIngester"]
