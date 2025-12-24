"""
Encoding detection for DATEV files.

DATEV files can be encoded in:
- UTF-8 with BOM (preferred)
- UTF-8 without BOM
- Windows-1252 (legacy)

This module provides robust encoding detection using charset-normalizer.
"""

from __future__ import annotations

from charset_normalizer import from_bytes

# Size of data to use for encoding detection (8KB is usually sufficient)
DETECTION_SAMPLE_SIZE = 8192


def detect_encoding(data: bytes) -> str:
    """
    Detect encoding of DATEV file data.

    Detection priority:
    1. UTF-8 BOM (explicit marker)
    2. charset-normalizer detection
    3. Fallback to Windows-1252

    Args:
        data: First ~8KB of file content (or full file if smaller)

    Returns:
        Encoding name: "utf-8-sig", "utf-8", or "windows-1252"
    """
    # Check for UTF-8 BOM first
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

    # Check for UTF-16 BOMs (not common but possible)
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        # UTF-16 is not typical for DATEV, but handle it
        return "utf-16"

    # Use charset-normalizer for detection
    results = from_bytes(data[:DETECTION_SAMPLE_SIZE])

    if results:
        best = results.best()
        if best is not None:
            encoding = best.encoding.lower()

            # Normalize encoding names
            if encoding in ("ascii", "utf-8", "utf8"):
                return "utf-8"

            if encoding in ("cp1252", "windows-1252", "latin-1", "iso-8859-1"):
                return "windows-1252"

            # Return detected encoding for other cases
            return encoding

    # Fallback: try to decode as UTF-8, fall back to Windows-1252
    try:
        data[:DETECTION_SAMPLE_SIZE].decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "windows-1252"


def decode_with_fallback(data: bytes, encoding: str) -> str:
    """
    Decode bytes with encoding, using replacement for invalid sequences.

    Args:
        data: Bytes to decode
        encoding: Target encoding

    Returns:
        Decoded string (with replacement characters for invalid bytes)
    """
    try:
        return data.decode(encoding)
    except UnicodeDecodeError:
        # Fall back to replacement mode
        return data.decode(encoding, errors="replace")
