"""Tests for CLI main module."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from datev_lint.cli.main import app

runner = CliRunner()


class TestVersion:
    """Tests for version command."""

    def test_version_option(self) -> None:
        """Test --version shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout

    def test_version_short_option(self) -> None:
        """Test -V shows version."""
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


class TestHelp:
    """Tests for help command."""

    def test_help_option(self) -> None:
        """Test --help shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "DATEV export file validator" in result.stdout

    def test_validate_help(self) -> None:
        """Test validate --help shows options."""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.stdout
        assert "--profile" in result.stdout

    def test_fix_help(self) -> None:
        """Test fix --help shows options."""
        result = runner.invoke(app, ["fix", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.stdout
        assert "--apply" in result.stdout


class TestValidate:
    """Tests for validate command."""

    def test_validate_valid_file(self, valid_minimal_700: Path) -> None:
        """Test validating a valid file."""
        result = runner.invoke(app, ["validate", str(valid_minimal_700)])
        # May have some findings but should not be fatal
        assert result.exit_code in (0, 1)

    def test_validate_file_not_found(self, tmp_path: Path) -> None:
        """Test validating non-existent file."""
        result = runner.invoke(app, ["validate", str(tmp_path / "nonexistent.csv")])
        assert result.exit_code != 0

    def test_validate_json_format(self, valid_minimal_700: Path) -> None:
        """Test validate with JSON output."""
        result = runner.invoke(app, ["validate", str(valid_minimal_700), "--format", "json"])
        assert result.exit_code in (0, 1)
        # Should be valid JSON
        import json
        output = json.loads(result.stdout)
        assert "findings" in output

    def test_validate_invalid_format(self, valid_minimal_700: Path) -> None:
        """Test validate with invalid format."""
        result = runner.invoke(app, ["validate", str(valid_minimal_700), "--format", "invalid"])
        assert result.exit_code != 0
        assert "Unknown format" in result.stdout or "Unknown format" in result.stderr or "invalid" in (result.stderr or "")


class TestProfiles:
    """Tests for profiles command."""

    def test_list_profiles(self) -> None:
        """Test listing profiles."""
        result = runner.invoke(app, ["profiles"])
        assert result.exit_code == 0
        assert "default" in result.stdout


class TestRules:
    """Tests for rules command."""

    def test_list_rules(self) -> None:
        """Test listing rules."""
        result = runner.invoke(app, ["rules"])
        assert result.exit_code == 0
        assert "DVL-FIELD-001" in result.stdout


class TestExplain:
    """Tests for explain command."""

    def test_explain_existing_rule(self) -> None:
        """Test explaining an existing rule."""
        result = runner.invoke(app, ["explain", "DVL-FIELD-001"])
        assert result.exit_code == 0
        assert "DVL-FIELD-001" in result.stdout

    def test_explain_unknown_rule(self) -> None:
        """Test explaining an unknown rule."""
        result = runner.invoke(app, ["explain", "DVL-UNKNOWN-999"])
        assert result.exit_code != 0
        assert "not found" in result.stdout or "not found" in (result.stderr or "")
