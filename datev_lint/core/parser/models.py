"""
Parser data models.

Core data models for DATEV file parsing.

CRITICAL DESIGN DECISIONS:
- beraternummer and mandantennummer are ALWAYS strings (preserve leading zeros)
- konto and gegenkonto in fields_raw are ALWAYS strings (preserve leading zeros)
- All models are frozen (immutable) for safety
- BookingRow has both fields_raw (strings) and fields_typed (converted values)
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from collections.abc import Iterator

# =============================================================================
# Enums
# =============================================================================


class DetectedFormat(Enum):
    """Result of format detection."""

    DATEV_FORMAT = "datev"  # EXTF file
    ASCII_STANDARD = "ascii"  # DATEV ASCII format (legacy)
    UNKNOWN = "unknown"  # Cannot determine


class DateConfidence(Enum):
    """Confidence level for TTMM year derivation."""

    HIGH = "high"  # Unambiguous, within period
    MEDIUM = "medium"  # Derived from fiscal year
    AMBIGUOUS = "ambiguous"  # Could be multiple years
    FAILED = "failed"  # Cannot derive, out of range
    UNKNOWN = "unknown"  # No context data available


# =============================================================================
# Basic Models
# =============================================================================


class Dialect(BaseModel, frozen=True):
    """CSV dialect settings for DATEV files."""

    delimiter: str = ";"
    quotechar: str = '"'
    escapechar: str = '"'  # Doubled quotes for escaping
    lineterminator: str = "\r"  # CR terminates lines, LF can appear in quoted fields

    model_config = {"frozen": True}


class DerivedDate(BaseModel, frozen=True):
    """
    Result of TTMM date year derivation.

    The TTMM format only contains day and month (e.g., "1503" = March 15).
    The year must be derived from context (period, fiscal year).
    """

    raw_ttmm: str = Field(
        description="Original TTMM value",
    )
    day: int = Field(ge=0, le=31)  # 0 allowed for invalid input
    month: int = Field(ge=0, le=12)  # 0 allowed for invalid input
    year: int | None = Field(
        default=None,
        description="Derived year, None if derivation failed",
    )
    derived_date: date | None = Field(
        default=None,
        description="Complete date if derivation succeeded",
    )
    confidence: DateConfidence
    warning_code: str | None = Field(
        default=None,
        description="Warning/error code if not HIGH confidence",
    )

    model_config = {"frozen": True}


# =============================================================================
# Header Model
# =============================================================================


class DatevHeader(BaseModel, frozen=True):
    """
    DATEV EXTF header (line 1).

    CRITICAL: beraternummer and mandantennummer are STRINGS, never int!
    Leading zeros must be preserved.
    """

    # Pflichtfelder
    kennzeichen: str = Field(
        pattern=r"^EXTF$",
        description="Must be 'EXTF' for DATEV format",
    )
    header_version: int = Field(
        ge=500,
        le=999,
        description="Header version (700 = current, 510 = legacy)",
    )
    format_category: int = Field(
        description="21 = Buchungsstapel, 16 = Debitoren, etc.",
    )
    format_name: str = Field(
        description="e.g., 'Buchungsstapel'",
    )
    format_version: int = Field(
        description="Format version within category",
    )

    # Optionale Metadaten
    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp",
    )

    # KRITISCH: Immer String!
    beraternummer: str | None = Field(
        default=None,
        pattern=r"^\d*$",
        description="Berater ID - MUST be string to preserve leading zeros",
    )
    mandantennummer: str | None = Field(
        default=None,
        pattern=r"^\d*$",
        description="Mandant ID - MUST be string to preserve leading zeros",
    )

    # Zeitraum
    fiscal_year_start: date | None = Field(
        default=None,
        description="Start of fiscal year (WJ-Beginn)",
    )
    period_from: date | None = Field(
        default=None,
        description="Period start date",
    )
    period_to: date | None = Field(
        default=None,
        description="Period end date",
    )

    # Kontenkonfiguration
    account_length: int | None = Field(
        default=None,
        ge=4,
        le=9,
        description="Account number length (4-9 digits)",
    )
    currency: str | None = Field(
        default=None,
        max_length=3,
        description="Currency code (WKZ), e.g., 'EUR'",
    )

    # Festschreibung
    festschreibung: int | None = Field(
        default=None,
        ge=0,
        le=1,
        description="0 = not locked, 1 = locked",
    )

    # Weitere optionale Felder
    bezeichnung: str | None = Field(
        default=None,
        description="Batch designation",
    )
    diktat_kuerzel: str | None = Field(
        default=None,
        description="Dictation abbreviation",
    )
    buchungstyp: int | None = Field(
        default=None,
        description="Booking type",
    )
    rechnungslegungszweck: int | None = Field(
        default=None,
        description="Accounting purpose",
    )

    # Roundtrip-Daten
    raw_tokens: list[str] = Field(
        default_factory=list,
        description="Original tokens for roundtrip writing",
    )

    model_config = {"frozen": True}


# =============================================================================
# Column Mapping Models
# =============================================================================


class ColumnMapping(BaseModel, frozen=True):
    """Maps a column index to a canonical field ID."""

    index: int
    canonical_id: str
    original_label: str

    model_config = {"frozen": True}


class ColumnMappings(BaseModel, frozen=True):
    """Complete column mapping for a file."""

    mappings: list[ColumnMapping]
    raw_labels: list[str]

    model_config = {"frozen": True}

    def get_index(self, canonical_id: str) -> int | None:
        """Get column index for canonical field ID."""
        for m in self.mappings:
            if m.canonical_id == canonical_id:
                return m.index
        return None

    def get_mapping(self, canonical_id: str) -> ColumnMapping | None:
        """Get mapping for canonical field ID."""
        for m in self.mappings:
            if m.canonical_id == canonical_id:
                return m
        return None

    def has_field(self, canonical_id: str) -> bool:
        """Check if a field is present in the mapping."""
        return self.get_index(canonical_id) is not None


# =============================================================================
# Booking Row Model
# =============================================================================


class BookingRow(BaseModel, frozen=True):
    """
    A single booking row from the DATEV file.

    CRITICAL Design Decisions:
    - fields_raw: Original string values, used for roundtrip writing
    - fields_typed: Converted values for validation, NEVER for writing
    - Konto/Gegenkonto in fields_raw are STRINGS, preserve leading zeros
    """

    row_no: int = Field(
        ge=3,
        description="Row number in file (1-indexed, starting at 3 for data)",
    )
    line_span: tuple[int, int] = Field(
        description="(start_line, end_line) for multi-line records",
    )

    # Raw string values - source of truth for writing
    fields_raw: dict[str, str] = Field(
        description="Original field values as strings (canonical IDs as keys)",
    )

    # Typed values - for validation only, NEVER for writing
    fields_typed: dict[str, Any] = Field(
        default_factory=dict,
        description="Converted values: Decimal for amounts, DerivedDate for dates",
    )

    # Integrity
    checksum: str = Field(
        description="SHA256 hash of raw tokens for integrity checking",
    )

    # Raw tokens for roundtrip
    raw_tokens: list[str] = Field(
        description="Original tokens for roundtrip writing",
    )

    model_config = {"frozen": True}

    def get_raw(self, field_id: str) -> str | None:
        """Get raw string value for field."""
        return self.fields_raw.get(field_id)

    def get_typed(self, field_id: str) -> Any | None:
        """Get typed value for field."""
        return self.fields_typed.get(field_id)

    @property
    def konto(self) -> str | None:
        """Account number as string (preserves leading zeros)."""
        return self.fields_raw.get("konto")

    @property
    def gegenkonto(self) -> str | None:
        """Counter account as string (preserves leading zeros)."""
        return self.fields_raw.get("gegenkonto")

    @property
    def umsatz(self) -> Decimal | None:
        """Amount as Decimal."""
        value = self.fields_typed.get("umsatz")
        return value if isinstance(value, Decimal) else None

    @property
    def belegdatum(self) -> DerivedDate | None:
        """Booking date with year derivation info."""
        value = self.fields_typed.get("belegdatum")
        return value if isinstance(value, DerivedDate) else None

    @property
    def buchungstext(self) -> str | None:
        """Booking text."""
        return self.fields_raw.get("buchungstext")

    @property
    def belegfeld1(self) -> str | None:
        """Document field 1 (Belegfeld 1)."""
        return self.fields_raw.get("belegfeld1")


# =============================================================================
# Parse Result Model
# =============================================================================


class ParseResult(BaseModel):
    """
    Result of parsing a DATEV file.

    The rows are provided as a lazy iterator to support streaming.
    Call list(result.rows) to materialize all rows.
    """

    # File metadata
    file_path: Path
    detected_format: DetectedFormat
    encoding: str
    dialect: Dialect

    # Parsed header
    header: DatevHeader
    columns: ColumnMappings

    # Streaming row iterator
    # Note: This is a factory function that creates a new iterator each time
    # Using Any for the callable type to avoid circular import issues
    row_factory_fn: Any = Field(
        exclude=True,
        repr=False,
        description="Factory function for creating row iterator",
    )

    # Collected errors during header/column parsing
    # Note: ParserError is imported at module level after definition
    header_errors: list[Any] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    @property
    def rows(self) -> Iterator[BookingRow | Any]:
        """
        Iterate over booking rows.

        Yields BookingRow for valid rows, ParserError for invalid rows.
        IMPORTANT: This is a streaming iterator. Each row is parsed on-demand.
        """
        return self.row_factory_fn()  # type: ignore[no-any-return]

    def materialize(self) -> tuple[list[BookingRow], list[Any]]:
        """
        Materialize all rows into memory.

        WARNING: May use significant memory for large files.
        Returns (rows, errors) tuple.
        """
        from .errors import ParserError as ParserErrorClass

        rows: list[BookingRow] = []
        errors: list[ParserErrorClass] = list(self.header_errors)

        for item in self.rows:
            if isinstance(item, ParserErrorClass):
                errors.append(item)
            else:
                rows.append(item)

        return rows, errors

    @property
    def has_fatal_errors(self) -> bool:
        """Check if there are any fatal errors in header parsing."""
        from .errors import Severity

        return any(e.severity == Severity.FATAL for e in self.header_errors)
