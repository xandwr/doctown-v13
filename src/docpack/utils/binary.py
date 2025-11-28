"""Binary file detection utilities."""

from pathlib import Path

# Common binary file extensions
BINARY_EXTENSIONS = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg", ".tiff",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods",
    # Archives
    ".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz",
    # Executables
    ".exe", ".dll", ".so", ".dylib", ".bin",
    # Media
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac", ".mkv", ".webm",
    # Compiled
    ".pyc", ".pyo", ".class", ".o", ".obj", ".wasm",
    # Fonts
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    # Other
    ".db", ".sqlite", ".sqlite3", ".docpack",
}


def is_binary_extension(path: str | Path) -> bool:
    """Check if file extension indicates binary content."""
    return Path(path).suffix.lower() in BINARY_EXTENSIONS


def is_binary_content(content: bytes, sample_size: int = 8192) -> bool:
    """Detect if content is binary by checking for null bytes and non-text chars.

    Args:
        content: Raw file content
        sample_size: Number of bytes to sample from the start

    Returns:
        True if content appears to be binary
    """
    if not content:
        return False

    sample = content[:sample_size]

    # Check for null bytes (strong binary indicator)
    if b"\x00" in sample:
        return True

    # Check ratio of non-printable characters
    # Printable ASCII + common whitespace
    text_chars = set(range(32, 127)) | {9, 10, 13}  # printable + tab, LF, CR
    non_text = sum(1 for byte in sample if byte not in text_chars)

    # If more than 30% non-text, treat as binary
    return (non_text / len(sample)) > 0.30


def detect_binary(path: str | Path, content: bytes) -> bool:
    """Detect if a file is binary using both extension and content analysis.

    Args:
        path: File path (for extension check)
        content: Raw file content

    Returns:
        True if file is binary
    """
    # Fast path: check extension first
    if is_binary_extension(path):
        return True

    # Fall back to content analysis
    return is_binary_content(content)
