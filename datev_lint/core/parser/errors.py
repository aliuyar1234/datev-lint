"""
Parser error models.

This module defines structured errors for the DATEV parser.
All parser errors use error codes from the DVL-XXX-NNN taxonomy.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(Enum):
    """Error severity levels."""

    FATAL = "fatal"  # Cannot continue parsing
    ERROR = "error"  # Likely import failure
    WARN = "warn"  # Risky, might cause issues
    INFO = "info"  # Informational


class Location(BaseModel, frozen=True):
    """Error location in file."""

    file: str | None = None
    line_no: int | None = None
    column: int | None = None
    field: str | None = None

    def __str__(self) -> str:
        """Format location for display."""
        parts = []
        if self.file:
            parts.append(self.file)
        if self.line_no is not None:
            parts.append(f"line {self.line_no}")
        if self.column is not None:
            parts.append(f"col {self.column}")
        if self.field:
            parts.append(f"field '{self.field}'")
        return ", ".join(parts) if parts else "<unknown>"


class ParserError(BaseModel, frozen=True):
    """
    Structured parser error.

    Uses error codes from the Error Taxonomy (DVL-XXX-NNN).
    Error domains:
    - DVL-ENC-*: Encoding errors
    - DVL-CSV-*: CSV/tokenization errors
    - DVL-HDR-*: Header parsing errors
    - DVL-DATE-*: Date parsing errors
    - DVL-FIELD-*: Field validation errors
    """

    code: str = Field(
        pattern=r"^DVL-[A-Z]{2,5}-\d{3}$",
        description="Error code, e.g., 'DVL-ENC-001'",
    )
    severity: Severity
    title: str = Field(description="Short error title")
    message: str = Field(description="Detailed error message")
    location: Location = Field(
        default_factory=Location,
        description="Where the error occurred",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (raw_value, expected, etc.)",
    )

    # Factory methods for common error creation patterns

    @classmethod
    def fatal(
        cls,
        code: str,
        title: str,
        message: str,
        *,
        location: Location | None = None,
        context: dict[str, Any] | None = None,
    ) -> ParserError:
        """Create a FATAL severity error."""
        return cls(
            code=code,
            severity=Severity.FATAL,
            title=title,
            message=message,
            location=location or Location(),
            context=context or {},
        )

    @classmethod
    def error(
        cls,
        code: str,
        title: str,
        message: str,
        *,
        location: Location | None = None,
        context: dict[str, Any] | None = None,
    ) -> ParserError:
        """Create an ERROR severity error."""
        return cls(
            code=code,
            severity=Severity.ERROR,
            title=title,
            message=message,
            location=location or Location(),
            context=context or {},
        )

    @classmethod
    def warn(
        cls,
        code: str,
        title: str,
        message: str,
        *,
        location: Location | None = None,
        context: dict[str, Any] | None = None,
    ) -> ParserError:
        """Create a WARN severity error."""
        return cls(
            code=code,
            severity=Severity.WARN,
            title=title,
            message=message,
            location=location or Location(),
            context=context or {},
        )

    @classmethod
    def info(
        cls,
        code: str,
        title: str,
        message: str,
        *,
        location: Location | None = None,
        context: dict[str, Any] | None = None,
    ) -> ParserError:
        """Create an INFO severity error."""
        return cls(
            code=code,
            severity=Severity.INFO,
            title=title,
            message=message,
            location=location or Location(),
            context=context or {},
        )

    def __str__(self) -> str:
        """Format error for display."""
        return f"[{self.code}] {self.severity.value.upper()}: {self.title} - {self.message}"


# =============================================================================
# Error Codes Registry
# =============================================================================

PARSER_ERROR_CODES: dict[str, str] = {
    # Encoding errors
    "DVL-ENC-001": "Encoding unknown or unreadable",
    "DVL-ENC-002": "Invalid byte sequence for detected encoding",
    # CSV errors
    "DVL-CSV-001": "Delimiter mismatch or malformed quotes",
    "DVL-CSV-002": "Unexpected end of file in quoted field",
    "DVL-CSV-003": "Invalid character in field",
    "DVL-CSV-004": "Line too long (exceeds maximum)",
    # Header errors
    "DVL-HDR-001": "Missing EXTF or wrong format category",
    "DVL-HDR-002": "Invalid header version",
    "DVL-HDR-003": "Invalid format category (expected 21 for Buchungsstapel)",
    "DVL-HDR-004": "Invalid period dates",
    "DVL-HDR-005": "Missing required header field",
    "DVL-HDR-006": "Invalid header field value",
    # Column errors
    "DVL-COL-001": "Missing required column",
    "DVL-COL-002": "Duplicate column name",
    "DVL-COL-003": "Unknown column (not in field dictionary)",
    # Date errors
    "DVL-DATE-001": "Invalid TTMM format",
    "DVL-DATE-002": "TTMM date is ambiguous (could be multiple years)",
    "DVL-DATE-003": "Date outside header period",
    "DVL-DATE-004": "No context data for year derivation",
    # Field errors
    "DVL-FIELD-001": "Required field missing",
    "DVL-FIELD-002": "Account number length invalid",
    "DVL-FIELD-003": "Invalid decimal format",
    "DVL-FIELD-004": "Field exceeds maximum length",
    "DVL-FIELD-005": "Invalid character in field",
    # Row errors
    "DVL-ROW-001": "Too many rows (exceeds 99,999)",
    "DVL-ROW-002": "Row checksum mismatch",
}


def get_error_description(code: str) -> str | None:
    """Get the description for an error code."""
    return PARSER_ERROR_CODES.get(code)
