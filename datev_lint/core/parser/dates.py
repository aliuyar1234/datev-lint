"""
TTMM date year derivation.

DATEV uses TTMM format (day + month, e.g., "1503" = March 15) without year.
The year must be derived from context (period dates, fiscal year).

This module implements the year derivation algorithm with confidence levels.
"""

from __future__ import annotations

from datetime import date

from .models import DateConfidence, DerivedDate


def derive_year(
    ttmm: str,
    fiscal_year_start: date | None = None,
    period_from: date | None = None,
    period_to: date | None = None,
) -> DerivedDate:
    """
    Derive year for TTMM date format.

    The algorithm:
    1. If period_from and period_to are in the same year and the date fits:
       → HIGH confidence
    2. If period spans years (Dec-Jan), check which year the date belongs to:
       → HIGH confidence if unambiguous
       → AMBIGUOUS if could be either year
    3. If only fiscal_year_start is available, use that year:
       → MEDIUM confidence
    4. No context data:
       → UNKNOWN confidence

    Args:
        ttmm: 4-digit TTMM string, e.g., "1503" for March 15
        fiscal_year_start: Optional fiscal year start date
        period_from: Optional period start date
        period_to: Optional period end date

    Returns:
        DerivedDate with year and confidence level
    """
    # Parse day and month
    if not ttmm or len(ttmm) != 4 or not ttmm.isdigit():
        return DerivedDate(
            raw_ttmm=ttmm or "",
            day=0,
            month=0,
            year=None,
            derived_date=None,
            confidence=DateConfidence.FAILED,
            warning_code="DVL-DATE-001",
        )

    day = int(ttmm[:2])
    month = int(ttmm[2:4])

    # Validate day and month ranges
    if not (1 <= day <= 31) or not (1 <= month <= 12):
        # Clamp values to valid ranges for the model
        return DerivedDate(
            raw_ttmm=ttmm,
            day=min(max(day, 0), 31),
            month=min(max(month, 0), 12),
            year=None,
            derived_date=None,
            confidence=DateConfidence.FAILED,
            warning_code="DVL-DATE-001",
        )

    # Case 1: Both period dates available
    if period_from and period_to:
        return _derive_from_period(ttmm, day, month, period_from, period_to)

    # Case 2: Only fiscal year available
    if fiscal_year_start:
        return _derive_from_fiscal_year(ttmm, day, month, fiscal_year_start)

    # Case 3: No context
    return DerivedDate(
        raw_ttmm=ttmm,
        day=day,
        month=month,
        year=None,
        derived_date=None,
        confidence=DateConfidence.UNKNOWN,
        warning_code="DVL-DATE-004",
    )


def _derive_from_period(
    ttmm: str,
    day: int,
    month: int,
    period_from: date,
    period_to: date,
) -> DerivedDate:
    """Derive year from period dates."""
    # Same year?
    if period_from.year == period_to.year:
        year = period_from.year
        try:
            derived_date = date(year, month, day)
            # Check if within period
            if period_from <= derived_date <= period_to:
                return DerivedDate(
                    raw_ttmm=ttmm,
                    day=day,
                    month=month,
                    year=year,
                    derived_date=derived_date,
                    confidence=DateConfidence.HIGH,
                )
            else:
                # Outside period but we can still use the year
                return DerivedDate(
                    raw_ttmm=ttmm,
                    day=day,
                    month=month,
                    year=year,
                    derived_date=derived_date,
                    confidence=DateConfidence.MEDIUM,
                    warning_code="DVL-DATE-003",
                )
        except ValueError:
            # Invalid date (e.g., Feb 30)
            return DerivedDate(
                raw_ttmm=ttmm,
                day=day,
                month=month,
                year=None,
                derived_date=None,
                confidence=DateConfidence.FAILED,
                warning_code="DVL-DATE-001",
            )

    # Period spans years (e.g., Oct 2024 - Jan 2025)
    year_from = period_from.year
    year_to = period_to.year

    # Try both years
    candidates: list[tuple[date, int]] = []

    for year in [year_from, year_to]:
        try:
            candidate_date = date(year, month, day)
            if period_from <= candidate_date <= period_to:
                candidates.append((candidate_date, year))
        except ValueError:
            pass

    if len(candidates) == 1:
        # Unambiguous
        derived_date, year = candidates[0]
        return DerivedDate(
            raw_ttmm=ttmm,
            day=day,
            month=month,
            year=year,
            derived_date=derived_date,
            confidence=DateConfidence.HIGH,
        )
    elif len(candidates) > 1:
        # Ambiguous - both years are valid
        # Prefer the earlier year (convention)
        derived_date, year = candidates[0]
        return DerivedDate(
            raw_ttmm=ttmm,
            day=day,
            month=month,
            year=year,
            derived_date=derived_date,
            confidence=DateConfidence.AMBIGUOUS,
            warning_code="DVL-DATE-002",
        )
    else:
        # No valid date found
        return DerivedDate(
            raw_ttmm=ttmm,
            day=day,
            month=month,
            year=None,
            derived_date=None,
            confidence=DateConfidence.FAILED,
            warning_code="DVL-DATE-003",
        )


def _derive_from_fiscal_year(
    ttmm: str,
    day: int,
    month: int,
    fiscal_year_start: date,
) -> DerivedDate:
    """Derive year from fiscal year start."""
    year = fiscal_year_start.year

    # If the month is before the fiscal year start month,
    # the date might be in the next calendar year
    if month < fiscal_year_start.month:
        year = fiscal_year_start.year + 1

    try:
        derived_date = date(year, month, day)
        return DerivedDate(
            raw_ttmm=ttmm,
            day=day,
            month=month,
            year=year,
            derived_date=derived_date,
            confidence=DateConfidence.MEDIUM,
        )
    except ValueError:
        return DerivedDate(
            raw_ttmm=ttmm,
            day=day,
            month=month,
            year=None,
            derived_date=None,
            confidence=DateConfidence.FAILED,
            warning_code="DVL-DATE-001",
        )
