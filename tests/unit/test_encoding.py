"""Tests for encoding detection."""

from pathlib import Path

import pytest

from datev_lint.core.parser import detect_encoding


class TestDetectEncoding:
    """Tests for detect_encoding function."""

    def test_utf8_with_bom(self, encoding_utf8_bom: Path) -> None:
        """Test detection of UTF-8 with BOM."""
        data = encoding_utf8_bom.read_bytes()
        assert detect_encoding(data) == "utf-8-sig"

    def test_windows1252(self, encoding_windows1252: Path) -> None:
        """Test detection of Windows-1252."""
        data = encoding_windows1252.read_bytes()
        encoding = detect_encoding(data)
        # charset-normalizer might detect as various encodings
        assert encoding in ("windows-1252", "utf-8", "cp1250", "iso-8859-1", "latin-1")

    def test_plain_utf8(self) -> None:
        """Test detection of plain UTF-8 without BOM."""
        data = b'"EXTF";700;21;'
        assert detect_encoding(data) in ("utf-8", "ascii")

    def test_empty_data(self) -> None:
        """Test with empty data falls back gracefully."""
        encoding = detect_encoding(b"")
        # Empty data should return some valid encoding
        assert encoding is not None
