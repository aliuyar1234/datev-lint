"""Tests for fix operations."""

import pytest

from datev_lint.core.fix.models import OperationContext, PatchOperation
from datev_lint.core.fix.operations import (
    NormalizeDecimalOperation,
    OperationRegistry,
    SanitizeCharsOperation,
    SetFieldOperation,
    TruncateOperation,
    UpperOperation,
)


class TestUpperOperation:
    """Tests for UpperOperation."""

    def test_upper_simple(self) -> None:
        """Test uppercase conversion."""
        op = UpperOperation()
        context = OperationContext(field_name="test")

        result = op.apply("hello", context, {})
        assert result == "HELLO"

    def test_upper_mixed(self) -> None:
        """Test mixed case conversion."""
        op = UpperOperation()
        context = OperationContext(field_name="test")

        result = op.apply("Hello World", context, {})
        assert result == "HELLO WORLD"

    def test_upper_already_upper(self) -> None:
        """Test already uppercase."""
        op = UpperOperation()
        context = OperationContext(field_name="test")

        result = op.apply("HELLO", context, {})
        assert result == "HELLO"


class TestTruncateOperation:
    """Tests for TruncateOperation."""

    def test_truncate_from_params(self) -> None:
        """Test truncation using params."""
        op = TruncateOperation()
        context = OperationContext(field_name="test")

        result = op.apply("abcdefghij", context, {"max_length": 5})
        assert result == "abcde"

    def test_truncate_from_context(self) -> None:
        """Test truncation using context."""
        op = TruncateOperation()
        context = OperationContext(field_name="test", max_length=3)

        result = op.apply("abcdefghij", context, {})
        assert result == "abc"

    def test_truncate_shorter_than_limit(self) -> None:
        """Test value shorter than limit."""
        op = TruncateOperation()
        context = OperationContext(field_name="test", max_length=10)

        result = op.apply("abc", context, {})
        assert result == "abc"

    def test_truncate_no_limit(self) -> None:
        """Test no limit specified."""
        op = TruncateOperation()
        context = OperationContext(field_name="test")

        result = op.apply("abcdefghij", context, {})
        assert result == "abcdefghij"


class TestSanitizeCharsOperation:
    """Tests for SanitizeCharsOperation."""

    def test_sanitize_remove_chars(self) -> None:
        """Test removing invalid characters."""
        op = SanitizeCharsOperation()
        context = OperationContext(field_name="test")

        result = op.apply("abc.def", context, {"pattern": r"\."})
        assert result == "abcdef"

    def test_sanitize_replace_chars(self) -> None:
        """Test replacing characters."""
        op = SanitizeCharsOperation()
        context = OperationContext(field_name="test")

        result = op.apply("abc.def", context, {"pattern": r"\.", "replacement": "-"})
        assert result == "abc-def"

    def test_sanitize_from_context(self) -> None:
        """Test using context pattern."""
        op = SanitizeCharsOperation()
        context = OperationContext(field_name="test", charset_pattern=r"[^A-Z0-9]")

        result = op.apply("abc123", context, {})
        assert result == "123"  # lowercase removed


class TestNormalizeDecimalOperation:
    """Tests for NormalizeDecimalOperation."""

    def test_normalize_dot_decimal(self) -> None:
        """Test normalizing dot decimal."""
        op = NormalizeDecimalOperation()
        context = OperationContext(field_name="test")

        result = op.apply("100.50", context, {})
        assert result == "100,50"

    def test_normalize_comma_decimal(self) -> None:
        """Test normalizing comma decimal."""
        op = NormalizeDecimalOperation()
        context = OperationContext(field_name="test")

        result = op.apply("100,50", context, {})
        assert result == "100,50"

    def test_normalize_integer(self) -> None:
        """Test normalizing integer."""
        op = NormalizeDecimalOperation()
        context = OperationContext(field_name="test")

        result = op.apply("100", context, {})
        assert result == "100,00"

    def test_normalize_invalid(self) -> None:
        """Test invalid number."""
        op = NormalizeDecimalOperation()
        context = OperationContext(field_name="test")

        result = op.apply("abc", context, {})
        assert result == "abc"  # Returns original


class TestSetFieldOperation:
    """Tests for SetFieldOperation."""

    def test_set_field(self) -> None:
        """Test setting field value."""
        op = SetFieldOperation()
        context = OperationContext(field_name="test")

        result = op.apply("old", context, {"new_value": "new"})
        assert result == "new"


class TestOperationRegistry:
    """Tests for OperationRegistry."""

    def test_get_operation(self) -> None:
        """Test getting operation by type."""
        op = OperationRegistry.get(PatchOperation.UPPER)
        assert isinstance(op, UpperOperation)

    def test_apply_operation(self) -> None:
        """Test applying operation."""
        context = OperationContext(field_name="test")

        result = OperationRegistry.apply(
            PatchOperation.UPPER,
            "hello",
            context,
        )
        assert result == "HELLO"

    def test_apply_by_name(self) -> None:
        """Test applying operation by name."""
        context = OperationContext(field_name="test")

        result = OperationRegistry.apply_by_name(
            "upper",
            "hello",
            context,
        )
        assert result == "HELLO"

    def test_unknown_operation(self) -> None:
        """Test unknown operation raises error."""
        with pytest.raises(ValueError):
            OperationRegistry.apply_by_name(
                "unknown",
                "value",
                OperationContext(field_name="test"),
            )
