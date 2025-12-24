"""
CLI context and configuration.

Manages CLI state, exit codes, and shared context.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from pathlib import Path


class ExitCode(IntEnum):
    """CLI exit codes following Unix conventions."""

    SUCCESS = 0  # No issues found
    ERROR = 1  # Validation errors found
    FATAL = 2  # Fatal error (parse failure, etc.)
    USAGE = 64  # Command line usage error
    CONFIG = 78  # Configuration error


class CliContext(BaseModel):
    """Shared context for CLI commands."""

    # Output settings
    format: str = Field(default="terminal")
    output_file: Path | None = Field(default=None)
    color: bool = Field(default=True)
    quiet: bool = Field(default=False)
    verbose: bool = Field(default=False)

    # Validation settings
    profile: str = Field(default="default")
    fail_on: str = Field(default="error")  # error, warn, info

    # Fix settings
    dry_run: bool = Field(default=True)
    accept_risk: str = Field(default="low")  # low, medium, high
    auto_approve: bool = Field(default=False)
    write_mode: str = Field(default="preserve")  # preserve, canonical

    # Paths
    config_file: Path | None = Field(default=None)
    audit_dir: Path | None = Field(default=None)

    # Runtime
    engine_version: str = Field(default="0.1.0")
    _extra: dict[str, Any] = {}

    model_config = {"frozen": False}

    def get_fail_severity(self) -> str:
        """Get severity level that triggers failure."""
        return self.fail_on

    def should_fail_on(self, severity: str) -> bool:
        """Check if severity should trigger failure."""
        severity_order = {"fatal": 0, "error": 1, "warn": 2, "info": 3, "hint": 4}
        fail_level = severity_order.get(self.fail_on, 1)
        check_level = severity_order.get(severity.lower(), 4)
        return check_level <= fail_level


def get_exit_code(has_fatal: bool, has_error: bool, has_warn: bool, fail_on: str) -> ExitCode:
    """Determine exit code based on findings and fail_on setting."""
    if has_fatal:
        return ExitCode.FATAL

    fail_on_lower = fail_on.lower()

    if fail_on_lower == "warn":
        if has_error or has_warn:
            return ExitCode.ERROR
    elif fail_on_lower == "error":
        if has_error:
            return ExitCode.ERROR
    elif fail_on_lower == "fatal":
        pass  # Only fail on fatal

    return ExitCode.SUCCESS
