"""
Parser Core API Contract

This file defines the public API for the datev-lint parser.
All functions and classes here are part of the stable public API.

Usage:
    from datev_lint.core.parser import parse_file, ParseResult, DatevHeader

Version: 1.0.0
"""

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Optional, Protocol

# =============================================================================
# Enums
# =============================================================================


class DetectedFormat(Enum):
    """Result of format detection."""

    DATEV_FORMAT = "datev"
    ASCII_STANDARD = "ascii"
    UNKNOWN = "unknown"


class Severity(Enum):
    """Error severity levels."""

    FATAL = "fatal"
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


class DateConfidence(Enum):
    """Confidence level for TTMM year derivation."""

    HIGH = "high"
    MEDIUM = "medium"
    AMBIGUOUS = "ambiguous"
    FAILED = "failed"
    UNKNOWN = "unknown"


# =============================================================================
# Data Classes (Protocols for type hints)
# =============================================================================


class DatevHeader(Protocol):
    """DATEV EXTF header from line 1."""

    kennzeichen: str
    header_version: int
    format_category: int
    format_name: str
    format_version: int
    created_at: datetime | None
    beraternummer: str | None  # ALWAYS string!
    mandantennummer: str | None  # ALWAYS string!
    fiscal_year_start: date | None
    period_from: date | None
    period_to: date | None
    account_length: int | None
    currency: str | None
    festschreibung: int | None
    raw_tokens: list[str]


class DerivedDate(Protocol):
    """Result of TTMM date year derivation."""

    raw_ttmm: str
    day: int
    month: int
    year: int | None
    derived_date: date | None
    confidence: DateConfidence
    warning_code: str | None


class BookingRow(Protocol):
    """A single booking row."""

    row_no: int
    line_span: tuple[int, int]
    fields_raw: dict[str, str]
    fields_typed: dict[str, Any]
    checksum: str
    raw_tokens: list[str]

    def get_raw(self, field_id: str) -> str | None: ...
    def get_typed(self, field_id: str) -> Any | None: ...

    @property
    def konto(self) -> str | None: ...

    @property
    def gegenkonto(self) -> str | None: ...

    @property
    def umsatz(self) -> Decimal | None: ...

    @property
    def belegdatum(self) -> DerivedDate | None: ...


class ParserError(Protocol):
    """Structured parser error."""

    code: str
    severity: Severity
    title: str
    message: str
    location: dict[str, Any]
    context: dict[str, Any]


class ParseResult(Protocol):
    """Result of parsing a DATEV file."""

    file_path: Path
    detected_format: DetectedFormat
    encoding: str
    header: DatevHeader
    header_errors: list[ParserError]

    @property
    def rows(self) -> Iterator[BookingRow | ParserError]:
        """Streaming iterator over rows."""
        ...

    def materialize(self) -> tuple[list[BookingRow], list[ParserError]]:
        """Materialize all rows into memory."""
        ...


# =============================================================================
# Public API Functions
# =============================================================================


def parse_file(path: Path | str) -> ParseResult:
    """
    Parse a DATEV EXTF file.

    Args:
        path: Path to the DATEV file

    Returns:
        ParseResult with header and streaming row iterator

    Raises:
        FileNotFoundError: If file does not exist
        ParserError (via header_errors): If file cannot be parsed

    Example:
        result = parse_file("EXTF_Buchungsstapel.csv")
        print(f"Version: {result.header.header_version}")
        for row in result.rows:
            if isinstance(row, ParserError):
                print(f"Error: {row.code}")
            else:
                print(f"Konto: {row.konto}")
    """
    ...


def parse_bytes(data: bytes, filename: str = "<bytes>") -> ParseResult:
    """
    Parse DATEV data from bytes.

    Args:
        data: Raw file content
        filename: Optional filename for error messages

    Returns:
        ParseResult with header and streaming row iterator
    """
    ...


def parse_stream(stream: BinaryIO, filename: str = "<stream>") -> ParseResult:
    """
    Parse DATEV data from a binary stream.

    Args:
        stream: Binary file-like object
        filename: Optional filename for error messages

    Returns:
        ParseResult with header and streaming row iterator
    """
    ...


def detect_encoding(data: bytes) -> str:
    """
    Detect encoding of DATEV file.

    Args:
        data: First ~8KB of file content

    Returns:
        Encoding name: "utf-8-sig", "utf-8", or "windows-1252"
    """
    ...


def detect_format(data: bytes) -> DetectedFormat:
    """
    Detect if data is DATEV EXTF format.

    Args:
        data: First ~1KB of file content

    Returns:
        DetectedFormat enum value
    """
    ...


def derive_year(
    ttmm: str,
    fiscal_year_start: date | None = None,
    period_from: date | None = None,
    period_to: date | None = None,
) -> DerivedDate:
    """
    Derive year for TTMM date format.

    The TTMM format contains only day (TT) and month (MM).
    This function derives the year based on context.

    Args:
        ttmm: 4-digit TTMM string, e.g., "1503" for March 15
        fiscal_year_start: Optional fiscal year start date
        period_from: Optional period start date
        period_to: Optional period end date

    Returns:
        DerivedDate with year and confidence level

    Example:
        result = derive_year("1503", period_from=date(2025, 1, 1), period_to=date(2025, 12, 31))
        print(f"Date: {result.derived_date}")  # 2025-03-15
        print(f"Confidence: {result.confidence}")  # HIGH
    """
    ...


# =============================================================================
# Field Dictionary API
# =============================================================================


def get_field_dictionary() -> "FieldDictionary":
    """
    Get the Field Dictionary (Single Source of Truth).

    Returns:
        FieldDictionary with all field definitions
    """
    ...


class FieldDictionary(Protocol):
    """Field Dictionary for DATEV fields."""

    fields: dict[str, "FieldDefinition"]
    version: str

    def get_by_synonym(self, label: str) -> Optional["FieldDefinition"]: ...
    def get_by_id(self, canonical_id: str) -> Optional["FieldDefinition"]: ...


class FieldDefinition(Protocol):
    """Definition of a DATEV field."""

    canonical_id: str
    synonyms: list[str]
    required: bool
    type: str
    max_length: int | None
    charset: str | None
    fix_strategies: list[str]


# =============================================================================
# Error Codes (Parser Domain)
# =============================================================================

PARSER_ERROR_CODES = {
    # Encoding errors
    "DVL-ENC-001": "Encoding unknown or unreadable",
    # CSV errors
    "DVL-CSV-001": "Delimiter mismatch or malformed quotes",
    "DVL-CSV-002": "Unexpected end of file in quoted field",
    "DVL-CSV-003": "Invalid character in field",
    # Header errors
    "DVL-HDR-001": "Missing EXTF or wrong format category",
    "DVL-HDR-002": "Invalid header version",
    "DVL-HDR-003": "Invalid format category (expected 21 for Buchungsstapel)",
    "DVL-HDR-004": "Invalid period dates",
    # Date errors
    "DVL-DATE-001": "Invalid TTMM format",
    "DVL-DATE-AMBIG-001": "TTMM date is ambiguous (could be multiple years)",
    "DVL-DATE-RANGE-001": "Date outside header period",
    "DVL-DATE-NOCTX-001": "No context data for year derivation",
    # Field errors
    "DVL-FIELD-001": "Required field missing",
    "DVL-FIELD-002": "Account number length invalid",
    "DVL-FIELD-003": "Invalid decimal format",
}
