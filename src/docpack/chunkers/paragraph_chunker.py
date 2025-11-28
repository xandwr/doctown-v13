"""Paragraph-based chunking strategy."""

from docpack.models import Chunk


class ParagraphChunker:
    """Default chunking: split by \\n\\n, hard-split >1000, merge <50.

    This strategy balances semantic coherence with chunk size limits:
    - Splits on paragraph boundaries (double newlines)
    - Hard-splits very long paragraphs to stay under max size
    - Merges tiny fragments to avoid noise
    """

    MAX_CHUNK_SIZE = 1000
    MIN_CHUNK_SIZE = 50

    def chunk(self, text: str, file_path: str) -> list[Chunk]:
        """Split text into chunks with metadata.

        Args:
            text: The text content to chunk
            file_path: Path to the source file (for metadata)

        Returns:
            List of Chunk objects with position information
        """
        if not text or not text.strip():
            return []

        # Split by double newlines (paragraph boundaries)
        raw_chunks = text.split("\n\n")

        processed: list[tuple[str, int]] = []  # (text, start_char)
        char_offset = 0
        buffer = ""
        buffer_start = 0

        for raw in raw_chunks:
            chunk_start = char_offset

            # Handle chunks over MAX_CHUNK_SIZE: hard-split
            if len(raw) > self.MAX_CHUNK_SIZE:
                # Flush buffer first
                if buffer:
                    processed.append((buffer, buffer_start))
                    buffer = ""

                # Hard-split the long chunk
                for i in range(0, len(raw), self.MAX_CHUNK_SIZE):
                    sub = raw[i : i + self.MAX_CHUNK_SIZE]
                    processed.append((sub, chunk_start + i))

            # Handle chunks under MIN_CHUNK_SIZE: merge with buffer
            elif len(raw) < self.MIN_CHUNK_SIZE:
                if buffer:
                    buffer += "\n\n" + raw
                else:
                    buffer = raw
                    buffer_start = chunk_start

                # Flush buffer if it's now big enough
                if len(buffer) >= self.MIN_CHUNK_SIZE:
                    processed.append((buffer, buffer_start))
                    buffer = ""

            # Normal-sized chunk
            else:
                # Flush buffer first
                if buffer:
                    processed.append((buffer, buffer_start))
                    buffer = ""
                processed.append((raw, chunk_start))

            # Move offset past this chunk + the separator
            char_offset += len(raw) + 2  # +2 for "\n\n"

        # Don't forget trailing buffer
        if buffer:
            processed.append((buffer, buffer_start))

        # Convert to Chunk objects
        chunks = []
        for idx, (chunk_text, start_char) in enumerate(processed):
            # Skip empty chunks
            if not chunk_text.strip():
                continue

            chunks.append(
                Chunk(
                    text=chunk_text,
                    file_path=file_path,
                    chunk_index=idx,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text),
                )
            )

        return chunks
