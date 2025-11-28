# DocPack

**The Universal Semantic Container**

*Ingest Chaos. Freeze State. Query Everything.*

---

## What is a `.docpack`?

A `.docpack` is a standard SQLite database—a single, portable file that works anywhere.

It contains:

- **The Filesystem**: Raw data preserved exactly as it was (text, code, logs)
- **The Vector Map**: Mathematical index linking concepts together (e.g., "flour" → "baking", `auth_token` → `login.rs`)

No internet connection. No vector database server. Just the file.

## Philosophy

Traditional AI systems try to "read" and "summarize" your data during import. This is slow, expensive, and prone to hallucinations.

DocPack takes a different approach:

| Phase | What Happens |
|-------|--------------|
| **Ingest (Freezing)** | Map the territory. Don't write the travel guide. Fast, deterministic, offline. |
| **Query (Thawing)** | Understanding happens only when you ask. An AI Agent enters the frozen snapshot and explores data exactly as it exists. |

---

## Installation

**Prerequisites:** Python 3.12+

```bash
# Using uv (recommended)
uv sync

# Or pip
pip install -e .
```

## Quick Start

```bash
# Freeze a folder or zip into a queryable docpack
docpack freeze ./my-project -o project.docpack

# Start MCP server for AI agents
docpack serve project.docpack

# One-shot: freeze + serve (uses temp file)
docpack run ./my-project

# Interactive TUI for testing
docpack deck

# Inspect a docpack
docpack info project.docpack
```

---

## Architecture

```
src/docpack/
├── cli.py              # Command-line interface
├── flight_deck.py      # Interactive TUI (Textual)
├── chunkers/           # Text segmentation (paragraph-based)
├── embedders/          # Vector embeddings (sentence-transformers)
├── ingesters/          # Input handlers (folder, zip)
├── models/             # Data classes (Document, Chunk, FileMetadata)
├── protocols/          # Extensibility interfaces
├── server/             # MCP server implementation
├── storage/            # SQLite database layer
└── utils/              # Binary detection, helpers

desktop/                # Native desktop app (Tauri + xterm.js)
├── src/                # Frontend terminal emulator
└── src-tauri/          # Rust PTY backend
```

### Processing Pipeline

1. **Ingest** — Walk directories or extract zips, detect binary vs text
2. **Chunk** — Split text on paragraph boundaries, merge small fragments
3. **Embed** — Generate 384-dim vectors via `all-MiniLM-L6-v2`
4. **Store** — Write to SQLite with indexed tables

### MCP Server Tools

When serving a docpack, AI agents get three tools:

| Tool | Description |
|------|-------------|
| `ls(path)` | List directory contents with file sizes |
| `read(path)` | Read file content (text) or metadata (binary) |
| `recall(query, limit)` | Semantic search via embedding similarity |

### Database Schema

```sql
files (path, content, size_bytes, extension, is_binary)
chunks (id, file_path, chunk_index, text, start_char, end_char)
vectors (chunk_id, embedding)
metadata (key, value)
```

---

## Desktop App

Native GUI wrapper using Tauri + xterm.js:

```bash
cd desktop
npm install
npm run tauri:dev    # Development
npm run tauri:build  # Production binary
```

Spawns a pseudo-terminal running the Flight Deck TUI in a native window.

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Python** | sentence-transformers, mcp, numpy, textual |
| **Rust/Node** | Tauri, portable-pty, xterm.js, Vite |

## Design Principles

- **Protocol-based extensibility** — Swap chunkers, embedders, ingesters without inheritance
- **Deterministic processing** — No network calls during freeze, reproducible embeddings
- **One process = one docpack** — Prevents context pollution between document universes
- **Lazy loading** — Models loaded on first use, not at import
