"""
Output adapters for CLI.

Provides different output formats: terminal, JSON, SARIF.
"""

from datev_lint.cli.output.base import OutputAdapter, OutputFormat, get_output_adapter
from datev_lint.cli.output.json import JsonOutput
from datev_lint.cli.output.sarif import SarifOutput
from datev_lint.cli.output.terminal import TerminalOutput

__all__ = [
    "JsonOutput",
    "OutputAdapter",
    "OutputFormat",
    "SarifOutput",
    "TerminalOutput",
    "get_output_adapter",
]
