"""
DATEV Rule Engine.

Provides rule-based validation for DATEV files.

Usage:
    from datev_lint.core.parser import parse_file
    from datev_lint.core.rules import validate

    result = parse_file("EXTF_Buchungsstapel.csv")
    validation = validate(result)

    for finding in validation.findings:
        print(f"{finding.code}: {finding.message}")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .constraints import ConstraintRegistry
from .models import (
    Constraint,
    Finding,
    FixCandidate,
    FixStrategy,
    Location,
    Profile,
    ProfileOverrides,
    RiskLevel,
    Rule,
    Severity,
    Stage,
    ValidationSummary,
)
from .pipeline import ExecutionPipeline, PipelineResult
from .registry import RuleRegistry, get_registry, reset_registry

if TYPE_CHECKING:
    from datev_lint.core.parser import ParseResult


def validate(
    parse_result: ParseResult,
    profile: Profile | str | None = None,
) -> PipelineResult:
    """
    Validate a parsed DATEV file.

    Args:
        parse_result: Result from parse_file()
        profile: Profile instance, profile ID, or None for default

    Returns:
        PipelineResult with findings and summary
    """
    registry = get_registry()

    # Resolve profile
    resolved_profile: Profile | None = None
    if isinstance(profile, str):
        resolved_profile = registry.get_profile(profile)
    elif isinstance(profile, Profile):
        resolved_profile = profile

    # Run pipeline
    pipeline = ExecutionPipeline(registry=registry, profile=resolved_profile)
    return pipeline.run(parse_result)


def get_validation_summary(
    parse_result: ParseResult,
    pipeline_result: PipelineResult,
) -> ValidationSummary:
    """Create a validation summary from parse and pipeline results."""
    row_count = pipeline_result.row_count
    if row_count is None:
        row_count = 0
        for item in parse_result.rows:
            from datev_lint.core.parser import ParserError

            if not isinstance(item, ParserError):
                row_count += 1

    return pipeline_result.get_summary(
        file=str(parse_result.file_path),
        encoding=parse_result.encoding,
        row_count=row_count,
    )


__all__ = [
    "Constraint",
    # Constraints
    "ConstraintRegistry",
    # Pipeline
    "ExecutionPipeline",
    "Finding",
    "FixCandidate",
    "FixStrategy",
    "Location",
    "PipelineResult",
    "Profile",
    "ProfileOverrides",
    "RiskLevel",
    "Rule",
    # Registry
    "RuleRegistry",
    "Severity",
    # Models
    "Stage",
    "ValidationSummary",
    "get_registry",
    "get_validation_summary",
    "reset_registry",
    # Main function
    "validate",
]
