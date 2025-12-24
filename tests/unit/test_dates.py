"""Tests for TTMM date year derivation."""

from datetime import date

import pytest

from datev_lint.core.parser import DateConfidence, derive_year


class TestDeriveYear:
    """Tests for derive_year function."""

    def test_within_single_year_period(self) -> None:
        """Test derivation when period is within a single year."""
        result = derive_year(
            "1503",  # March 15
            period_from=date(2025, 1, 1),
            period_to=date(2025, 12, 31),
        )

        assert result.year == 2025
        assert result.derived_date == date(2025, 3, 15)
        assert result.confidence == DateConfidence.HIGH

    def test_cross_year_period_unambiguous(self) -> None:
        """Test derivation for cross-year period with unambiguous date."""
        # Period is Oct 2024 - Mar 2025
        # Date is January (only fits 2025)
        result = derive_year(
            "1501",  # January 15
            period_from=date(2024, 10, 1),
            period_to=date(2025, 3, 31),
        )

        assert result.year == 2025
        assert result.confidence == DateConfidence.HIGH

    def test_fiscal_year_only(self) -> None:
        """Test derivation with only fiscal year start."""
        result = derive_year(
            "1503",
            fiscal_year_start=date(2025, 1, 1),
        )

        assert result.year == 2025
        assert result.confidence == DateConfidence.MEDIUM

    def test_no_context(self) -> None:
        """Test derivation with no context data."""
        result = derive_year("1503")

        assert result.year is None
        assert result.confidence == DateConfidence.UNKNOWN

    def test_invalid_ttmm_format(self) -> None:
        """Test with invalid TTMM format."""
        result = derive_year("abc")

        assert result.confidence == DateConfidence.FAILED
        assert result.year is None

    def test_invalid_day_month(self) -> None:
        """Test with invalid day/month values."""
        result = derive_year("3213")  # Invalid month 13

        assert result.confidence == DateConfidence.FAILED

    def test_february_30(self) -> None:
        """Test with invalid date (Feb 30)."""
        result = derive_year(
            "3002",  # February 30
            period_from=date(2025, 1, 1),
            period_to=date(2025, 12, 31),
        )

        assert result.confidence == DateConfidence.FAILED

    def test_date_parsing(self) -> None:
        """Test that day and month are correctly parsed."""
        result = derive_year(
            "0112",  # December 1
            period_from=date(2025, 1, 1),
            period_to=date(2025, 12, 31),
        )

        assert result.day == 1
        assert result.month == 12
        assert result.derived_date == date(2025, 12, 1)
