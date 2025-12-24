"""
Row parsing for DATEV files.

Converts tokenized rows into structured BookingRow objects with type conversion.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .dates import derive_year
from .errors import Location, ParserError
from .field_dict import FieldDefinition, FieldDictionary, get_field_dictionary
from .models import BookingRow, ColumnMappings, DateConfidence, DatevHeader, DerivedDate


def parse_row(
    tokens: list[str],
    row_no: int,
    line_span: tuple[int, int],
    columns: ColumnMappings,
    header: DatevHeader,
    field_dict: FieldDictionary | None = None,
    filename: str | None = None,
) -> tuple[BookingRow | None, list[ParserError]]:
    """
    Parse a single booking row.

    Args:
        tokens: Tokenized row fields
        row_no: Row number in file (1-indexed)
        line_span: (start_line, end_line) for this row
        columns: Column mappings
        header: Parsed header for context
        field_dict: Optional field dictionary
        filename: Optional filename for errors

    Returns:
        Tuple of (BookingRow or None, list of errors)
    """
    if field_dict is None:
        field_dict = get_field_dictionary()

    errors: list[ParserError] = []
    fields_raw: dict[str, str] = {}
    fields_typed: dict[str, Any] = {}

    # Map tokens to canonical fields
    for mapping in columns.mappings:
        if mapping.index < len(tokens):
            raw_value = tokens[mapping.index]
            fields_raw[mapping.canonical_id] = raw_value

            # Get field definition for type conversion
            field_def = field_dict.get_by_id(mapping.canonical_id)
            if field_def and raw_value:
                typed_value, field_errors = _convert_field(
                    raw_value=raw_value,
                    field_def=field_def,
                    header=header,
                    row_no=row_no,
                    filename=filename,
                )
                if typed_value is not None:
                    fields_typed[mapping.canonical_id] = typed_value
                errors.extend(field_errors)

    # Calculate checksum
    checksum = _calculate_checksum(tokens)

    try:
        row = BookingRow(
            row_no=row_no,
            line_span=line_span,
            fields_raw=fields_raw,
            fields_typed=fields_typed,
            checksum=checksum,
            raw_tokens=tokens,
        )
        return row, errors
    except Exception as e:
        errors.append(
            ParserError.error(
                code="DVL-ROW-002",
                title="Row parsing failed",
                message=str(e),
                location=Location(file=filename, line_no=line_span[0]),
            )
        )
        return None, errors


def _convert_field(
    raw_value: str,
    field_def: FieldDefinition,
    header: DatevHeader,
    row_no: int,
    filename: str | None,
) -> tuple[Any | None, list[ParserError]]:
    """
    Convert a raw field value to its typed representation.

    Args:
        raw_value: Raw string value
        field_def: Field definition
        header: Header for context (dates, etc.)
        row_no: Row number for errors
        filename: Filename for errors

    Returns:
        Tuple of (typed value or None, list of errors)
    """
    errors: list[ParserError] = []
    location = Location(file=filename, line_no=row_no, field=field_def.canonical_id)

    value = raw_value.strip()
    if not value:
        return None, errors

    field_type = field_def.type

    if field_type == "decimal":
        return _parse_decimal(value, location, errors)

    elif field_type == "ttmm":
        return _parse_ttmm(value, header, location, errors)

    elif field_type == "integer":
        return _parse_integer(value, location, errors)

    elif field_type == "enum":
        return _parse_enum(value, field_def, location, errors)

    else:
        # String type - return as-is
        return value, errors


def _parse_decimal(
    value: str,
    location: Location,
    errors: list[ParserError],
) -> tuple[Decimal | None, list[ParserError]]:
    """Parse a decimal value (German format with comma)."""
    try:
        # Replace German decimal comma with dot
        normalized = value.replace(",", ".")
        # Remove thousand separators if present
        normalized = normalized.replace(" ", "").replace(".", "", normalized.count(".") - 1)
        return Decimal(normalized), errors
    except InvalidOperation:
        errors.append(
            ParserError.error(
                code="DVL-FIELD-003",
                title="Invalid decimal",
                message=f"Cannot parse decimal value: '{value}'",
                location=location,
                context={"raw_value": value},
            )
        )
        return None, errors


def _parse_ttmm(
    value: str,
    header: DatevHeader,
    location: Location,
    errors: list[ParserError],
) -> tuple[DerivedDate | None, list[ParserError]]:
    """Parse a TTMM date value."""
    # Validate format
    if not re.match(r"^\d{4}$", value):
        errors.append(
            ParserError.error(
                code="DVL-DATE-001",
                title="Invalid TTMM format",
                message=f"TTMM must be 4 digits, got: '{value}'",
                location=location,
                context={"raw_value": value},
            )
        )
        return None, errors

    derived = derive_year(
        ttmm=value,
        fiscal_year_start=header.fiscal_year_start,
        period_from=header.period_from,
        period_to=header.period_to,
    )

    # Add warnings for non-HIGH confidence
    if derived.confidence == DateConfidence.AMBIGUOUS:
        errors.append(
            ParserError.warn(
                code="DVL-DATE-002",
                title="Ambiguous date",
                message=f"TTMM date '{value}' could map to multiple years",
                location=location,
                context={"raw_value": value, "confidence": derived.confidence.value},
            )
        )
    elif derived.confidence == DateConfidence.FAILED:
        errors.append(
            ParserError.error(
                code="DVL-DATE-003",
                title="Date derivation failed",
                message=f"Cannot derive year for TTMM date '{value}'",
                location=location,
                context={"raw_value": value, "confidence": derived.confidence.value},
            )
        )

    return derived, errors


def _parse_integer(
    value: str,
    location: Location,
    errors: list[ParserError],
) -> tuple[int | None, list[ParserError]]:
    """Parse an integer value."""
    try:
        return int(value), errors
    except ValueError:
        errors.append(
            ParserError.error(
                code="DVL-FIELD-003",
                title="Invalid integer",
                message=f"Cannot parse integer value: '{value}'",
                location=location,
                context={"raw_value": value},
            )
        )
        return None, errors


def _parse_enum(
    value: str,
    field_def: FieldDefinition,
    location: Location,
    errors: list[ParserError],
) -> tuple[str | None, list[ParserError]]:
    """Parse an enum value."""
    if field_def.enum_values and value not in field_def.enum_values:
        errors.append(
            ParserError.error(
                code="DVL-FIELD-005",
                title="Invalid enum value",
                message=f"Value '{value}' not in allowed values: {field_def.enum_values}",
                location=location,
                context={"raw_value": value, "allowed": field_def.enum_values},
            )
        )
        return None, errors
    return value, errors


def _calculate_checksum(tokens: list[str]) -> str:
    """Calculate SHA256 checksum of row tokens."""
    content = ";".join(tokens)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
