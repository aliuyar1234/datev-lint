"""
Fix operations implementation.

Implements individual patch operations: upper, truncate, sanitize, etc.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from typing import Any

from datev_lint.core.fix.models import OperationContext, PatchOperation

# =============================================================================
# Operation Interface
# =============================================================================


class Operation(ABC):
    """Base class for fix operations."""

    @abstractmethod
    def apply(self, value: str, context: OperationContext, params: dict[str, Any]) -> str:
        """Apply the operation to a value."""
        pass


# =============================================================================
# Concrete Operations
# =============================================================================


class SetFieldOperation(Operation):
    """Set field to a specific value."""

    def apply(self, value: str, context: OperationContext, params: dict[str, Any]) -> str:
        return str(params.get("new_value", value))


class UpperOperation(Operation):
    """Convert to uppercase."""

    def apply(self, value: str, context: OperationContext, params: dict[str, Any]) -> str:
        return value.upper()


class TruncateOperation(Operation):
    """Truncate to max length."""

    def apply(self, value: str, context: OperationContext, params: dict[str, Any]) -> str:
        max_length = params.get("max_length") or context.max_length
        if max_length is None:
            return value
        return value[:max_length]


class SanitizeCharsOperation(Operation):
    """Remove or replace invalid characters."""

    def apply(self, value: str, context: OperationContext, params: dict[str, Any]) -> str:
        pattern = params.get("pattern") or context.charset_pattern
        replacement = params.get("replacement", "")

        if pattern is None:
            return value

        # Pattern specifies invalid characters to remove
        return re.sub(pattern, replacement, value)


class NormalizeDecimalOperation(Operation):
    """Normalize decimal format to German comma notation."""

    def apply(self, value: str, context: OperationContext, params: dict[str, Any]) -> str:
        if not value.strip():
            return value

        # Handle both dot and comma as decimal separators
        normalized = value.replace(",", ".")

        try:
            decimal_value = Decimal(normalized)
            # Format with comma as decimal separator (German format)
            formatted = f"{decimal_value:,.2f}"
            # Convert to German format: swap comma and dot
            formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
            # Remove thousand separators for DATEV
            formatted = formatted.replace(".", "")
            return formatted
        except InvalidOperation:
            # Return original if not a valid number
            return value


class DeleteRowOperation(Operation):
    """Mark row for deletion (returns empty string as marker)."""

    def apply(self, value: str, context: OperationContext, params: dict[str, Any]) -> str:
        # Special marker for row deletion - handled by writer
        return "\x00DELETE\x00"


# =============================================================================
# Operation Registry
# =============================================================================


class OperationRegistry:
    """Registry of available operations."""

    _operations: dict[PatchOperation, Operation] = {
        PatchOperation.SET_FIELD: SetFieldOperation(),
        PatchOperation.UPPER: UpperOperation(),
        PatchOperation.TRUNCATE: TruncateOperation(),
        PatchOperation.SANITIZE_CHARS: SanitizeCharsOperation(),
        PatchOperation.NORMALIZE_DECIMAL: NormalizeDecimalOperation(),
        PatchOperation.DELETE_ROW: DeleteRowOperation(),
    }

    @classmethod
    def get(cls, operation: PatchOperation) -> Operation:
        """Get operation handler."""
        if operation not in cls._operations:
            raise ValueError(f"Unknown operation: {operation}")
        return cls._operations[operation]

    @classmethod
    def apply(
        cls,
        operation: PatchOperation,
        value: str,
        context: OperationContext,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Apply an operation to a value."""
        op = cls.get(operation)
        return op.apply(value, context, params or {})

    @classmethod
    def apply_by_name(
        cls,
        operation_name: str,
        value: str,
        context: OperationContext,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Apply an operation by name."""
        try:
            operation = PatchOperation(operation_name)
        except ValueError:
            raise ValueError(f"Unknown operation: {operation_name}")
        return cls.apply(operation, value, context, params)
