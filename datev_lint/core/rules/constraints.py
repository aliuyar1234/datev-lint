"""
Constraint implementations for rule validation.

Each constraint type has a corresponding checker function.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Constraint


class ConstraintChecker(ABC):
    """Base class for constraint checkers."""

    @abstractmethod
    def check(self, value: str, constraint: "Constraint", context: dict[str, Any]) -> bool:
        """
        Check if value satisfies the constraint.

        Args:
            value: The value to check
            constraint: The constraint definition
            context: Additional context (header, row, etc.)

        Returns:
            True if valid, False if violation
        """
        ...

    @abstractmethod
    def get_message(self, value: str, constraint: "Constraint", lang: str = "de") -> str:
        """Get error message for violation."""
        ...


class RegexConstraint(ConstraintChecker):
    """Check value against regex pattern."""

    def check(self, value: str, constraint: "Constraint", context: dict[str, Any]) -> bool:
        if not constraint.pattern:
            return True
        try:
            return bool(re.match(constraint.pattern, value))
        except re.error:
            return False

    def get_message(self, value: str, constraint: "Constraint", lang: str = "de") -> str:
        if lang == "de":
            return f"Wert '{value}' entspricht nicht dem Muster '{constraint.pattern}'"
        return f"Value '{value}' does not match pattern '{constraint.pattern}'"


class MaxLengthConstraint(ConstraintChecker):
    """Check value does not exceed maximum length."""

    def check(self, value: str, constraint: "Constraint", context: dict[str, Any]) -> bool:
        if constraint.value is None:
            return True
        return len(value) <= constraint.value

    def get_message(self, value: str, constraint: "Constraint", lang: str = "de") -> str:
        if lang == "de":
            return f"Wert hat {len(value)} Zeichen, maximal {constraint.value} erlaubt"
        return f"Value has {len(value)} characters, maximum {constraint.value} allowed"


class MinLengthConstraint(ConstraintChecker):
    """Check value meets minimum length."""

    def check(self, value: str, constraint: "Constraint", context: dict[str, Any]) -> bool:
        if constraint.value is None:
            return True
        return len(value) >= constraint.value

    def get_message(self, value: str, constraint: "Constraint", lang: str = "de") -> str:
        if lang == "de":
            return f"Wert hat {len(value)} Zeichen, mindestens {constraint.value} erforderlich"
        return f"Value has {len(value)} characters, minimum {constraint.value} required"


class EnumConstraint(ConstraintChecker):
    """Check value is in allowed list."""

    def check(self, value: str, constraint: "Constraint", context: dict[str, Any]) -> bool:
        if not constraint.values:
            return True
        return value in constraint.values

    def get_message(self, value: str, constraint: "Constraint", lang: str = "de") -> str:
        allowed = ", ".join(constraint.values or [])
        if lang == "de":
            return f"Wert '{value}' nicht in erlaubten Werten: {allowed}"
        return f"Value '{value}' not in allowed values: {allowed}"


class RequiredConstraint(ConstraintChecker):
    """Check value is not empty."""

    def check(self, value: str, constraint: "Constraint", context: dict[str, Any]) -> bool:
        return bool(value and value.strip())

    def get_message(self, value: str, constraint: "Constraint", lang: str = "de") -> str:
        field = constraint.field or "Feld"
        if lang == "de":
            return f"{field} ist erforderlich"
        return f"{field} is required"


class CharsetConstraint(ConstraintChecker):
    """Check value only contains allowed characters."""

    # Predefined charsets
    CHARSETS = {
        "digits": r"^\d*$",
        "alphanumeric": r"^[A-Za-z0-9]*$",
        "belegfeld1": r"^[A-Z0-9_$&%*+\-/]*$",
        "uppercase": r"^[A-Z]*$",
    }

    def check(self, value: str, constraint: "Constraint", context: dict[str, Any]) -> bool:
        # Use pattern if provided, otherwise look up charset name
        pattern = constraint.pattern
        if not pattern and constraint.params.get("charset"):
            charset_name = constraint.params["charset"]
            pattern = self.CHARSETS.get(charset_name)

        if not pattern:
            return True

        try:
            return bool(re.match(pattern, value))
        except re.error:
            return False

    def get_message(self, value: str, constraint: "Constraint", lang: str = "de") -> str:
        charset = constraint.params.get("charset", "unbekannt")
        if lang == "de":
            return f"Wert enthält unerlaubte Zeichen für Zeichensatz '{charset}'"
        return f"Value contains invalid characters for charset '{charset}'"


class RangeConstraint(ConstraintChecker):
    """Check numeric value is within range."""

    def check(self, value: str, constraint: "Constraint", context: dict[str, Any]) -> bool:
        try:
            num = float(value.replace(",", "."))
            min_val = constraint.params.get("min")
            max_val = constraint.params.get("max")

            if min_val is not None and num < min_val:
                return False
            if max_val is not None and num > max_val:
                return False
            return True
        except ValueError:
            return False

    def get_message(self, value: str, constraint: "Constraint", lang: str = "de") -> str:
        min_val = constraint.params.get("min", "-∞")
        max_val = constraint.params.get("max", "∞")
        if lang == "de":
            return f"Wert '{value}' liegt nicht im Bereich [{min_val}, {max_val}]"
        return f"Value '{value}' is not in range [{min_val}, {max_val}]"


# =============================================================================
# Constraint Registry
# =============================================================================


class ConstraintRegistry:
    """Registry of available constraint checkers."""

    _checkers: dict[str, ConstraintChecker] = {}

    @classmethod
    def register(cls, constraint_type: str, checker: ConstraintChecker) -> None:
        """Register a constraint checker."""
        cls._checkers[constraint_type] = checker

    @classmethod
    def get(cls, constraint_type: str) -> ConstraintChecker | None:
        """Get checker for constraint type."""
        return cls._checkers.get(constraint_type)

    @classmethod
    def check(
        cls,
        value: str,
        constraint: "Constraint",
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check value against constraint."""
        checker = cls.get(constraint.type)
        if checker is None:
            # Unknown constraint type - pass
            return True
        return checker.check(value, constraint, context or {})

    @classmethod
    def get_message(
        cls,
        value: str,
        constraint: "Constraint",
        lang: str = "de",
    ) -> str:
        """Get error message for constraint violation."""
        checker = cls.get(constraint.type)
        if checker is None:
            return f"Constraint '{constraint.type}' violated"
        return checker.get_message(value, constraint, lang)


# Register built-in constraints
ConstraintRegistry.register("regex", RegexConstraint())
ConstraintRegistry.register("max_length", MaxLengthConstraint())
ConstraintRegistry.register("min_length", MinLengthConstraint())
ConstraintRegistry.register("enum", EnumConstraint())
ConstraintRegistry.register("required", RequiredConstraint())
ConstraintRegistry.register("charset", CharsetConstraint())
ConstraintRegistry.register("range", RangeConstraint())
