"""
Rule Engine data models.

Core models for rules, findings, profiles, and execution.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class Stage(Enum):
    """Execution stages in order."""

    PARSE = "parse"
    HEADER = "header"
    SCHEMA = "schema"
    ROW_SEMANTIC = "row_semantic"
    CROSS_ROW = "cross_row"
    POLICY = "policy"


class Severity(Enum):
    """Finding severity levels."""

    FATAL = "fatal"  # Cannot continue
    ERROR = "error"  # Likely import failure
    WARN = "warn"  # Risky
    INFO = "info"  # Informational
    HINT = "hint"  # Best practice


class RiskLevel(Enum):
    """Risk level for fix operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# =============================================================================
# Constraint Models
# =============================================================================


class Constraint(BaseModel, frozen=True):
    """Rule constraint definition."""

    type: str = Field(description="Constraint type: regex, max_length, enum, required, etc.")
    params: dict[str, Any] = Field(default_factory=dict)

    # Specific constraint parameters
    pattern: str | None = Field(default=None, description="Regex pattern")
    value: int | None = Field(default=None, description="Numeric value (max_length, etc.)")
    values: list[str] | None = Field(default=None, description="Allowed values for enum")
    field: str | None = Field(default=None, description="Target field for validation")

    model_config = {"frozen": True}


class FixStep(BaseModel, frozen=True):
    """Single step in a fix operation."""

    operation: str = Field(description="Operation type: upper, truncate, sanitize, etc.")
    params: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}


class FixStrategy(BaseModel, frozen=True):
    """How to fix a rule violation."""

    type: str = Field(description="Fix strategy type")
    steps: list[FixStep] = Field(default_factory=list)
    risk: RiskLevel = Field(default=RiskLevel.MEDIUM)
    requires_approval: bool = Field(default=False)

    model_config = {"frozen": True}


# =============================================================================
# Rule Model
# =============================================================================


class Rule(BaseModel, frozen=True):
    """
    Rule definition (from YAML or Python).

    CRITICAL: version is required for audit trail.
    """

    id: str = Field(description="Rule ID, e.g., DVL-FIELD-011")
    version: str = Field(description="Rule version for audit, e.g., 1.0.0")
    title: str = Field(description="Short title")
    stage: Stage = Field(description="Execution stage")
    severity: Severity = Field(description="Default severity")
    applies_to: str = Field(default="row", description="row, header, or file")

    # Selector
    selector: dict[str, str] = Field(
        default_factory=dict,
        description="Selector, e.g., {'field': 'belegfeld1'}",
    )

    # Constraint
    constraint: Constraint = Field(description="The validation constraint")

    # Messages
    message: dict[str, str] = Field(
        default_factory=dict,
        description="Localized messages: {'de': '...', 'en': '...'}",
    )
    docs_url: str | None = Field(default=None, description="Documentation URL")

    # Fix
    fix: FixStrategy | None = Field(default=None, description="Fix strategy if available")

    # Metadata
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")
    deprecated: bool = Field(default=False)

    model_config = {"frozen": True}

    def get_message(self, lang: str = "de") -> str:
        """Get message in specified language, fallback to English then first available."""
        if lang in self.message:
            return self.message[lang]
        if "en" in self.message:
            return self.message["en"]
        if self.message:
            return next(iter(self.message.values()))
        return self.title


# =============================================================================
# Finding Model
# =============================================================================


class Location(BaseModel, frozen=True):
    """Where a finding occurred."""

    file: str | None = None
    row_no: int | None = None
    column: int | None = None
    field: str | None = None

    model_config = {"frozen": True}

    def __str__(self) -> str:
        parts = []
        if self.file:
            parts.append(self.file)
        if self.row_no is not None:
            parts.append(f"row {self.row_no}")
        if self.column is not None:
            parts.append(f"col {self.column}")
        if self.field:
            parts.append(f"field '{self.field}'")
        return ", ".join(parts) if parts else "<unknown>"


class FixCandidate(BaseModel, frozen=True):
    """Proposed fix for a finding."""

    operation: str = Field(description="Fix operation type")
    field: str = Field(description="Field to fix")
    old_value: str = Field(description="Original value")
    new_value: str = Field(description="Proposed new value")
    risk: RiskLevel = Field(default=RiskLevel.MEDIUM)
    requires_approval: bool = Field(default=False)

    model_config = {"frozen": True}


class Finding(BaseModel, frozen=True):
    """
    Result of rule validation.

    CRITICAL: rule_version and engine_version required for audit.
    """

    code: str = Field(description="Rule ID that generated this finding")
    rule_version: str = Field(description="Version of the rule")
    engine_version: str = Field(description="Version of datev-lint engine")

    severity: Severity
    title: str
    message: str

    location: Location = Field(default_factory=Location)
    context: dict[str, Any] = Field(default_factory=dict)

    fix_candidates: list[FixCandidate] = Field(default_factory=list)
    related: list[Location] = Field(
        default_factory=list,
        description="Related locations for cross-row findings",
    )

    docs_url: str | None = None

    model_config = {"frozen": True}


# =============================================================================
# Profile Model
# =============================================================================


class ProfileOverrides(BaseModel, frozen=True):
    """Overrides for rules in this profile."""

    severity: dict[str, str] = Field(
        default_factory=dict,
        description="Override severity: {'DVL-FIELD-011': 'warn'}",
    )
    params: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Override params: {'DVL-PERIOD-001': {'max_days': 0}}",
    )
    disabled: list[str] = Field(
        default_factory=list,
        description="Disabled rule IDs",
    )

    model_config = {"frozen": True}


class Profile(BaseModel, frozen=True):
    """
    Rule profile configuration.

    Supports inheritance via 'base' field.
    """

    id: str = Field(description="Profile ID, e.g., de.skr03.default")
    version: str = Field(description="Profile version")
    label: str = Field(description="Human-readable label")
    base: str | None = Field(default=None, description="Parent profile ID for inheritance")

    # Rule selection
    enable: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Glob patterns for enabled rules",
    )
    disable: list[str] = Field(
        default_factory=list,
        description="Glob patterns for disabled rules",
    )

    # Overrides
    overrides: ProfileOverrides = Field(default_factory=ProfileOverrides)

    model_config = {"frozen": True}


# =============================================================================
# Execution Result Models
# =============================================================================


class ValidationSummary(BaseModel):
    """Summary of validation run."""

    file: str
    encoding: str
    row_count: int

    # Versions
    engine_version: str
    profile_id: str
    profile_version: str

    # Counts by severity
    fatal_count: int = 0
    error_count: int = 0
    warn_count: int = 0
    info_count: int = 0
    hint_count: int = 0

    # Top issues
    top_codes: list[tuple[str, int]] = Field(default_factory=list)

    # Timing
    duration_ms: int = 0

    @property
    def total_findings(self) -> int:
        """Total number of findings."""
        return self.fatal_count + self.error_count + self.warn_count + self.info_count

    @property
    def has_errors(self) -> bool:
        """Check if there are any fatal or error findings."""
        return self.fatal_count > 0 or self.error_count > 0
