"""
Terminal output adapter.

Renders findings with colors using Rich library.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

from datev_lint.cli.output.base import OutputAdapter, OutputFormat

if TYPE_CHECKING:
    from datev_lint.core.rules.models import Finding, ValidationSummary
    from datev_lint.core.rules.pipeline import PipelineResult
    from datev_lint.core.fix.models import PatchPlan


# Check if Unicode is supported
def _supports_unicode() -> bool:
    """Check if terminal supports Unicode."""
    try:
        "\u2713".encode(sys.stdout.encoding or "utf-8")
        return True
    except (UnicodeEncodeError, LookupError):
        return False


# Severity colors
SEVERITY_COLORS = {
    "fatal": "bold red",
    "error": "red",
    "warn": "yellow",
    "info": "blue",
    "hint": "dim",
}

# Unicode and ASCII fallback symbols
SEVERITY_SYMBOLS_UNICODE = {
    "fatal": "\u2716",
    "error": "\u2716",
    "warn": "\u26a0",
    "info": "\u2139",
    "hint": "\u2022",
}

SEVERITY_SYMBOLS_ASCII = {
    "fatal": "X",
    "error": "X",
    "warn": "!",
    "info": "i",
    "hint": "*",
}

SUCCESS_SYMBOL_UNICODE = "\u2713"
SUCCESS_SYMBOL_ASCII = "OK"


class TerminalOutput(OutputAdapter):
    """Terminal output with Rich colors."""

    format = OutputFormat.TERMINAL

    def __init__(self, stream: TextIO | None = None, color: bool = True):
        super().__init__(stream=stream, color=color)
        self._use_rich = color and self._is_tty()
        self._use_unicode = _supports_unicode()
        self._severity_symbols = SEVERITY_SYMBOLS_UNICODE if self._use_unicode else SEVERITY_SYMBOLS_ASCII
        self._success_symbol = SUCCESS_SYMBOL_UNICODE if self._use_unicode else SUCCESS_SYMBOL_ASCII

    def _is_tty(self) -> bool:
        """Check if output is a TTY."""
        return hasattr(self.stream, "isatty") and self.stream.isatty()

    def render_findings(
        self,
        findings: list["Finding"],
        summary: "ValidationSummary | None" = None,
    ) -> str:
        """Render findings to terminal string."""
        if not findings:
            return self._style(f"{self._success_symbol} No issues found.", "green")

        lines: list[str] = []

        # Group by file
        by_file: dict[str, list["Finding"]] = {}
        for finding in findings:
            file_key = finding.location.file or "<unknown>"
            if file_key not in by_file:
                by_file[file_key] = []
            by_file[file_key].append(finding)

        for file_path, file_findings in by_file.items():
            lines.append(self._style(f"\n{file_path}", "bold"))

            for finding in sorted(file_findings, key=lambda f: f.location.row_no or 0):
                lines.append(self._format_finding(finding))

        # Summary
        if summary:
            lines.append("")
            lines.append(self._format_summary(summary))

        return "\n".join(lines)

    def render_result(self, result: "PipelineResult") -> str:
        """Render pipeline result."""
        from datev_lint.core.rules.models import ValidationSummary

        # Create a basic summary if we have findings
        summary = ValidationSummary(
            file=result.file or "<unknown>",
            encoding="utf-8",
            row_count=0,
            engine_version="0.1.0",
            profile_id="default",
            profile_version="1.0.0",
            fatal_count=sum(1 for f in result.findings if f.severity.value == "fatal"),
            error_count=sum(1 for f in result.findings if f.severity.value == "error"),
            warn_count=sum(1 for f in result.findings if f.severity.value == "warn"),
            info_count=sum(1 for f in result.findings if f.severity.value == "info"),
            hint_count=sum(1 for f in result.findings if f.severity.value == "hint"),
        )

        return self.render_findings(result.findings, summary)

    def render_patch_plan(self, plan: "PatchPlan") -> str:
        """Render a patch plan preview."""
        if not plan.patches:
            return self._style(f"{self._success_symbol} No fixes to apply.", "green")

        lines: list[str] = []
        lines.append(self._style(f"\nFix preview for {plan.file_path}", "bold"))
        lines.append(f"Checksum: {plan.file_checksum[:12]}...")

        if plan.conflicts:
            warn_symbol = self._severity_symbols.get("warn", "!")
            lines.append(self._style(
                f"\n{warn_symbol} {len(plan.conflicts)} conflict(s) detected (first-wins resolution)",
                "yellow"
            ))

        lines.append("")

        current_row = -1
        for patch in sorted(plan.patches, key=lambda p: (p.row_no, p.field)):
            if patch.row_no != current_row:
                lines.append(self._style(f"Row {patch.row_no}:", "bold"))
                current_row = patch.row_no

            risk_color = {
                "low": "green",
                "medium": "yellow",
                "high": "red",
            }.get(patch.risk.value, "white")

            risk_label = self._style(f"[{patch.risk.value}]", risk_color)
            lines.append(f"  {patch.field}: {risk_label}")
            lines.append(f"    - {self._style(repr(patch.old_value), 'red')}")
            lines.append(f"    + {self._style(repr(patch.new_value), 'green')}")
            lines.append(f"    ({patch.rule_id})")

        # Summary
        lines.append("")
        lines.append(f"Total: {len(plan.patches)} patch(es)")
        if plan.requires_approval:
            warn_symbol = self._severity_symbols.get("warn", "!")
            lines.append(self._style(f"{warn_symbol} Some patches require approval", "yellow"))

        return "\n".join(lines)

    def _format_finding(self, finding: "Finding") -> str:
        """Format a single finding."""
        severity = finding.severity.value
        color = SEVERITY_COLORS.get(severity, "white")
        symbol = self._severity_symbols.get(severity, "*")

        # Location
        loc_parts = []
        if finding.location.row_no is not None:
            loc_parts.append(f"L{finding.location.row_no}")
        if finding.location.column is not None:
            loc_parts.append(f"C{finding.location.column}")
        if finding.location.field:
            loc_parts.append(finding.location.field)

        location_str = ":".join(loc_parts) if loc_parts else ""

        # Format line
        styled_symbol = self._style(symbol, color)
        styled_code = self._style(finding.code, "dim")

        if location_str:
            return f"  {styled_symbol} {location_str}: {finding.message} [{styled_code}]"
        else:
            return f"  {styled_symbol} {finding.message} [{styled_code}]"

    def _format_summary(self, summary: "ValidationSummary") -> str:
        """Format summary line."""
        parts = []

        if summary.fatal_count > 0:
            parts.append(self._style(f"{summary.fatal_count} fatal", "bold red"))
        if summary.error_count > 0:
            parts.append(self._style(f"{summary.error_count} error(s)", "red"))
        if summary.warn_count > 0:
            parts.append(self._style(f"{summary.warn_count} warning(s)", "yellow"))
        if summary.info_count > 0:
            parts.append(self._style(f"{summary.info_count} info", "blue"))

        if not parts:
            return self._style(f"{self._success_symbol} No issues found.", "green")

        return f"Found: {', '.join(parts)}"

    def _style(self, text: str, style: str) -> str:
        """Apply style to text if colors are enabled."""
        if not self._use_rich:
            return text

        # ANSI color codes
        codes = {
            "bold": "\033[1m",
            "dim": "\033[2m",
            "red": "\033[31m",
            "green": "\033[32m",
            "yellow": "\033[33m",
            "blue": "\033[34m",
            "bold red": "\033[1;31m",
            "white": "\033[37m",
        }
        reset = "\033[0m"

        code = codes.get(style, "")
        if code:
            return f"{code}{text}{reset}"
        return text
