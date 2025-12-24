"""Tests for rule engine."""

from pathlib import Path

import pytest

from datev_lint.core.parser import ParserError, parse_file
from datev_lint.core.rules import (
    Severity,
    get_registry,
    reset_registry,
    validate,
)


@pytest.fixture(autouse=True)
def reset_rule_registry() -> None:
    """Reset the rule registry before each test."""
    reset_registry()


class TestRuleRegistry:
    """Tests for RuleRegistry."""

    def test_registry_loads_builtin_rules(self) -> None:
        """Test that built-in rules are loaded."""
        registry = get_registry()
        assert len(registry.rules) > 0

    def test_registry_loads_profiles(self) -> None:
        """Test that profiles are loaded."""
        registry = get_registry()
        assert len(registry.profiles) > 0

    def test_get_rule_by_id(self) -> None:
        """Test getting a rule by ID."""
        registry = get_registry()
        rule = registry.get_rule("DVL-FIELD-001")
        assert rule is not None
        assert rule.id == "DVL-FIELD-001"

    def test_get_profile_by_id(self) -> None:
        """Test getting a profile by ID."""
        registry = get_registry()
        profile = registry.get_profile("default")
        assert profile is not None
        assert profile.id == "default"


class TestValidation:
    """Tests for validation function."""

    def test_validate_valid_file(self, valid_minimal_700: Path) -> None:
        """Test validation of a valid file."""
        result = parse_file(valid_minimal_700)
        validation = validate(result)

        # Valid file should have minimal findings
        error_count = sum(1 for f in validation.findings if f.severity == Severity.ERROR)
        assert error_count == 0

    def test_validate_detects_invalid_soll_haben(self) -> None:
        """Test that invalid S/H value is detected."""
        from datev_lint.core.parser import parse_bytes

        data = b'''"EXTF";700;21;"Buchungsstapel";13;20250101000000000;;;;;;"00001";"00002";20250101;4;20250101;20251231;"Test";;"";"";;"";"";"EUR";;;;;;;0
"Umsatz";"S/H";"Konto";"Gegenkonto";"Belegdatum"
"100,00";"X";"1200";"8400";"1501"
'''
        result = parse_bytes(data, "<test>")
        validation = validate(result)

        # Should find invalid S/H
        sh_findings = [f for f in validation.findings if f.code == "DVL-FIELD-005"]
        assert len(sh_findings) >= 1

    def test_validate_detects_missing_konto(self) -> None:
        """Test that missing Konto is detected."""
        from datev_lint.core.parser import parse_bytes

        data = b'''"EXTF";700;21;"Buchungsstapel";13;20250101000000000;;;;;;"00001";"00002";20250101;4;20250101;20251231;"Test";;"";"";;"";"";"EUR";;;;;;;0
"Umsatz";"S/H";"Konto";"Gegenkonto";"Belegdatum"
"100,00";"S";"";"8400";"1501"
'''
        result = parse_bytes(data, "<test>")
        validation = validate(result)

        # Should find missing Konto
        konto_findings = [f for f in validation.findings if f.code == "DVL-FIELD-001"]
        assert len(konto_findings) >= 1

    def test_validate_detects_belegfeld1_issues(self) -> None:
        """Test that Belegfeld 1 issues are detected."""
        from datev_lint.core.parser import parse_bytes

        data = b'''"EXTF";700;21;"Buchungsstapel";13;20250101000000000;;;;;;"00001";"00002";20250101;4;20250101;20251231;"Test";;"";"";;"";"";"EUR";;;;;;;0
"Umsatz";"S/H";"Konto";"Gegenkonto";"Belegdatum";"Belegfeld 1"
"100,00";"S";"1200";"8400";"1501";"lowercase-invalid"
'''
        result = parse_bytes(data, "<test>")
        validation = validate(result)

        # Should find Belegfeld 1 character issues
        bf_findings = [
            f for f in validation.findings if f.code in ("DVL-FIELD-011", "DVL-FIELD-013")
        ]
        assert len(bf_findings) >= 1


class TestConstraints:
    """Tests for constraint checkers."""

    def test_regex_constraint(self) -> None:
        """Test regex constraint checker."""
        from datev_lint.core.rules.constraints import ConstraintRegistry
        from datev_lint.core.rules.models import Constraint

        constraint = Constraint(type="regex", pattern=r"^\d+$")

        assert ConstraintRegistry.check("12345", constraint) is True
        assert ConstraintRegistry.check("abc", constraint) is False

    def test_max_length_constraint(self) -> None:
        """Test max_length constraint checker."""
        from datev_lint.core.rules.constraints import ConstraintRegistry
        from datev_lint.core.rules.models import Constraint

        constraint = Constraint(type="max_length", value=5)

        assert ConstraintRegistry.check("abc", constraint) is True
        assert ConstraintRegistry.check("abcdef", constraint) is False

    def test_enum_constraint(self) -> None:
        """Test enum constraint checker."""
        from datev_lint.core.rules.constraints import ConstraintRegistry
        from datev_lint.core.rules.models import Constraint

        constraint = Constraint(type="enum", values=["S", "H"])

        assert ConstraintRegistry.check("S", constraint) is True
        assert ConstraintRegistry.check("H", constraint) is True
        assert ConstraintRegistry.check("X", constraint) is False

    def test_required_constraint(self) -> None:
        """Test required constraint checker."""
        from datev_lint.core.rules.constraints import ConstraintRegistry
        from datev_lint.core.rules.models import Constraint

        constraint = Constraint(type="required")

        assert ConstraintRegistry.check("value", constraint) is True
        assert ConstraintRegistry.check("", constraint) is False
        assert ConstraintRegistry.check("   ", constraint) is False


class TestPipelineResult:
    """Tests for PipelineResult."""

    def test_has_fatal(self) -> None:
        """Test has_fatal property."""
        from datev_lint.core.rules.models import Finding, Location
        from datev_lint.core.rules.pipeline import PipelineResult

        result = PipelineResult(findings=[])
        assert result.has_fatal is False

        result = PipelineResult(
            findings=[
                Finding(
                    code="DVL-TEST-001",
                    rule_version="1.0.0",
                    engine_version="0.1.0",
                    severity=Severity.FATAL,
                    title="Test",
                    message="Test",
                    location=Location(),
                )
            ]
        )
        assert result.has_fatal is True

    def test_has_errors(self) -> None:
        """Test has_errors property."""
        from datev_lint.core.rules.models import Finding, Location
        from datev_lint.core.rules.pipeline import PipelineResult

        result = PipelineResult(
            findings=[
                Finding(
                    code="DVL-TEST-001",
                    rule_version="1.0.0",
                    engine_version="0.1.0",
                    severity=Severity.WARN,
                    title="Test",
                    message="Test",
                    location=Location(),
                )
            ]
        )
        assert result.has_errors is False

        result = PipelineResult(
            findings=[
                Finding(
                    code="DVL-TEST-001",
                    rule_version="1.0.0",
                    engine_version="0.1.0",
                    severity=Severity.ERROR,
                    title="Test",
                    message="Test",
                    location=Location(),
                )
            ]
        )
        assert result.has_errors is True
