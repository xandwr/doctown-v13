"""SQLite-backed storage for .docpack files."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from docpack.models import Chunk, Document
from docpack.storage.schema import SCHEMA


class DocPackStore:
    """SQLite-backed storage for .docpack files."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create schema if not exists."""
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    def store_document(self, doc: Document) -> None:
        """Store a document and its metadata."""
        with self.connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO files
                   (path, content, size_bytes, extension, is_binary)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    doc.metadata.path,
                    doc.content,
                    doc.metadata.size_bytes,
                    doc.metadata.extension,
                    1 if doc.metadata.is_binary else 0,
                ),
            )

    def store_chunks(self, chunks: list[Chunk]) -> list[int]:
        """Store chunks and return their IDs."""
        chunk_ids = []
        with self.connection() as conn:
            for chunk in chunks:
                cursor = conn.execute(
                    """INSERT INTO chunks (file_path, chunk_index, text, start_char, end_char)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        chunk.file_path,
                        chunk.chunk_index,
                        chunk.text,
                        chunk.start_char,
                        chunk.end_char,
                    ),
                )
                chunk_ids.append(cursor.lastrowid)
        return chunk_ids

    def store_embeddings(self, chunk_ids: list[int], embeddings: np.ndarray) -> None:
        """Store embeddings for chunks."""
        with self.connection() as conn:
            for chunk_id, embedding in zip(chunk_ids, embeddings):
                conn.execute(
                    "INSERT INTO vectors (chunk_id, embedding) VALUES (?, ?)",
                    (chunk_id, embedding.astype(np.float32).tobytes()),
                )

    def set_metadata(self, key: str, value: str) -> None:
        """Store a metadata key-value pair."""
        with self.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                (key, value),
            )

    def get_metadata(self, key: str) -> Optional[str]:
        """Retrieve a metadata value by key."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT value FROM metadata WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else None

    # Query methods for MCP tools

    def list_files(self, path_prefix: str = "") -> list[dict]:
        """List files matching prefix (for ls tool)."""
        with self.connection() as conn:
            cursor = conn.execute(
                """SELECT path, size_bytes, extension, is_binary
                   FROM files WHERE path LIKE ? ORDER BY path""",
                (f"{path_prefix}%",),
            )
            return [dict(row) for row in cursor]

    def read_file(self, path: str) -> Optional[dict]:
        """Read file content and metadata (for read tool)."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT path, content, size_bytes, extension, is_binary FROM files WHERE path = ?",
                (path,),
            ).fetchone()
            return dict(row) if row else None

    def recall(self, query_embedding: np.ndarray, limit: int = 10) -> list[dict]:
        """Find similar chunks by embedding (for recall tool)."""
        with self.connection() as conn:
            cursor = conn.execute(
                """SELECT c.id, c.file_path, c.text, v.embedding
                   FROM chunks c JOIN vectors v ON c.id = v.chunk_id"""
            )

            results = []
            for row in cursor:
                stored_emb = np.frombuffer(row["embedding"], dtype=np.float32)
                similarity = self._cosine_similarity(query_embedding, stored_emb)
                results.append(
                    {
                        "file_path": row["file_path"],
                        "text": row["text"],
                        "similarity": float(similarity),
                    }
                )

            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:limit]

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
