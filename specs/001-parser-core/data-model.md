# Data Model: Parser Core

**Feature**: 001-parser-core
**Date**: 2025-12-24

## Entity Overview

```
┌─────────────────┐     ┌─────────────────┐
│  ParseResult    │────▶│  DatevHeader    │
└────────┬────────┘     └─────────────────┘
         │
         │ 1:n (streaming)
         ▼
┌─────────────────┐     ┌─────────────────┐
│  BookingRow     │────▶│  DerivedDate    │
└─────────────────┘     └─────────────────┘
         │
         │ 0:n
         ▼
┌─────────────────┐
│  ParserError    │
└─────────────────┘
```

## Core Entities

### DetectedFormat

Erkanntes Dateiformat nach Layer 0 Detection.

```python
from enum import Enum

class DetectedFormat(Enum):
    """Result of format detection."""
    DATEV_FORMAT = "datev"      # EXTF file
    ASCII_STANDARD = "ascii"    # DATEV ASCII format
    UNKNOWN = "unknown"         # Cannot determine
```

### Dialect

CSV-Dialekt-Konfiguration.

```python
from pydantic import BaseModel

class Dialect(BaseModel, frozen=True):
    """CSV dialect settings for DATEV files."""
    delimiter: str = ";"
    quotechar: str = '"'
    escapechar: str = '"'  # Doubled quotes
    lineterminator: str = "\r"  # CR terminates, LF can be in quotes

    class Config:
        frozen = True
```

### DatevHeader

Metadaten aus Zeile 1 der EXTF-Datei.

```python
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional

class DatevHeader(BaseModel, frozen=True):
    """
    DATEV EXTF header (line 1).

    CRITICAL: beraternummer and mandantennummer are STRINGS, never int!
    Leading zeros must be preserved.
    """

    # Pflichtfelder
    kennzeichen: str = Field(
        pattern=r'^EXTF$',
        description="Must be 'EXTF' for DATEV format"
    )
    header_version: int = Field(
        ge=500, le=999,
        description="Header version (700 = current, 510 = legacy)"
    )
    format_category: int = Field(
        description="21 = Buchungsstapel, 16 = Debitoren, etc."
    )
    format_name: str = Field(
        description="e.g., 'Buchungsstapel'"
    )
    format_version: int = Field(
        description="Format version within category"
    )

    # Optionale Metadaten
    created_at: Optional[datetime] = Field(
        default=None,
        description="Creation timestamp"
    )

    # KRITISCH: Immer String!
    beraternummer: Optional[str] = Field(
        default=None,
        pattern=r'^\d*$',
        description="Berater ID - MUST be string to preserve leading zeros"
    )
    mandantennummer: Optional[str] = Field(
        default=None,
        pattern=r'^\d*$',
        description="Mandant ID - MUST be string to preserve leading zeros"
    )

    # Zeitraum
    fiscal_year_start: Optional[date] = Field(
        default=None,
        description="Start of fiscal year"
    )
    period_from: Optional[date] = Field(
        default=None,
        description="Period start date"
    )
    period_to: Optional[date] = Field(
        default=None,
        description="Period end date"
    )

    # Kontenkonfiguration
    account_length: Optional[int] = Field(
        default=None,
        ge=4, le=9,
        description="Account number length (4-9 digits)"
    )
    currency: Optional[str] = Field(
        default=None,
        max_length=3,
        description="Currency code (WKZ), e.g., 'EUR'"
    )

    # Festschreibung
    festschreibung: Optional[int] = Field(
        default=None,
        ge=0, le=1,
        description="0 = not locked, 1 = locked"
    )

    # Roundtrip-Daten
    raw_tokens: list[str] = Field(
        description="Original tokens for roundtrip writing"
    )

    class Config:
        frozen = True
```

### ColumnMapping

Zuordnung von Spaltenüberschriften zu kanonischen Field-IDs.

```python
from pydantic import BaseModel

class ColumnMapping(BaseModel, frozen=True):
    """Maps column index to canonical field ID."""
    index: int
    canonical_id: str
    original_label: str

class ColumnMappings(BaseModel, frozen=True):
    """Complete column mapping for a file."""
    mappings: list[ColumnMapping]
    raw_labels: list[str]

    def get_index(self, canonical_id: str) -> Optional[int]:
        """Get column index for canonical field ID."""
        for m in self.mappings:
            if m.canonical_id == canonical_id:
                return m.index
        return None
```

### DerivedDate

Abgeleitetes Datum aus TTMM-Format.

```python
from enum import Enum
from pydantic import BaseModel
from datetime import date
from typing import Optional

class DateConfidence(Enum):
    """Confidence level for year derivation."""
    HIGH = "high"           # Unambiguous, within period
    MEDIUM = "medium"       # Derived from fiscal year
    AMBIGUOUS = "ambiguous" # Could be multiple years
    FAILED = "failed"       # Cannot derive, out of range
    UNKNOWN = "unknown"     # No context data available

class DerivedDate(BaseModel, frozen=True):
    """
    Result of TTMM date year derivation.

    The TTMM format only contains day and month (e.g., "1503" = March 15).
    The year must be derived from context (period, fiscal year).
    """
    raw_ttmm: str = Field(
        pattern=r'^\d{4}$',
        description="Original TTMM value"
    )
    day: int = Field(ge=1, le=31)
    month: int = Field(ge=1, le=12)
    year: Optional[int] = Field(
        default=None,
        description="Derived year, None if derivation failed"
    )
    derived_date: Optional[date] = Field(
        default=None,
        description="Complete date if derivation succeeded"
    )
    confidence: DateConfidence
    warning_code: Optional[str] = Field(
        default=None,
        description="Warning/error code if not HIGH confidence"
    )
```

### BookingRow

Eine Buchungszeile mit Raw- und Typed-Feldern.

```python
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Any, Optional

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
        description="Row number in file (1-indexed, starting at 3 for data)"
    )
    line_span: tuple[int, int] = Field(
        description="(start_line, end_line) for multi-line records"
    )

    # Raw string values - source of truth for writing
    fields_raw: dict[str, str] = Field(
        description="Original field values as strings (canonical IDs as keys)"
    )

    # Typed values - for validation only, NEVER for writing
    fields_typed: dict[str, Any] = Field(
        default_factory=dict,
        description="Converted values: Decimal for amounts, DerivedDate for dates"
    )

    # Integrity
    checksum: str = Field(
        description="SHA256 hash of raw tokens for integrity checking"
    )

    # Raw tokens for roundtrip
    raw_tokens: list[str] = Field(
        description="Original tokens for roundtrip writing"
    )

    def get_raw(self, field_id: str) -> Optional[str]:
        """Get raw string value for field."""
        return self.fields_raw.get(field_id)

    def get_typed(self, field_id: str) -> Optional[Any]:
        """Get typed value for field."""
        return self.fields_typed.get(field_id)

    @property
    def konto(self) -> Optional[str]:
        """Account number as string (preserves leading zeros)."""
        return self.fields_raw.get("konto")

    @property
    def gegenkonto(self) -> Optional[str]:
        """Counter account as string (preserves leading zeros)."""
        return self.fields_raw.get("gegenkonto")

    @property
    def umsatz(self) -> Optional[Decimal]:
        """Amount as Decimal."""
        return self.fields_typed.get("umsatz")

    @property
    def belegdatum(self) -> Optional[DerivedDate]:
        """Booking date with year derivation info."""
        return self.fields_typed.get("belegdatum")
```

### ParserError

Strukturierter Parser-Fehler.

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any

class Severity(Enum):
    """Error severity levels."""
    FATAL = "fatal"   # Cannot continue parsing
    ERROR = "error"   # Likely import failure
    WARN = "warn"     # Risky, might cause issues
    INFO = "info"     # Informational

class Location(BaseModel, frozen=True):
    """Error location in file."""
    file: Optional[str] = None
    line_no: Optional[int] = None
    column: Optional[int] = None
    field: Optional[str] = None

class ParserError(BaseModel, frozen=True):
    """
    Structured parser error.

    Uses error codes from the Error Taxonomy (DVL-XXX-NNN).
    """
    code: str = Field(
        pattern=r'^DVL-[A-Z]{2,5}-\d{3}$',
        description="Error code, e.g., 'DVL-ENC-001'"
    )
    severity: Severity
    title: str = Field(
        description="Short error title"
    )
    message: str = Field(
        description="Detailed error message"
    )
    location: Location = Field(
        default_factory=Location,
        description="Where the error occurred"
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (raw_value, expected, etc.)"
    )

    @classmethod
    def fatal(cls, code: str, title: str, message: str, **kwargs) -> "ParserError":
        return cls(code=code, severity=Severity.FATAL, title=title, message=message, **kwargs)

    @classmethod
    def error(cls, code: str, title: str, message: str, **kwargs) -> "ParserError":
        return cls(code=code, severity=Severity.ERROR, title=title, message=message, **kwargs)

    @classmethod
    def warn(cls, code: str, title: str, message: str, **kwargs) -> "ParserError":
        return cls(code=code, severity=Severity.WARN, title=title, message=message, **kwargs)
```

### ParseResult

Gesamtergebnis des Parsens.

```python
from pydantic import BaseModel
from typing import Iterator, Callable
from pathlib import Path

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
    _row_factory: Callable[[], Iterator[BookingRow | ParserError]]

    # Collected errors during header/column parsing
    header_errors: list[ParserError] = []

    @property
    def rows(self) -> Iterator[BookingRow | ParserError]:
        """
        Iterate over booking rows.

        Yields BookingRow for valid rows, ParserError for invalid rows.
        IMPORTANT: This is a streaming iterator. Each row is parsed on-demand.
        """
        return self._row_factory()

    def materialize(self) -> tuple[list[BookingRow], list[ParserError]]:
        """
        Materialize all rows into memory.

        WARNING: May use significant memory for large files.
        Returns (rows, errors) tuple.
        """
        rows = []
        errors = list(self.header_errors)

        for item in self.rows:
            if isinstance(item, ParserError):
                errors.append(item)
            else:
                rows.append(item)

        return rows, errors

    class Config:
        arbitrary_types_allowed = True  # For Iterator type
```

## Field Dictionary Entity

```python
from pydantic import BaseModel
from typing import Optional

class FieldDefinition(BaseModel, frozen=True):
    """Definition of a DATEV field from the Field Dictionary."""
    canonical_id: str
    synonyms: list[str]
    required: bool
    type: str  # "string", "decimal", "ttmm", "enum"
    max_length: Optional[int]
    charset: Optional[str]
    charset_pattern: Optional[str]  # Regex for validation
    fix_strategies: list[str]

class FieldDictionary(BaseModel, frozen=True):
    """Complete field dictionary loaded from YAML."""
    fields: dict[str, FieldDefinition]
    version: str

    def get_by_synonym(self, label: str) -> Optional[FieldDefinition]:
        """Find field definition by synonym (case-insensitive)."""
        label_lower = label.lower().strip()
        for field in self.fields.values():
            for syn in field.synonyms:
                if syn.lower().strip() == label_lower:
                    return field
        return None

    def get_by_id(self, canonical_id: str) -> Optional[FieldDefinition]:
        """Get field definition by canonical ID."""
        return self.fields.get(canonical_id)
```

## State Transitions

### Parser State Machine

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │ read bytes
                           ▼
                    ┌─────────────┐
                    │  DETECTING  │──── encoding error ────▶ FATAL
                    └──────┬──────┘
                           │ encoding detected
                           ▼
                    ┌─────────────┐
                    │PARSING_HDR  │──── header error ──────▶ FATAL
                    └──────┬──────┘
                           │ header parsed
                           ▼
                    ┌─────────────┐
                    │PARSING_COLS │──── column error ──────▶ ERROR (continue)
                    └──────┬──────┘
                           │ columns mapped
                           ▼
                    ┌─────────────┐
              ┌────▶│PARSING_ROWS │──── row error ─────────▶ yield ParserError
              │     └──────┬──────┘                          (continue)
              │            │ row parsed
              │            ▼
              │     ┌─────────────┐
              └─────│ yield Row   │
                    └──────┬──────┘
                           │ EOF
                           ▼
                    ┌─────────────┐
                    │   DONE      │
                    └─────────────┘
```

### Tokenizer State Machine

```
          ┌───────────────────────────────────────────────┐
          │                                               │
          ▼                                               │
    ┌───────────┐    ; (not in quotes)     ┌───────────┐  │
    │FIELD_START│─────────────────────────▶│emit field │──┘
    └─────┬─────┘                          └───────────┘
          │
          │ "
          ▼
    ┌───────────┐    ""           ┌───────────────┐
    │IN_QUOTED  │────────────────▶│QUOTE_IN_QUOTED│
    └─────┬─────┘                 └───────┬───────┘
          │                               │
          │ any char                      │ " (close quote)
          │ (including LF)                │
          ▼                               ▼
    ┌───────────┐                  ┌───────────┐
    │accumulate │                  │end quoted │
    └───────────┘                  └───────────┘
```

## Validation Rules

| Field | Validation | Error Code |
|-------|------------|------------|
| kennzeichen | Must be "EXTF" | DVL-HDR-001 |
| header_version | 500-999 | DVL-HDR-002 |
| format_category | 21 for Buchungsstapel | DVL-HDR-003 |
| beraternummer | Digits only, string type | DVL-HDR-004 |
| konto | Digits only, ≤ account_length | DVL-FIELD-002 |
| belegdatum | Valid TTMM (01-31, 01-12) | DVL-DATE-001 |
| umsatz | Valid decimal with comma | DVL-FIELD-003 |
