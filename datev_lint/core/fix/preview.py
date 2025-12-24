"""
Preview/diff generation for fix engine.

Generates human-readable diffs of patches without applying them.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO

from datev_lint.core.rules.models import RiskLevel

if TYPE_CHECKING:
    from datev_lint.core.fix.models import Patch, PatchPlan


@dataclass
class DiffLine:
    """Single line in a diff output."""

    line_no: int
    old_value: str
    new_value: str
    field: str
    rule_id: str
    risk: RiskLevel


@dataclass
class DiffOutput:
    """Complete diff output for a patch plan."""

    file_path: str
    original_checksum: str
    lines: list[DiffLine]
    conflicts_count: int = 0

    @property
    def total_changes(self) -> int:
        """Total number of changes."""
        return len(self.lines)

    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return len(self.lines) > 0


class DiffGenerator:
    """Generates diff previews from patch plans."""

    def __init__(self, colorize: bool = True):
        self.colorize = colorize

    def generate(self, plan: PatchPlan) -> DiffOutput:
        """Generate diff from patch plan."""
        lines: list[DiffLine] = []

        for patch in plan.patches:
            line = DiffLine(
                line_no=patch.row_no,
                old_value=patch.old_value,
                new_value=patch.new_value,
                field=patch.field,
                rule_id=patch.rule_id,
                risk=patch.risk,
            )
            lines.append(line)

        return DiffOutput(
            file_path=plan.file_path,
            original_checksum=plan.file_checksum,
            lines=lines,
            conflicts_count=len(plan.conflicts),
        )

    def format(self, diff: DiffOutput, output: TextIO | None = None) -> str:
        """Format diff for display."""
        if output is None:
            output = sys.stdout

        lines: list[str] = []

        # Header
        lines.append(f"--- {diff.file_path} (original)")
        lines.append(f"+++ {diff.file_path} (fixed)")
        lines.append(f"Checksum: {diff.original_checksum[:12]}...")
        lines.append("")

        if diff.conflicts_count > 0:
            lines.append(f"⚠ {diff.conflicts_count} conflict(s) detected (first-wins resolution)")
            lines.append("")

        if not diff.has_changes():
            lines.append("No changes to apply.")
            return "\n".join(lines)

        # Group by row
        current_row = -1
        for line in sorted(diff.lines, key=lambda x: (x.line_no, x.field)):
            if line.line_no != current_row:
                if current_row != -1:
                    lines.append("")
                lines.append(f"@@ Row {line.line_no} @@")
                current_row = line.line_no

            # Risk indicator
            risk_indicator = self._risk_symbol(line.risk)

            # Format change
            old_display = self._format_value(line.old_value, is_old=True)
            new_display = self._format_value(line.new_value, is_old=False)

            lines.append(f"  {line.field}: {risk_indicator}")
            lines.append(f"    - {old_display}")
            lines.append(f"    + {new_display}")
            lines.append(f"    ({line.rule_id})")

        # Summary
        lines.append("")
        lines.append(f"Summary: {len(diff.lines)} change(s)")

        return "\n".join(lines)

    def _risk_symbol(self, risk: RiskLevel) -> str:
        """Get risk level symbol."""
        if risk == RiskLevel.LOW:
            return "[low]" if not self.colorize else "\033[32m[low]\033[0m"
        elif risk == RiskLevel.MEDIUM:
            return "[medium]" if not self.colorize else "\033[33m[medium]\033[0m"
        else:
            return "[HIGH]" if not self.colorize else "\033[31m[HIGH]\033[0m"

    def _format_value(self, value: str, is_old: bool) -> str:
        """Format value for display."""
        # Escape special characters
        display = repr(value)[1:-1]  # Remove quotes from repr

        if self.colorize:
            color = "\033[31m" if is_old else "\033[32m"
            return f"{color}\"{display}\"\033[0m"
        return f'"{display}"'


def preview_diff(plan: PatchPlan, colorize: bool = True) -> str:
    """
    Generate a preview diff from a patch plan.

    Args:
        plan: The patch plan to preview
        colorize: Whether to add ANSI colors

    Returns:
        Formatted diff string
    """
    generator = DiffGenerator(colorize=colorize)
    diff = generator.generate(plan)
    return generator.format(diff)


def preview_patch(patch: Patch, colorize: bool = True) -> str:
    """
    Generate a preview for a single patch.

    Args:
        patch: The patch to preview
        colorize: Whether to add ANSI colors

    Returns:
        Formatted patch string
    """
    risk_symbol = {
        RiskLevel.LOW: "[low]",
        RiskLevel.MEDIUM: "[medium]",
        RiskLevel.HIGH: "[HIGH]",
    }[patch.risk]

    if colorize:
        old_color = "\033[31m"
        new_color = "\033[32m"
        reset = "\033[0m"
        old_display = f'{old_color}"{patch.old_value}"{reset}'
        new_display = f'{new_color}"{patch.new_value}"{reset}'
    else:
        old_display = f'"{patch.old_value}"'
        new_display = f'"{patch.new_value}"'

    return f'Row {patch.row_no}, {patch.field} {risk_symbol}: {old_display} → {new_display} ({patch.rule_id})'
