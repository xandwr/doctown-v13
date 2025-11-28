"""Database schema for .docpack files."""

SCHEMA = """
-- File system table: stores file metadata and content
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    content TEXT,              -- NULL for binary files
    size_bytes INTEGER NOT NULL,
    extension TEXT,
    is_binary INTEGER NOT NULL DEFAULT 0
);

-- Chunks table: stores text chunks for semantic search
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    FOREIGN KEY (file_path) REFERENCES files(path)
);

-- Vectors table: stores embeddings
CREATE TABLE IF NOT EXISTS vectors (
    chunk_id INTEGER PRIMARY KEY,
    embedding BLOB NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id)
);

-- Metadata table: stores docpack metadata
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_path);
"""
