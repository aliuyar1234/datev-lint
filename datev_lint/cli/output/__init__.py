"""
Output adapters for CLI.

Provides different output formats: terminal, JSON, SARIF, JUnit.
"""

from datev_lint.cli.output.base import OutputAdapter, OutputFormat, get_output_adapter
from datev_lint.cli.output.json import JsonOutput
from datev_lint.cli.output.junit import JunitOutput
from datev_lint.cli.output.sarif import SarifOutput
from datev_lint.cli.output.terminal import TerminalOutput

__all__ = [
    "JsonOutput",
    "JunitOutput",
    "OutputAdapter",
    "OutputFormat",
    "SarifOutput",
    "TerminalOutput",
    "get_output_adapter",
]
