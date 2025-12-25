"""
DATEV Parser Core.

Public API for parsing DATEV EXTF files.

Usage:
    from datev_lint.core.parser import parse_file, ParseResult

    result = parse_file("EXTF_Buchungsstapel.csv")
    print(f"Header version: {result.header.header_version}")

    for row in result.rows:
        print(f"Konto: {row.konto}")

API Functions:
    parse_file(path) -> ParseResult
    parse_bytes(data, filename) -> ParseResult
    parse_stream(stream, filename) -> ParseResult
    detect_encoding(data) -> str
    detect_format(data) -> DetectedFormat
    derive_year(ttmm, ...) -> DerivedDate
    get_field_dictionary() -> FieldDictionary
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from collections.abc import Iterator

from .columns import map_columns
from .dates import derive_year
from .detector import detect_format
from .encoding import detect_encoding
from .errors import Location, ParserError, Severity
from .field_dict import FieldDefinition, FieldDictionary, get_field_dictionary
from .header import parse_header
from .models import (
    BookingRow,
    ColumnMapping,
    ColumnMappings,
    DateConfidence,
    DatevHeader,
    DerivedDate,
    DetectedFormat,
    Dialect,
    ParseResult,
)
from .rows import parse_row
from .tokenizer import tokenize_stream


def parse_file(path: Path | str, *, max_bytes: int | None = None) -> ParseResult:
    """
    Parse a DATEV EXTF file.

    Args:
        path: Path to the DATEV file

    Returns:
        ParseResult with header and streaming row iterator

    Raises:
        FileNotFoundError: If file does not exist
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return parse_bytes_from_path(path, max_bytes=max_bytes)


def parse_bytes_from_path(path: Path, *, max_bytes: int | None = None) -> ParseResult:
    """
    Parse a DATEV file from disk with optional size limits.

    Args:
        path: Path to the DATEV file
        max_bytes: Maximum bytes to read (None = unlimited)

    Returns:
        ParseResult with header and streaming row iterator
    """
    if max_bytes is not None and max_bytes > 0:
        with path.open("rb") as f:
            data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            file_size: int | None
            try:
                file_size = path.stat().st_size
            except OSError:
                file_size = None
            return _create_error_result(
                filename=str(path),
                encoding="<unknown>",
                detected_format=DetectedFormat.UNKNOWN,
                error=ParserError.fatal(
                    code="DVL-IO-001",
                    title="File too large",
                    message=f"File exceeds maximum size of {max_bytes} bytes",
                    location=Location(file=str(path)),
                    context={"max_bytes": max_bytes, "file_size": file_size},
                ),
            )
        return parse_bytes(data, str(path), max_bytes=max_bytes)

    data = path.read_bytes()
    return parse_bytes(data, str(path), max_bytes=None)


def parse_bytes(
    data: bytes, filename: str = "<bytes>", *, max_bytes: int | None = None
) -> ParseResult:
    """
    Parse DATEV data from bytes.

    Args:
        data: Raw file content
        filename: Optional filename for error messages

    Returns:
        ParseResult with header and streaming row iterator
    """
    if max_bytes is not None and max_bytes > 0 and len(data) > max_bytes:
        return _create_error_result(
            filename=filename,
            encoding="<unknown>",
            detected_format=DetectedFormat.UNKNOWN,
            error=ParserError.fatal(
                code="DVL-IO-001",
                title="File too large",
                message=f"Input exceeds maximum size of {max_bytes} bytes",
                location=Location(file=filename),
                context={"max_bytes": max_bytes, "file_size": len(data)},
            ),
        )

    # Step 1: Detect encoding
    encoding = detect_encoding(data)

    # Step 2: Detect format
    detected_format = detect_format(data)

    # Step 3: Decode data
    text = data.decode(encoding, errors="replace")
    dialect = Dialect()

    # Step 4: Tokenize
    records_iter = tokenize_stream(text, dialect)

    # Need at least 2 records (header + columns)
    try:
        header_tokens, _, _ = next(records_iter)
        column_tokens, _, _ = next(records_iter)
    except StopIteration:
        # Not enough records for header and column line
        return _create_error_result(
            filename=filename,
            encoding=encoding,
            detected_format=detected_format,
            error=ParserError.fatal(
                code="DVL-HDR-001",
                title="Insufficient data",
                message="File must have at least 2 lines (header and columns)",
                location=Location(file=filename),
            ),
        )

    # Step 5: Parse header (first record)
    header, header_errors = parse_header(header_tokens, filename)

    if header is None:
        # Fatal header error
        return _create_error_result(
            filename=filename,
            encoding=encoding,
            detected_format=detected_format,
            error=header_errors[0]
            if header_errors
            else ParserError.fatal(
                code="DVL-HDR-001",
                title="Header parsing failed",
                message="Could not parse header",
                location=Location(file=filename),
            ),
        )

    # Step 6: Parse column headers (second record)
    columns, column_errors = map_columns(column_tokens, filename=filename)
    header_errors.extend(column_errors)

    # Step 7: Create row factory for streaming
    def row_factory() -> Iterator[BookingRow | ParserError]:
        """Create an iterator over data rows."""
        row_no = 3  # Data rows start at line 3

        # Re-tokenize from the start to keep the iterator reusable.
        row_records = tokenize_stream(text, dialect)
        next(row_records, None)  # header
        next(row_records, None)  # columns

        for tokens, start_line, end_line in row_records:
            # Skip empty rows
            if not tokens or not any(t.strip() for t in tokens):
                row_no += 1
                continue

            row, row_errors = parse_row(
                tokens=tokens,
                row_no=row_no,
                line_span=(start_line, end_line),
                columns=columns,
                header=header,
                filename=filename,
            )

            # Yield errors
            yield from row_errors

            # Yield row if successfully parsed
            if row is not None:
                yield row

            row_no += 1

            # Check row limit (99,999)
            if row_no > 99_999 + 2:
                yield ParserError.warn(
                    code="DVL-ROW-001",
                    title="Row limit exceeded",
                    message="File has more than 99,999 data rows",
                    location=Location(file=filename, line_no=row_no),
                )
                break

    return ParseResult(
        file_path=Path(filename),
        detected_format=detected_format,
        encoding=encoding,
        dialect=dialect,
        header=header,
        columns=columns,
        row_factory_fn=row_factory,
        header_errors=header_errors,
    )


def parse_stream(
    stream: BinaryIO, filename: str = "<stream>", *, max_bytes: int | None = None
) -> ParseResult:
    """
    Parse DATEV data from a binary stream.

    Args:
        stream: Binary file-like object
        filename: Optional filename for error messages

    Returns:
        ParseResult with header and streaming row iterator
    """
    data = stream.read(max_bytes + 1) if max_bytes is not None and max_bytes > 0 else stream.read()

    return parse_bytes(data, filename, max_bytes=max_bytes)


def _create_error_result(
    filename: str,
    encoding: str,
    detected_format: DetectedFormat,
    error: ParserError,
) -> ParseResult:
    """Create a ParseResult for fatal errors."""
    # Create minimal header for error cases
    dummy_header = DatevHeader(
        kennzeichen="EXTF",
        header_version=700,
        format_category=21,
        format_name="Unknown",
        format_version=0,
        raw_tokens=[],
    )

    def empty_row_factory() -> Iterator[BookingRow | ParserError]:
        """Empty row factory."""
        return iter([])

    return ParseResult(
        file_path=Path(filename),
        detected_format=detected_format,
        encoding=encoding,
        dialect=Dialect(),
        header=dummy_header,
        columns=ColumnMappings(mappings=[], raw_labels=[]),
        row_factory_fn=empty_row_factory,
        header_errors=[error],
    )


# =============================================================================
# Public API Exports
# =============================================================================

__all__ = [
    "BookingRow",
    "ColumnMapping",
    "ColumnMappings",
    "DateConfidence",
    "DatevHeader",
    "DerivedDate",
    # Enums
    "DetectedFormat",
    # Models
    "Dialect",
    "FieldDefinition",
    "FieldDictionary",
    "Location",
    "ParseResult",
    "ParserError",
    "Severity",
    "derive_year",
    "detect_encoding",
    "detect_format",
    "get_field_dictionary",
    "parse_bytes",
    # Main functions
    "parse_file",
    "parse_stream",
]
