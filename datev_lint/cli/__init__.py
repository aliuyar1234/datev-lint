"""
CLI for DATEV Lint.

Command-line interface for validating and fixing DATEV export files.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from datev_lint.cli.context import CliContext, ExitCode

if TYPE_CHECKING:
    from typer import Typer

    app: Typer


def __getattr__(name: str) -> Any:
    if name == "app":
        from datev_lint.cli.main import app as _app

        return _app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CliContext",
    "ExitCode",
    "app",
]
