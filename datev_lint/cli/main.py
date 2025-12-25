"""
Main CLI application.

Entry point for datev-lint command.
"""

from __future__ import annotations

import os
from pathlib import Path  # noqa: TC003
from typing import Annotated

import typer

import datev_lint
from datev_lint.cli.context import ExitCode, get_exit_code
from datev_lint.cli.output import OutputFormat, get_output_adapter

# Default input size limit for CLI usage (can be overridden via flag/env).
_DEFAULT_MAX_BYTES = 100 * 1024 * 1024  # 100 MiB


def _resolve_max_bytes(max_bytes: int | None) -> int | None:
    if max_bytes is not None:
        return None if max_bytes <= 0 else max_bytes

    env_value = os.environ.get("DATEV_LINT_MAX_BYTES")
    if env_value:
        try:
            parsed = int(env_value)
        except ValueError:
            raise typer.BadParameter("DATEV_LINT_MAX_BYTES must be an integer") from None
        return None if parsed <= 0 else parsed

    return _DEFAULT_MAX_BYTES


# Create main app
app = typer.Typer(
    name="datev-lint",
    help="DATEV export file validator and linter",
    add_completion=False,
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"datev-lint {datev_lint.__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """DATEV export file validator and linter."""
    pass


# =============================================================================
# Validate Command
# =============================================================================


@app.command()
def validate(
    file: Annotated[Path, typer.Argument(help="DATEV file to validate", exists=True)],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: terminal, json, sarif, junit (Pro)"),
    ] = "terminal",
    profile: Annotated[
        str,
        typer.Option("--profile", "-p", help="Validation profile to use"),
    ] = "default",
    fail_on: Annotated[
        str,
        typer.Option("--fail-on", help="Severity level that triggers failure: error, warn, fatal"),
    ] = "error",
    output: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Write output to file"),
    ] = None,
    color: Annotated[
        bool,
        typer.Option("--color/--no-color", help="Enable/disable colored output"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress non-error output"),
    ] = False,
    max_bytes: Annotated[
        int | None,
        typer.Option(
            "--max-bytes",
            help="Maximum input size in bytes (0 = unlimited). Defaults to DATEV_LINT_MAX_BYTES or 100MiB.",
        ),
    ] = None,
) -> None:
    """Validate a DATEV export file."""
    from datev_lint.core.parser import parse_file
    from datev_lint.core.rules import get_registry
    from datev_lint.core.rules import validate as run_validation

    max_bytes_value = _resolve_max_bytes(max_bytes)

    # Parse the file
    try:
        parse_result = parse_file(file, max_bytes=max_bytes_value)
    except Exception as e:
        typer.echo(f"Error parsing file: {e}", err=True)
        raise typer.Exit(ExitCode.FATAL) from None

    # Validate
    registry = get_registry()
    profile_obj = registry.get_profile(profile)
    if profile_obj is None:
        typer.echo(f"Profile not found: {profile}", err=True)
        typer.echo("Available profiles:", err=True)
        for p in registry.profiles.values():
            typer.echo(f"  - {p.id}: {p.label}", err=True)
        raise typer.Exit(ExitCode.CONFIG)

    result = run_validation(parse_result, profile=profile)

    # Get output adapter
    try:
        output_format = OutputFormat(format)
    except ValueError:
        typer.echo(f"Unknown format: {format}", err=True)
        typer.echo("Available formats: terminal, json, sarif, junit", err=True)
        raise typer.Exit(ExitCode.USAGE) from None

    if output_format == OutputFormat.JUNIT:
        from datev_lint.core.licensing import Feature, check_feature, get_upgrade_cta

        if not check_feature(Feature.JUNIT_OUTPUT):
            typer.echo("", err=True)
            typer.secho("Pro License Required", fg=typer.colors.YELLOW, bold=True, err=True)
            typer.echo(get_upgrade_cta(Feature.JUNIT_OUTPUT), err=True)
            typer.echo("", err=True)
            raise typer.Exit(ExitCode.ERROR)

    try:
        adapter = get_output_adapter(output_format, color=color)
    except ValueError:
        typer.echo(f"Unknown format: {format}", err=True)
        typer.echo("Available formats: terminal, json, sarif, junit", err=True)
        raise typer.Exit(ExitCode.USAGE) from None

    # Render output
    rendered = adapter.render_result(result)

    # Write to file or stdout
    if output:
        output.write_text(rendered, encoding="utf-8")
        if not quiet:
            typer.echo(f"Output written to {output}")
    else:
        typer.echo(rendered)

    # Determine exit code
    has_fatal = any(f.severity.value == "fatal" for f in result.findings)
    has_error = any(f.severity.value == "error" for f in result.findings)
    has_warn = any(f.severity.value == "warn" for f in result.findings)

    exit_code = get_exit_code(has_fatal, has_error, has_warn, fail_on)
    raise typer.Exit(exit_code)


# =============================================================================
# Fix Command
# =============================================================================


@app.command()
def fix(
    file: Annotated[Path, typer.Argument(help="DATEV file to fix", exists=True)],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--no-dry-run", help="Preview fixes without applying"),
    ] = True,
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Apply fixes (Pro feature)"),
    ] = False,
    write_mode: Annotated[
        str,
        typer.Option("--write-mode", help="Write mode: preserve, canonical"),
    ] = "preserve",
    accept_risk: Annotated[
        str,
        typer.Option("--accept-risk", help="Risk level to accept: low, medium, high"),
    ] = "low",
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Auto-approve all prompts"),
    ] = False,
    profile: Annotated[
        str,
        typer.Option("--profile", "-p", help="Validation profile to use"),
    ] = "default",
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: terminal, json"),
    ] = "terminal",
    color: Annotated[
        bool,
        typer.Option("--color/--no-color", help="Enable/disable colored output"),
    ] = True,
    max_bytes: Annotated[
        int | None,
        typer.Option(
            "--max-bytes",
            help="Maximum input size in bytes (0 = unlimited). Defaults to DATEV_LINT_MAX_BYTES or 100MiB.",
        ),
    ] = None,
) -> None:
    """Fix issues in a DATEV export file."""
    from datev_lint.core.fix import apply_fixes
    from datev_lint.core.fix import plan as plan_fixes
    from datev_lint.core.fix.models import WriteMode
    from datev_lint.core.parser import parse_file
    from datev_lint.core.rules import validate as run_validation
    from datev_lint.core.rules.models import RiskLevel

    max_bytes_value = _resolve_max_bytes(max_bytes)

    # Parse the file
    try:
        parse_result = parse_file(file, max_bytes=max_bytes_value)
    except Exception as e:
        typer.echo(f"Error parsing file: {e}", err=True)
        raise typer.Exit(ExitCode.FATAL) from None

    # Validate to get findings
    result = run_validation(parse_result, profile=profile)

    # Plan fixes
    fix_plan = plan_fixes(file, result)

    if fix_plan.total_patches == 0:
        typer.echo("No fixes available.")
        raise typer.Exit(ExitCode.SUCCESS)

    # Get output adapter
    try:
        output_format = OutputFormat(format)
    except ValueError:
        typer.echo(f"Unknown format: {format}", err=True)
        typer.echo("Available formats: terminal, json", err=True)
        raise typer.Exit(ExitCode.USAGE) from None

    if output_format not in {OutputFormat.TERMINAL, OutputFormat.JSON}:
        typer.echo(f"Unknown format: {format}", err=True)
        typer.echo("Available formats: terminal, json", err=True)
        raise typer.Exit(ExitCode.USAGE)

    adapter = get_output_adapter(output_format, color=color)

    # --apply implies not dry_run
    if apply:
        dry_run = False

    if not dry_run:
        # Apply fixes (Pro feature) - check license
        from datev_lint.core.licensing import (
            Feature,
            check_feature,
            get_upgrade_cta,
        )

        if not check_feature(Feature.FIX_APPLY):
            typer.echo("", err=True)
            typer.secho("Pro License Required", fg=typer.colors.YELLOW, bold=True, err=True)
            typer.echo(get_upgrade_cta(Feature.FIX_APPLY), err=True)
            typer.echo("", err=True)
            raise typer.Exit(ExitCode.ERROR)

        try:
            risk_level = RiskLevel(accept_risk)
        except ValueError:
            typer.echo(f"Invalid risk level: {accept_risk}", err=True)
            raise typer.Exit(ExitCode.USAGE) from None

        try:
            mode = WriteMode(write_mode)
        except ValueError:
            typer.echo(f"Invalid write mode: {write_mode}", err=True)
            raise typer.Exit(ExitCode.USAGE) from None

        # Show preview first
        typer.echo(adapter.render_patch_plan(fix_plan))

        # Confirm if not auto-approved
        if not yes and fix_plan.requires_approval and not typer.confirm("Apply these fixes?"):
            typer.echo("Aborted.")
            raise typer.Exit(ExitCode.SUCCESS)

        # Apply
        write_result, audit_entry = apply_fixes(
            fix_plan,
            parse_result,
            mode=mode,
            accept_risk=risk_level,
            profile_id=profile,
        )

        if write_result.success:
            typer.echo(f"\n✓ Applied {write_result.patches_applied} fix(es)")
            if write_result.backup_path:
                typer.echo(f"  Backup: {write_result.backup_path}")
            if audit_entry:
                typer.echo(f"  Run ID: {audit_entry.run_id}")
        else:
            typer.echo(f"\n✖ Failed to apply fixes: {write_result.error}", err=True)
            raise typer.Exit(ExitCode.ERROR)
    else:
        # Dry run - just show preview
        typer.echo(adapter.render_patch_plan(fix_plan))
        typer.echo("\nUse --apply to apply these fixes.")

    raise typer.Exit(ExitCode.SUCCESS)


# =============================================================================
# Utility Commands
# =============================================================================


@app.command("profiles")
def list_profiles() -> None:
    """List available validation profiles."""
    from datev_lint.core.rules import get_registry

    registry = get_registry()

    typer.echo("Available profiles:\n")
    for profile in registry.profiles.values():
        base_info = f" (extends: {profile.base})" if profile.base else ""
        typer.echo(f"  {profile.id}{base_info}")
        typer.echo(f"    {profile.label}")
        typer.echo()


@app.command("rules")
def list_rules(
    profile: Annotated[
        str,
        typer.Option("--profile", "-p", help="Filter by profile"),
    ] = "default",
    severity: Annotated[
        str | None,
        typer.Option("--severity", "-s", help="Filter by severity"),
    ] = None,
) -> None:
    """List available validation rules."""
    from datev_lint.core.rules import get_registry

    registry = get_registry()

    typer.echo(f"Rules (profile: {profile}):\n")

    for rule in sorted(registry.rules.values(), key=lambda r: r.id):
        if severity and rule.severity.value != severity:
            continue

        sev_color = {
            "fatal": typer.colors.RED,
            "error": typer.colors.RED,
            "warn": typer.colors.YELLOW,
            "info": typer.colors.BLUE,
            "hint": typer.colors.WHITE,
        }.get(rule.severity.value, typer.colors.WHITE)

        typer.secho(f"  {rule.id}", bold=True, nl=False)
        typer.secho(f" [{rule.severity.value}]", fg=sev_color)
        typer.echo(f"    {rule.title}")


@app.command()
def explain(
    code: Annotated[str, typer.Argument(help="Rule code to explain, e.g., DVL-FIELD-011")],
) -> None:
    """Explain a validation rule in detail."""
    from datev_lint.core.rules import get_registry

    registry = get_registry()
    rule = registry.get_rule(code)

    if rule is None:
        typer.echo(f"Rule not found: {code}", err=True)
        raise typer.Exit(ExitCode.USAGE)

    typer.secho(f"\n{rule.id}", bold=True)
    typer.echo(f"Version: {rule.version}")
    typer.echo(f"Severity: {rule.severity.value}")
    typer.echo(f"Stage: {rule.stage.value}")
    typer.echo()

    typer.secho("Title:", bold=True)
    typer.echo(f"  {rule.title}")
    typer.echo()

    typer.secho("Message:", bold=True)
    for lang, msg in rule.message.items():
        typer.echo(f"  [{lang}] {msg}")
    typer.echo()

    if rule.fix:
        typer.secho("Fix available:", bold=True)
        typer.echo(f"  Type: {rule.fix.type}")
        typer.echo(f"  Risk: {rule.fix.risk.value}")
        for step in rule.fix.steps:
            typer.echo(f"  - {step.operation}")

    if rule.docs_url:
        typer.echo()
        typer.echo(f"Documentation: {rule.docs_url}")


@app.command()
def rollback(
    run_id: Annotated[str, typer.Argument(help="Run ID to rollback")],
    audit_dir: Annotated[
        Path | None,
        typer.Option("--audit-dir", help="Audit log directory"),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm rollback without prompting"),
    ] = False,
) -> None:
    """Rollback a fix operation by run ID."""
    from datev_lint.core.fix import get_audit_entry
    from datev_lint.core.fix import rollback as do_rollback
    from datev_lint.core.licensing import Feature, check_feature, get_upgrade_cta

    if not check_feature(Feature.ROLLBACK):
        typer.echo("", err=True)
        typer.secho("Pro License Required", fg=typer.colors.YELLOW, bold=True, err=True)
        typer.echo(get_upgrade_cta(Feature.ROLLBACK), err=True)
        typer.echo("", err=True)
        raise typer.Exit(ExitCode.ERROR)

    entry = get_audit_entry(run_id, audit_dir=audit_dir)
    if entry is None:
        typer.echo(f"Run ID not found: {run_id}", err=True)
        raise typer.Exit(ExitCode.ERROR)

    if not yes:
        prompt = (
            f"Rollback run {run_id}?\n"
            f"This will overwrite: {entry.file_path}\n"
            f"Using backup: {entry.backup_path or '<none>'}"
        )
        if not typer.confirm(prompt):
            typer.echo("Aborted.")
            raise typer.Exit(ExitCode.SUCCESS)

    result = do_rollback(run_id, audit_dir=audit_dir)

    if result.success:
        typer.echo("✓ Rollback successful")
        typer.echo(f"  File: {result.file_path}")
        typer.echo(f"  Backup used: {result.backup_path}")
        if result.checksums_match:
            typer.echo("  Checksum verified ✓")
        else:
            typer.secho("  Warning: Checksum mismatch!", fg=typer.colors.YELLOW)
    else:
        typer.echo(f"✖ Rollback failed: {result.error}", err=True)
        raise typer.Exit(ExitCode.ERROR)


# =============================================================================
# CLI Entry Point
# =============================================================================


def run() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    run()
