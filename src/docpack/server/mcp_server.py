"""FastMCP server implementation for DocPack."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from docpack.embedders import SentenceTransformerEmbedder
from docpack.storage import DocPackStore


def create_mcp_server(docpack_path: Path) -> FastMCP:
    """Create an MCP server for a specific docpack.

    Design: 1 process = 1 docpack. This prevents context pollution
    between different document universes.

    Args:
        docpack_path: Path to the .docpack file to serve

    Returns:
        Configured FastMCP server instance
    """
    mcp = FastMCP(
        name="docpack",
    )

    # Initialize store and embedder (loaded once per server)
    store = DocPackStore(docpack_path)
    embedder = SentenceTransformerEmbedder()

    @mcp.tool()
    def ls(path: str = "") -> str:
        """List files in the docpack.

        Args:
            path: Optional path prefix to filter results (e.g., "src/" to list only files in src/)

        Returns:
            Formatted list of files with size and type information
        """
        files = store.list_files(path)

        if not files:
            return f"No files found matching '{path}'"

        lines = []
        for f in files:
            size = f["size_bytes"]
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            file_type = "[binary]" if f["is_binary"] else ""
            lines.append(f"{f['path']:<60} {size_str:>10} {file_type}")

        return "\n".join(lines)

    @mcp.tool()
    def read(path: str) -> str:
        """Read a file's content from the docpack.

        Args:
            path: Full path to the file (as shown in ls output)

        Returns:
            File content for text files, or metadata for binary files
        """
        result = store.read_file(path)

        if result is None:
            return f"Error: File not found: {path}"

        if result["is_binary"]:
            return (
                f"[Binary file]\n"
                f"  Path: {result['path']}\n"
                f"  Size: {result['size_bytes']} bytes\n"
                f"  Extension: {result['extension']}"
            )

        return result["content"]

    @mcp.tool()
    def recall(query: str, limit: int = 10) -> str:
        """Semantic search across the docpack.

        Use this to find relevant content by concept, not just keyword.
        For example: "authentication logic" might find login.py even if
        it doesn't contain the word "authentication".

        Args:
            query: Natural language description of what you're looking for
            limit: Maximum number of results to return (default: 10)

        Returns:
            Ranked list of relevant file chunks with similarity scores
        """
        query_embedding = embedder.embed([query])[0]
        results = store.recall(query_embedding, limit=limit)

        if not results:
            return f"No results found for: {query}"

        lines = []
        for i, r in enumerate(results, 1):
            score = r["similarity"]
            # Truncate long text snippets
            text = r["text"][:200].replace("\n", " ")
            if len(r["text"]) > 200:
                text += "..."

            lines.append(f"{i}. [{score:.3f}] {r['file_path']}")
            lines.append(f"   {text}")
            lines.append("")

        return "\n".join(lines)

    return mcp
