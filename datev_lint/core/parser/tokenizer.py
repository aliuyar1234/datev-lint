"""
CSV tokenizer for DATEV files.

DATEV files use a specific CSV dialect:
- Delimiter: semicolon (;)
- Quote character: double quote (")
- Escape: doubled quotes ("")
- Line terminator: CR (\r), with LF allowed inside quoted fields

This module implements a streaming state-machine tokenizer that handles
all these edge cases correctly.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from .models import Dialect

if TYPE_CHECKING:
    from collections.abc import Iterator


class TokenizerState(Enum):
    """State of the tokenizer state machine."""

    FIELD_START = auto()  # At start of a field
    IN_UNQUOTED = auto()  # Inside an unquoted field
    IN_QUOTED = auto()  # Inside a quoted field
    QUOTE_IN_QUOTED = auto()  # Just saw a quote inside a quoted field


class TokenizerError(Exception):
    """Error during tokenization."""

    def __init__(self, message: str, line: int, column: int) -> None:
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Line {line}, column {column}: {message}")


def tokenize_line(
    line: str,
    dialect: Dialect | None = None,
) -> list[str]:
    """
    Tokenize a single line into fields.

    Note: This function assumes the line does NOT contain embedded newlines.
    For multi-line records, use tokenize_stream().

    Args:
        line: The line to tokenize (without line terminator)
        dialect: CSV dialect (defaults to DATEV dialect)

    Returns:
        List of field values (unquoted and unescaped)
    """
    if dialect is None:
        dialect = Dialect()

    delimiter = dialect.delimiter
    quotechar = dialect.quotechar

    fields: list[str] = []
    field_buffer: list[str] = []
    state = TokenizerState.FIELD_START
    i = 0

    while i < len(line):
        char = line[i]

        if state == TokenizerState.FIELD_START:
            if char == quotechar:
                state = TokenizerState.IN_QUOTED
            elif char == delimiter:
                fields.append("")
            else:
                field_buffer.append(char)
                state = TokenizerState.IN_UNQUOTED

        elif state == TokenizerState.IN_UNQUOTED:
            if char == delimiter:
                fields.append("".join(field_buffer))
                field_buffer = []
                state = TokenizerState.FIELD_START
            else:
                field_buffer.append(char)

        elif state == TokenizerState.IN_QUOTED:
            if char == quotechar:
                state = TokenizerState.QUOTE_IN_QUOTED
            else:
                field_buffer.append(char)

        elif state == TokenizerState.QUOTE_IN_QUOTED:
            if char == quotechar:
                # Escaped quote
                field_buffer.append(quotechar)
                state = TokenizerState.IN_QUOTED
            elif char == delimiter:
                fields.append("".join(field_buffer))
                field_buffer = []
                state = TokenizerState.FIELD_START
            else:
                # Quote ended, but there's more content
                field_buffer.append(char)
                state = TokenizerState.IN_UNQUOTED

        i += 1

    # Handle final field
    if state == TokenizerState.IN_QUOTED:
        # Unclosed quote - still capture the field
        fields.append("".join(field_buffer))
    elif state == TokenizerState.QUOTE_IN_QUOTED:
        fields.append("".join(field_buffer))
    else:
        fields.append("".join(field_buffer))

    return fields


def tokenize_stream(
    text: str,
    dialect: Dialect | None = None,
) -> Iterator[tuple[list[str], int, int]]:
    """
    Tokenize a text stream into records (rows).

    Handles multi-line records where LF appears inside quoted fields.
    Supports both CR (DATEV standard) and LF/CRLF line endings.

    Args:
        text: The full text to tokenize
        dialect: CSV dialect (defaults to DATEV dialect)

    Yields:
        Tuples of (fields, start_line, end_line)
        start_line and end_line are 1-indexed line numbers
    """
    if dialect is None:
        dialect = Dialect()

    delimiter = dialect.delimiter
    quotechar = dialect.quotechar

    fields: list[str] = []
    field_buffer: list[str] = []
    state = TokenizerState.FIELD_START

    line_no = 1
    record_start_line = 1

    def is_line_terminator(c: str, next_c: str | None) -> bool:
        """Check if current char is a line terminator."""
        # Accept CR, LF, or CRLF as line terminators
        return c in ("\r", "\n")

    i = 0
    while i < len(text):
        char = text[i]
        next_char = text[i + 1] if i + 1 < len(text) else None

        # Check for line terminator
        is_eol = is_line_terminator(char, next_char) and state != TokenizerState.IN_QUOTED

        # Track line numbers on LF
        if char == "\n":
            line_no += 1

        if state == TokenizerState.FIELD_START:
            if char == quotechar:
                state = TokenizerState.IN_QUOTED
            elif char == delimiter:
                fields.append("")
            elif is_eol:
                # End of record
                fields.append("".join(field_buffer))
                if fields and any(f for f in fields):
                    yield fields, record_start_line, line_no
                fields = []
                field_buffer = []
                record_start_line = line_no if char == "\n" else line_no
                # Skip LF if we just saw CR
                if char == "\r" and next_char == "\n":
                    i += 1
                    line_no += 1
            else:
                field_buffer.append(char)
                state = TokenizerState.IN_UNQUOTED

        elif state == TokenizerState.IN_UNQUOTED:
            if char == delimiter:
                fields.append("".join(field_buffer))
                field_buffer = []
                state = TokenizerState.FIELD_START
            elif is_eol:
                # End of record
                fields.append("".join(field_buffer))
                if fields and any(f for f in fields):
                    yield fields, record_start_line, line_no
                fields = []
                field_buffer = []
                state = TokenizerState.FIELD_START
                record_start_line = line_no if char == "\n" else line_no
                # Skip LF if we just saw CR
                if char == "\r" and next_char == "\n":
                    i += 1
                    line_no += 1
            else:
                field_buffer.append(char)

        elif state == TokenizerState.IN_QUOTED:
            if char == quotechar:
                state = TokenizerState.QUOTE_IN_QUOTED
            else:
                # Include everything, including LF (multi-line field)
                field_buffer.append(char)

        elif state == TokenizerState.QUOTE_IN_QUOTED:
            if char == quotechar:
                # Escaped quote
                field_buffer.append(quotechar)
                state = TokenizerState.IN_QUOTED
            elif char == delimiter:
                fields.append("".join(field_buffer))
                field_buffer = []
                state = TokenizerState.FIELD_START
            elif is_eol:
                # End of record
                fields.append("".join(field_buffer))
                if fields and any(f for f in fields):
                    yield fields, record_start_line, line_no
                fields = []
                field_buffer = []
                state = TokenizerState.FIELD_START
                record_start_line = line_no if char == "\n" else line_no
                # Skip LF if we just saw CR
                if char == "\r" and next_char == "\n":
                    i += 1
                    line_no += 1
            else:
                # Content after closing quote
                field_buffer.append(char)
                state = TokenizerState.IN_UNQUOTED

        i += 1

    # Handle final record if not empty
    if field_buffer or fields:
        fields.append("".join(field_buffer))
        if any(f for f in fields):  # Only yield if there's actual content
            yield fields, record_start_line, line_no


def tokenize_bytes(
    data: bytes,
    encoding: str,
    dialect: Dialect | None = None,
) -> Iterator[tuple[list[str], int, int]]:
    """
    Tokenize bytes into records.

    Args:
        data: Raw file content
        encoding: File encoding
        dialect: CSV dialect

    Yields:
        Tuples of (fields, start_line, end_line)
    """
    text = data.decode(encoding, errors="replace")
    yield from tokenize_stream(text, dialect)
