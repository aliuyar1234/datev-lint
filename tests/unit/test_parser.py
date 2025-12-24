"""Tests for main parser functionality."""

from pathlib import Path

import pytest

from datev_lint.core.parser import (
    DetectedFormat,
    ParserError,
    parse_bytes,
    parse_file,
)


class TestParseFile:
    """Tests for parse_file function."""

    def test_parse_valid_file(self, valid_minimal_700: Path) -> None:
        """Test parsing a valid minimal DATEV file."""
        result = parse_file(valid_minimal_700)

        assert result.detected_format == DetectedFormat.DATEV_FORMAT
        assert result.header.header_version == 700
        assert result.header.format_category == 21
        assert result.header.format_name == "Buchungsstapel"

    def test_header_metadata(self, valid_minimal_700: Path) -> None:
        """Test that header metadata is correctly parsed."""
        result = parse_file(valid_minimal_700)

        # Leading zeros preserved as strings
        assert result.header.beraternummer == "00001"
        assert result.header.mandantennummer == "00002"

        # Period dates
        assert result.header.period_from is not None
        assert result.header.period_to is not None

    def test_row_iteration(self, valid_minimal_700: Path) -> None:
        """Test iterating over rows."""
        result = parse_file(valid_minimal_700)

        rows = []
        for item in result.rows:
            if isinstance(item, ParserError):
                continue
            rows.append(item)

        assert len(rows) == 10

    def test_leading_zeros_in_konto(self, leading_zero_konto: Path) -> None:
        """Test that leading zeros in account numbers are preserved."""
        result = parse_file(leading_zero_konto)

        for item in result.rows:
            if isinstance(item, ParserError):
                continue
            # Konto should start with leading zeros
            assert item.konto is not None
            assert item.konto.startswith("000"), f"Leading zeros lost: {item.konto}"

    def test_file_not_found(self) -> None:
        """Test that FileNotFoundError is raised for missing files."""
        with pytest.raises(FileNotFoundError):
            parse_file("nonexistent_file.csv")


class TestParseBytes:
    """Tests for parse_bytes function."""

    def test_minimal_valid_data(self) -> None:
        """Test parsing minimal valid DATEV data."""
        data = b'''"EXTF";700;21;"Buchungsstapel";13
"Umsatz";"Konto"
"100,00";"1200"
'''
        result = parse_bytes(data, "<test>")

        assert result.header.header_version == 700
        assert result.header.format_category == 21

    def test_empty_data(self) -> None:
        """Test parsing empty data."""
        result = parse_bytes(b"", "<test>")
        assert result.has_fatal_errors

    def test_header_only(self) -> None:
        """Test parsing with only header line."""
        data = b'"EXTF";700;21;"Test";1'
        result = parse_bytes(data, "<test>")
        assert result.has_fatal_errors


class TestMaterialize:
    """Tests for ParseResult.materialize method."""

    def test_materialize_rows(self, valid_minimal_700: Path) -> None:
        """Test materializing all rows."""
        result = parse_file(valid_minimal_700)
        rows, errors = result.materialize()

        assert len(rows) == 10
        # Check that we can access row properties
        assert rows[0].konto is not None


class TestEncodingDetection:
    """Tests for encoding detection during parsing."""

    def test_utf8_bom_encoding(self, encoding_utf8_bom: Path) -> None:
        """Test that UTF-8 BOM files are parsed correctly."""
        result = parse_file(encoding_utf8_bom)

        assert result.encoding == "utf-8-sig"
        # Should parse without fatal errors
        assert not result.has_fatal_errors
