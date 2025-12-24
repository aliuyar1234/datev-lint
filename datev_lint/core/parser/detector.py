"""
Format detection for DATEV files.

Detects whether a file is a valid DATEV EXTF file.
"""

from __future__ import annotations

import re

from .models import DetectedFormat

# Pattern to match EXTF header start
EXTF_PATTERN = re.compile(
    rb'^["\']?EXTF["\']?\s*[;,]',
    re.IGNORECASE,
)

# Pattern for ASCII format (legacy)
ASCII_PATTERN = re.compile(
    rb'^["\']?ASCII["\']?\s*[;,]',
    re.IGNORECASE,
)


def detect_format(data: bytes) -> DetectedFormat:
    """
    Detect if data is DATEV EXTF format.

    Checks the first line of the file for the EXTF or ASCII marker.

    Args:
        data: First ~1KB of file content

    Returns:
        DetectedFormat enum value
    """
    # Skip BOM if present
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    elif data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        # Handle UTF-16 BOM (skip 2 bytes)
        data = data[2:]

    # Get first line (handle both \r\n and \n)
    first_line_end = data.find(b"\r")
    if first_line_end == -1:
        first_line_end = data.find(b"\n")
    if first_line_end == -1:
        first_line_end = min(len(data), 1024)

    first_line = data[:first_line_end]

    # Check for EXTF format
    if EXTF_PATTERN.match(first_line):
        return DetectedFormat.DATEV_FORMAT

    # Check for ASCII format (legacy)
    if ASCII_PATTERN.match(first_line):
        return DetectedFormat.ASCII_STANDARD

    return DetectedFormat.UNKNOWN
