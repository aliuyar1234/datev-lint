"""
File writer for fix engine.

Implements preserve and canonical write modes with atomic writes.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from datev_lint.core.fix.models import (
    OperationContext,
    Patch,
    PatchPlan,
    WriteMode,
    WriteResult,
)
from datev_lint.core.fix.operations import OperationRegistry
from datev_lint.core.fix.planner import compute_bytes_checksum

if TYPE_CHECKING:
    from datev_lint.core.parser.models import ParseResult


# =============================================================================
# Writer Interface
# =============================================================================


class Writer(ABC):
    """Base class for file writers."""

    @abstractmethod
    def write(
        self,
        plan: PatchPlan,
        parse_result: ParseResult,
        output_path: Path,
    ) -> bytes:
        """
        Write patched content.

        Args:
            plan: Patch plan to apply
            parse_result: Original parse result
            output_path: Path to write to

        Returns:
            Written bytes
        """
        pass


# =============================================================================
# Preserve Mode Writer
# =============================================================================


class PreserveWriter(Writer):
    """
    Writer that preserves original formatting.

    Only modifies the specific fields that need patching.
    """

    def write(
        self,
        plan: PatchPlan,
        parse_result: ParseResult,
        output_path: Path,
    ) -> bytes:
        """Write with minimal changes."""
        # Read original file
        original_bytes = Path(plan.file_path).read_bytes()
        original_text = original_bytes.decode(parse_result.encoding)

        # Split into lines (preserving line endings)
        lines = self._split_lines(original_text)

        # Group patches by row
        patches_by_row: dict[int, list[Patch]] = {}
        for patch in plan.patches:
            if patch.row_no not in patches_by_row:
                patches_by_row[patch.row_no] = []
            patches_by_row[patch.row_no].append(patch)

        # Apply patches to each affected row
        for row_no, patches in patches_by_row.items():
            # Row numbers are 1-indexed, lines are 0-indexed
            line_idx = row_no - 1
            if line_idx < 0 or line_idx >= len(lines):
                continue

            line_content, line_ending = lines[line_idx]
            new_line = self._apply_patches_to_line(line_content, patches, parse_result)
            lines[line_idx] = (new_line, line_ending)

        # Reconstruct file
        result = "".join(content + ending for content, ending in lines)

        # Encode back to original encoding
        result_bytes = result.encode(parse_result.encoding)

        return result_bytes

    def _split_lines(self, text: str) -> list[tuple[str, str]]:
        """Split text into lines, preserving line endings."""
        result: list[tuple[str, str]] = []
        i = 0
        start = 0

        while i < len(text):
            if text[i] == "\r":
                if i + 1 < len(text) and text[i + 1] == "\n":
                    result.append((text[start:i], "\r\n"))
                    i += 2
                else:
                    result.append((text[start:i], "\r"))
                    i += 1
                start = i
            elif text[i] == "\n":
                result.append((text[start:i], "\n"))
                i += 1
                start = i
            else:
                i += 1

        # Last line (may not have ending)
        if start < len(text):
            result.append((text[start:], ""))

        return result

    def _apply_patches_to_line(
        self,
        line: str,
        patches: list[Patch],
        parse_result: ParseResult,
    ) -> str:
        """Apply patches to a single line while preserving formatting."""
        # Parse the line into tokens
        tokens = self._tokenize_csv_line(line)

        # Get column mapping
        column_map = parse_result.columns

        for patch in patches:
            # Find column index for this field
            col_idx = column_map.get_index(patch.field)
            if col_idx is None:
                continue
            if col_idx >= len(tokens):
                continue

            # Get original token
            original_token = tokens[col_idx]

            # Determine if was quoted
            was_quoted = original_token.startswith('"') and original_token.endswith('"')

            # Extract value
            if was_quoted:
                original_value = original_token[1:-1].replace('""', '"')
            else:
                original_value = original_token

            # Apply operation
            context = OperationContext(field_name=patch.field)
            new_value = OperationRegistry.apply(
                patch.operation,
                original_value,
                context,
                {"new_value": patch.new_value},
            )

            # Re-quote if was quoted
            if was_quoted:
                new_value = '"' + new_value.replace('"', '""') + '"'

            tokens[col_idx] = new_value

        return ";".join(tokens)

    def _tokenize_csv_line(self, line: str) -> list[str]:
        """Tokenize a CSV line, preserving quotes."""
        tokens: list[str] = []
        current = ""
        in_quotes = False
        i = 0

        while i < len(line):
            c = line[i]

            if c == '"':
                if in_quotes:
                    # Check for escaped quote
                    if i + 1 < len(line) and line[i + 1] == '"':
                        current += '""'
                        i += 2
                        continue
                    else:
                        in_quotes = False
                else:
                    in_quotes = True
                current += c
            elif c == ";" and not in_quotes:
                tokens.append(current)
                current = ""
            else:
                current += c
            i += 1

        tokens.append(current)
        return tokens


# =============================================================================
# Canonical Mode Writer
# =============================================================================


class CanonicalWriter(Writer):
    """
    Writer that produces standardized output.

    All fields are quoted, CRLF line endings, standard encoding.
    """

    CANONICAL_ENCODING = "windows-1252"
    CANONICAL_LINE_ENDING = "\r\n"

    def write(
        self,
        plan: PatchPlan,
        parse_result: ParseResult,
        output_path: Path,
    ) -> bytes:
        """Write with canonical formatting."""
        lines: list[str] = []

        # Write header (row 1)
        header_tokens = self._quote_all(parse_result.header.raw_tokens)
        lines.append(";".join(header_tokens))

        # Write column headers (row 2)
        column_tokens = self._quote_all(parse_result.columns.raw_labels)
        lines.append(";".join(column_tokens))

        # Group patches by row
        patches_by_row: dict[int, list[Patch]] = {}
        for patch in plan.patches:
            if patch.row_no not in patches_by_row:
                patches_by_row[patch.row_no] = []
            patches_by_row[patch.row_no].append(patch)

        # Write data rows (row 3+)
        for row in parse_result.rows:
            row_no = row.row_no
            tokens = list(row.raw_tokens)

            # Apply patches if any
            if row_no in patches_by_row:
                for patch in patches_by_row[row_no]:
                    col_idx = parse_result.columns.get_index(patch.field)
                    if col_idx is None or col_idx >= len(tokens):
                        continue

                    # Apply operation
                    context = OperationContext(field_name=patch.field)
                    tokens[col_idx] = OperationRegistry.apply(
                        patch.operation,
                        tokens[col_idx],
                        context,
                        {"new_value": patch.new_value},
                    )

            # Quote all tokens
            quoted_tokens = self._quote_all(tokens)
            lines.append(";".join(quoted_tokens))

        # Join with CRLF
        result = self.CANONICAL_LINE_ENDING.join(lines)
        if not result.endswith(self.CANONICAL_LINE_ENDING):
            result += self.CANONICAL_LINE_ENDING

        # Encode
        return result.encode(self.CANONICAL_ENCODING)

    def _quote_all(self, tokens: list[str]) -> list[str]:
        """Quote all tokens."""
        result: list[str] = []
        for token in tokens:
            # Remove existing quotes if present
            if token.startswith('"') and token.endswith('"'):
                value = token[1:-1].replace('""', '"')
            else:
                value = token
            # Re-quote
            escaped = value.replace('"', '""')
            result.append(f'"{escaped}"')
        return result


# =============================================================================
# Writer Factory
# =============================================================================


def get_writer(mode: WriteMode) -> Writer:
    """Get writer for specified mode."""
    if mode == WriteMode.PRESERVE:
        return PreserveWriter()
    elif mode == WriteMode.CANONICAL:
        return CanonicalWriter()
    else:
        raise ValueError(f"Unknown write mode: {mode}")


def write_file(
    plan: PatchPlan,
    parse_result: ParseResult,
    output_path: Path | None = None,
    mode: WriteMode = WriteMode.PRESERVE,
    backup_path: Path | None = None,
    atomic: bool = True,
) -> WriteResult:
    """
    Write patched file.

    Args:
        plan: Patch plan to apply
        parse_result: Original parse result
        output_path: Output path (defaults to original)
        mode: Write mode (preserve or canonical)
        backup_path: Path for backup (created before write)
        atomic: Use atomic write (temp file + rename)

    Returns:
        WriteResult with status and paths
    """
    import shutil
    import time

    start_time = time.time()

    original_path = Path(plan.file_path)
    if output_path is None:
        output_path = original_path

    # Compute old checksum
    old_checksum = plan.file_checksum

    # Create backup if requested
    if backup_path is not None:
        shutil.copy2(original_path, backup_path)

    # Get writer
    writer = get_writer(mode)
    fallback_used = False

    try:
        # Write content
        content = writer.write(plan, parse_result, output_path)
    except Exception as e:
        # Try fallback to canonical if preserve fails
        if mode == WriteMode.PRESERVE:
            fallback_used = True
            writer = CanonicalWriter()
            content = writer.write(plan, parse_result, output_path)
        else:
            return WriteResult(
                success=False,
                output_path=str(output_path),
                backup_path=str(backup_path) if backup_path else None,
                old_checksum=old_checksum,
                new_checksum="",
                mode=mode,
                error=str(e),
            )

    # Compute new checksum
    new_checksum = compute_bytes_checksum(content)

    # Write to file
    try:
        if atomic:
            # Atomic write: write to temp file, then rename
            fd, temp_path = tempfile.mkstemp(
                dir=output_path.parent,
                prefix=".datev_lint_",
                suffix=".tmp",
            )
            try:
                os.write(fd, content)
                os.close(fd)
                # Rename (atomic on most filesystems)
                os.replace(temp_path, output_path)
            except Exception:
                # Clean up temp file on failure
                with contextlib.suppress(Exception):
                    os.unlink(temp_path)
                raise
        else:
            output_path.write_bytes(content)
    except Exception as e:
        return WriteResult(
            success=False,
            output_path=str(output_path),
            backup_path=str(backup_path) if backup_path else None,
            old_checksum=old_checksum,
            new_checksum=new_checksum,
            mode=mode if not fallback_used else WriteMode.CANONICAL,
            fallback_used=fallback_used,
            error=str(e),
        )

    duration_ms = int((time.time() - start_time) * 1000)

    return WriteResult(
        success=True,
        output_path=str(output_path),
        backup_path=str(backup_path) if backup_path else None,
        old_checksum=old_checksum,
        new_checksum=new_checksum,
        mode=mode if not fallback_used else WriteMode.CANONICAL,
        fallback_used=fallback_used,
        patches_applied=len(plan.patches),
        duration_ms=duration_ms,
    )
