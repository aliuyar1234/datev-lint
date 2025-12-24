"""
Output adapter base classes.

Defines the interface for output adapters.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from datev_lint.core.fix.models import PatchPlan
    from datev_lint.core.rules.models import Finding, ValidationSummary
    from datev_lint.core.rules.pipeline import PipelineResult


class OutputFormat(Enum):
    """Supported output formats."""

    TERMINAL = "terminal"
    JSON = "json"
    SARIF = "sarif"
    JUNIT = "junit"


class OutputAdapter(ABC):
    """Base class for output adapters."""

    format: OutputFormat

    def __init__(self, stream: TextIO | None = None, color: bool = True):
        self.stream = stream or sys.stdout
        self.color = color

    @abstractmethod
    def render_findings(
        self,
        findings: list[Finding],
        summary: ValidationSummary | None = None,
    ) -> str:
        """Render findings to string."""
        pass

    @abstractmethod
    def render_result(self, result: PipelineResult) -> str:
        """Render pipeline result to string."""
        pass

    def write(self, content: str) -> None:
        """Write content to stream."""
        self.stream.write(content)
        if not content.endswith("\n"):
            self.stream.write("\n")
        self.stream.flush()

    def render_and_write(self, result: PipelineResult) -> None:
        """Render and write result to stream."""
        output = self.render_result(result)
        self.write(output)

    def render_patch_plan(self, plan: PatchPlan) -> str:
        """Render a patch plan. Override in subclasses that support it."""
        return ""


def get_output_adapter(
    format: OutputFormat | str,
    stream: TextIO | None = None,
    color: bool = True,
) -> OutputAdapter:
    """Get an output adapter by format."""
    if isinstance(format, str):
        format = OutputFormat(format)

    if format == OutputFormat.TERMINAL:
        from datev_lint.cli.output.terminal import TerminalOutput

        return TerminalOutput(stream=stream, color=color)
    elif format == OutputFormat.JSON:
        from datev_lint.cli.output.json import JsonOutput

        return JsonOutput(stream=stream, color=color)
    elif format == OutputFormat.SARIF:
        from datev_lint.cli.output.sarif import SarifOutput

        return SarifOutput(stream=stream, color=color)
    else:
        raise ValueError(f"Unknown output format: {format}")
