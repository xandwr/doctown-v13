"""CLI entry point for DocPack."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from docpack.chunkers import ParagraphChunker
from docpack.embedders import SentenceTransformerEmbedder
from docpack.ingesters import get_ingester
from docpack.storage import DocPackStore

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def freeze(source: str, output: str) -> None:
    """Freeze a source into a .docpack file.

    Args:
        source: Path to folder or zip file
        output: Path for output .docpack file
    """
    source_path = Path(source)
    output_path = Path(output)

    # Get appropriate ingester
    ingester = get_ingester(source_path)
    if ingester is None:
        logger.error(f"Cannot process: {source}")
        logger.error("Supported inputs: folders, .zip files")
        sys.exit(1)

    # Initialize components
    logger.info(f"Loading embedding model...")
    embedder = SentenceTransformerEmbedder()
    chunker = ParagraphChunker()
    store = DocPackStore(output_path)
    store.initialize()

    # Store metadata
    store.set_metadata("source", str(source_path.absolute()))
    store.set_metadata("source_type", ingester.source_type)
    store.set_metadata("created_at", datetime.now().isoformat())
    store.set_metadata("embedding_model", embedder.model_name)

    logger.info(f"Freezing {source} -> {output}")

    file_count = 0
    chunk_count = 0

    # Process documents
    for doc in ingester.ingest(source_path):
        store.store_document(doc)
        file_count += 1

        # Only chunk and embed text files
        if doc.content:
            chunks = chunker.chunk(doc.content, doc.metadata.path)

            if chunks:
                chunk_ids = store.store_chunks(chunks)
                texts = [c.text for c in chunks]
                embeddings = embedder.embed(texts)
                store.store_embeddings(chunk_ids, embeddings)
                chunk_count += len(chunks)

        status = "binary" if doc.metadata.is_binary else f"{len(doc.chunks if doc.chunks else [])} chunks"
        logger.info(f"  {doc.metadata.path}")

    logger.info(f"")
    logger.info(f"Frozen {file_count} files, {chunk_count} chunks -> {output_path}")


def serve(docpack: str, transport: str = "stdio") -> None:
    """Start MCP server for a docpack.

    Args:
        docpack: Path to .docpack file
        transport: Transport protocol (stdio or sse)
    """
    docpack_path = Path(docpack)
    if not docpack_path.exists():
        logger.error(f"Docpack not found: {docpack}")
        sys.exit(1)

    # Import here to avoid loading MCP unless needed
    from docpack.server import create_mcp_server

    from typing import cast, Literal

    logger.info(f"Serving {docpack} via {transport}")
    mcp = create_mcp_server(docpack_path)
    mcp.run(transport=cast(Literal["stdio", "sse", "streamable-http"], transport))


def run(source: str, transport: str = "stdio") -> None:
    """Freeze source and immediately serve (convenience command).

    Args:
        source: Path to folder or zip file
        transport: Transport protocol (stdio or sse)
    """
    import tempfile

    # Create temporary docpack
    with tempfile.NamedTemporaryFile(suffix=".docpack", delete=False) as f:
        output = f.name

    freeze(source, output)
    serve(output, transport)


def get_desktop_binary_path() -> Path | None:
    """Find the DocOS desktop binary."""
    install_path = Path.home() / ".doctown" / "desktop" / "DocOS"
    if install_path.exists():
        return install_path
    return None


def launch_windowed() -> None:
    """Launch the TUI in the native desktop app."""
    import subprocess

    binary = get_desktop_binary_path()
    if binary is None:
        logger.error("DocOS Desktop not installed.")
        logger.error("Get it here: https://doctown.app/download")
        sys.exit(1)

    subprocess.Popen([str(binary)], start_new_session=True)


def deck(windowed: bool = False) -> None:
    """Launch the Flight Deck TUI for interactive pipeline testing."""
    if windowed:
        launch_windowed()
        return

    from docpack.flight_deck import main as flight_deck_main

    flight_deck_main()


def info(docpack: str) -> None:
    """Show information about a docpack.

    Args:
        docpack: Path to .docpack file
    """
    docpack_path = Path(docpack)
    if not docpack_path.exists():
        logger.error(f"Docpack not found: {docpack}")
        sys.exit(1)

    store = DocPackStore(docpack_path)

    # Get metadata
    metadata = {}
    for key in ["source", "source_type", "created_at", "embedding_model"]:
        value = store.get_metadata(key)
        if value:
            metadata[key] = value

    # Get file stats
    files = store.list_files()
    text_files = [f for f in files if not f["is_binary"]]
    binary_files = [f for f in files if f["is_binary"]]

    print(f"DocPack: {docpack_path.name}")
    print(f"  Size: {docpack_path.stat().st_size / 1024:.1f} KB")
    print(f"")
    print(f"Metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    print(f"")
    print(f"Contents:")
    print(f"  Text files: {len(text_files)}")
    print(f"  Binary files: {len(binary_files)}")
    print(f"  Total: {len(files)}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="docpack",
        description="DocPack - The Universal Semantic Container",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # freeze command
    freeze_parser = subparsers.add_parser(
        "freeze",
        help="Freeze a folder or zip into a .docpack file",
    )
    freeze_parser.add_argument("source", help="Input folder or zip file path")
    freeze_parser.add_argument(
        "-o",
        "--output",
        default="output.docpack",
        help="Output .docpack path (default: output.docpack)",
    )

    # serve command
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start MCP server for a docpack",
    )
    serve_parser.add_argument("docpack", help="Path to .docpack file")
    serve_parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )

    # run command
    run_parser = subparsers.add_parser(
        "run",
        help="Freeze and serve in one step",
    )
    run_parser.add_argument("source", help="Input folder or zip file path")
    run_parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )

    # deck command
    deck_parser = subparsers.add_parser(
        "deck",
        help="Launch Flight Deck TUI for interactive testing",
    )
    deck_parser.add_argument(
        "--windowed",
        "-w",
        action="store_true",
        help="Launch in native desktop window",
    )

    # info command
    info_parser = subparsers.add_parser(
        "info",
        help="Show information about a docpack",
    )
    info_parser.add_argument("docpack", help="Path to .docpack file")

    args = parser.parse_args()

    if args.command == "freeze":
        freeze(args.source, args.output)
    elif args.command == "serve":
        serve(args.docpack, args.transport)
    elif args.command == "run":
        run(args.source, args.transport)
    elif args.command == "deck":
        deck(windowed=args.windowed)
    elif args.command == "info":
        info(args.docpack)


if __name__ == "__main__":
    main()
