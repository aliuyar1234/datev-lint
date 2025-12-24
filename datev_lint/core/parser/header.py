"""
DATEV header parsing.

Parses the first line of a DATEV EXTF file (header metadata).
"""

from __future__ import annotations

import re
from datetime import date, datetime

from .errors import Location, ParserError
from .models import DatevHeader

# Header field indices for DATEV 700 format
# Based on DATEV-Format-Beschreibung
HEADER_FIELDS = {
    0: "kennzeichen",
    1: "header_version",
    2: "format_category",
    3: "format_name",
    4: "format_version",
    5: "created_at",
    6: "reserved_1",
    7: "reserved_2",
    8: "reserved_3",
    9: "reserved_4",
    10: "reserved_5",
    11: "beraternummer",
    12: "mandantennummer",
    13: "fiscal_year_start",
    14: "account_length",
    15: "period_from",
    16: "period_to",
    17: "bezeichnung",
    18: "diktat_kuerzel",
    19: "buchungstyp",
    20: "rechnungslegungszweck",
    21: "reserved_6",
    22: "reserved_7",
    23: "currency",
    24: "reserved_8",
    25: "reserved_9",
    26: "reserved_10",
    27: "reserved_11",
    28: "reserved_12",
    29: "reserved_13",
    30: "festschreibung",
}


def parse_header(
    tokens: list[str],
    filename: str | None = None,
) -> tuple[DatevHeader | None, list[ParserError]]:
    """
    Parse DATEV header from tokenized first line.

    Args:
        tokens: Tokenized header fields
        filename: Optional filename for error locations

    Returns:
        Tuple of (DatevHeader or None, list of errors)
    """
    errors: list[ParserError] = []
    location = Location(file=filename, line_no=1)

    if not tokens:
        errors.append(
            ParserError.fatal(
                code="DVL-HDR-001",
                title="Empty header",
                message="Header line is empty",
                location=location,
            )
        )
        return None, errors

    # Check minimum field count
    if len(tokens) < 5:
        errors.append(
            ParserError.fatal(
                code="DVL-HDR-001",
                title="Invalid header",
                message=f"Header has only {len(tokens)} fields, expected at least 5",
                location=location,
            )
        )
        return None, errors

    # Parse required fields
    kennzeichen = tokens[0].strip().upper()
    if kennzeichen != "EXTF":
        errors.append(
            ParserError.fatal(
                code="DVL-HDR-001",
                title="Invalid format marker",
                message=f"Expected 'EXTF', got '{kennzeichen}'",
                location=location,
            )
        )
        return None, errors

    # Parse header version
    try:
        header_version = int(tokens[1])
        if not 500 <= header_version <= 999:
            errors.append(
                ParserError.error(
                    code="DVL-HDR-002",
                    title="Invalid header version",
                    message=f"Header version {header_version} not in range 500-999",
                    location=location,
                )
            )
    except ValueError:
        errors.append(
            ParserError.fatal(
                code="DVL-HDR-002",
                title="Invalid header version",
                message=f"Cannot parse header version: '{tokens[1]}'",
                location=location,
            )
        )
        return None, errors

    # Parse format category
    try:
        format_category = int(tokens[2])
    except ValueError:
        errors.append(
            ParserError.fatal(
                code="DVL-HDR-003",
                title="Invalid format category",
                message=f"Cannot parse format category: '{tokens[2]}'",
                location=location,
            )
        )
        return None, errors

    format_name = tokens[3].strip()

    # Parse format version
    try:
        format_version = int(tokens[4])
    except ValueError:
        format_version = 0
        errors.append(
            ParserError.warn(
                code="DVL-HDR-006",
                title="Invalid format version",
                message=f"Cannot parse format version: '{tokens[4]}'",
                location=location,
            )
        )

    # Parse optional fields
    created_at = _parse_datetime(tokens, 5)
    beraternummer = _parse_string_id(tokens, 11)
    mandantennummer = _parse_string_id(tokens, 12)
    fiscal_year_start = _parse_date(tokens, 13)
    account_length = _parse_int(tokens, 14)
    period_from = _parse_date(tokens, 15)
    period_to = _parse_date(tokens, 16)
    bezeichnung = _get_token(tokens, 17)
    diktat_kuerzel = _get_token(tokens, 18)
    buchungstyp = _parse_int(tokens, 19)
    rechnungslegungszweck = _parse_int(tokens, 20)
    currency = _get_token(tokens, 23)
    festschreibung = _parse_int(tokens, 30)

    # Validate period dates
    if period_from and period_to and period_from > period_to:
        errors.append(
            ParserError.error(
                code="DVL-HDR-004",
                title="Invalid period dates",
                message=f"period_from ({period_from}) is after period_to ({period_to})",
                location=location,
            )
        )

    try:
        header = DatevHeader(
            kennzeichen=kennzeichen,
            header_version=header_version,
            format_category=format_category,
            format_name=format_name,
            format_version=format_version,
            created_at=created_at,
            beraternummer=beraternummer,
            mandantennummer=mandantennummer,
            fiscal_year_start=fiscal_year_start,
            period_from=period_from,
            period_to=period_to,
            account_length=account_length,
            currency=currency,
            festschreibung=festschreibung,
            bezeichnung=bezeichnung,
            diktat_kuerzel=diktat_kuerzel,
            buchungstyp=buchungstyp,
            rechnungslegungszweck=rechnungslegungszweck,
            raw_tokens=tokens,
        )
        return header, errors
    except Exception as e:
        errors.append(
            ParserError.fatal(
                code="DVL-HDR-006",
                title="Header validation failed",
                message=str(e),
                location=location,
            )
        )
        return None, errors


def _get_token(tokens: list[str], index: int) -> str | None:
    """Get token at index, or None if not present or empty."""
    if index < len(tokens):
        value = tokens[index].strip()
        return value if value else None
    return None


def _parse_int(tokens: list[str], index: int) -> int | None:
    """Parse integer at index, or None if not present/invalid."""
    value = _get_token(tokens, index)
    if value:
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _parse_string_id(tokens: list[str], index: int) -> str | None:
    """
    Parse a string ID (beraternummer, mandantennummer).

    CRITICAL: These must remain strings to preserve leading zeros!
    """
    value = _get_token(tokens, index)
    if value:
        # Remove any non-digit characters but preserve as string
        digits = re.sub(r"\D", "", value)
        return digits if digits else None
    return None


def _parse_date(tokens: list[str], index: int) -> date | None:
    """Parse date at index (YYYYMMDD format)."""
    value = _get_token(tokens, index)
    if value and len(value) >= 8:
        try:
            # Extract YYYYMMDD
            digits = re.sub(r"\D", "", value)[:8]
            if len(digits) == 8:
                return date(
                    year=int(digits[:4]),
                    month=int(digits[4:6]),
                    day=int(digits[6:8]),
                )
        except ValueError:
            pass
    return None


def _parse_datetime(tokens: list[str], index: int) -> datetime | None:
    """Parse datetime at index (YYYYMMDDHHMMSS format)."""
    value = _get_token(tokens, index)
    if value and len(value) >= 14:
        try:
            # Extract digits only
            digits = re.sub(r"\D", "", value)[:17]
            if len(digits) >= 14:
                return datetime(
                    year=int(digits[:4]),
                    month=int(digits[4:6]),
                    day=int(digits[6:8]),
                    hour=int(digits[8:10]),
                    minute=int(digits[10:12]),
                    second=int(digits[12:14]),
                )
        except ValueError:
            pass
    return None
