"""Optional integration tests against real-world DATEV exports.

These tests are skipped by default and only run when `DATEV_LINT_INTEGRATION_DIR`
is set to a directory containing `.csv` files.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from datev_lint.cli.main import app

runner = CliRunner()


def _get_integration_dir() -> Path:
    value = os.environ.get("DATEV_LINT_INTEGRATION_DIR")
    if not value:
        pytest.skip("Set DATEV_LINT_INTEGRATION_DIR to run integration tests.")

    path = Path(value)
    if not path.exists() or not path.is_dir():
        pytest.skip(f"DATEV_LINT_INTEGRATION_DIR is not a directory: {path}")

    return path


def _get_limit() -> int:
    raw = os.environ.get("DATEV_LINT_INTEGRATION_LIMIT", "10").strip()
    if not raw:
        return 10
    try:
        value = int(raw)
    except ValueError:
        pytest.skip("DATEV_LINT_INTEGRATION_LIMIT must be an integer.")
    return value


def _max_bytes_args() -> list[str]:
    raw = os.environ.get("DATEV_LINT_INTEGRATION_MAX_BYTES")
    if raw is None or not raw.strip():
        return []
    return ["--max-bytes", raw.strip()]


def test_validate_real_exports_as_json() -> None:
    integration_dir = _get_integration_dir()
    limit = _get_limit()

    files = sorted(
        p for p in integration_dir.rglob("*.csv") if p.is_file() and not p.name.startswith(".")
    )
    if not files:
        pytest.skip(f"No .csv files found under: {integration_dir}")

    files_to_check = files if limit <= 0 else files[:limit]

    for file_path in files_to_check:
        result = runner.invoke(
            app,
            ["validate", str(file_path), "--format", "json", "--no-color", *_max_bytes_args()],
        )

        assert result.exit_code in (0, 1), (
            file_path,
            result.exit_code,
            result.stdout,
            result.stderr,
        )
