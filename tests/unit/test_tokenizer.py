"""Tests for CSV tokenizer."""

from datev_lint.core.parser.tokenizer import tokenize_line, tokenize_stream


class TestTokenizeLine:
    """Tests for tokenize_line function."""

    def test_simple_fields(self) -> None:
        """Test tokenizing simple semicolon-separated fields."""
        result = tokenize_line('"a";"b";"c"')
        assert result == ["a", "b", "c"]

    def test_empty_fields(self) -> None:
        """Test tokenizing with empty fields."""
        result = tokenize_line('"a";"";"c"')
        assert result == ["a", "", "c"]

    def test_unquoted_fields(self) -> None:
        """Test tokenizing unquoted fields."""
        result = tokenize_line("a;b;c")
        assert result == ["a", "b", "c"]

    def test_mixed_quoted_unquoted(self) -> None:
        """Test tokenizing mixed quoted and unquoted fields."""
        result = tokenize_line('"quoted";unquoted;"also quoted"')
        assert result == ["quoted", "unquoted", "also quoted"]

    def test_escaped_quotes(self) -> None:
        """Test tokenizing fields with escaped quotes."""
        result = tokenize_line('"contains ""quotes"""')
        assert result == ['contains "quotes"']

    def test_semicolon_in_quotes(self) -> None:
        """Test tokenizing fields containing semicolons."""
        result = tokenize_line('"a;b";"c"')
        assert result == ["a;b", "c"]


class TestTokenizeStream:
    """Tests for tokenize_stream function."""

    def test_multiple_lines(self) -> None:
        """Test tokenizing multiple lines."""
        text = '"a";"b"\n"c";"d"'
        records = list(tokenize_stream(text))
        assert len(records) == 2
        assert records[0][0] == ["a", "b"]
        assert records[1][0] == ["c", "d"]

    def test_crlf_line_endings(self) -> None:
        """Test tokenizing with CRLF line endings."""
        text = '"a";"b"\r\n"c";"d"'
        records = list(tokenize_stream(text))
        assert len(records) == 2

    def test_cr_line_endings(self) -> None:
        """Test tokenizing with CR-only line endings (DATEV standard)."""
        text = '"a";"b"\r"c";"d"'
        records = list(tokenize_stream(text))
        assert len(records) == 2

    def test_embedded_newline_in_quoted_field(self) -> None:
        """Test multi-line field with embedded newline."""
        text = '"line1\nline2";"b"'
        records = list(tokenize_stream(text))
        assert len(records) == 1
        assert records[0][0][0] == "line1\nline2"

    def test_line_numbers(self) -> None:
        """Test that line numbers are correctly tracked."""
        text = '"a"\n"b"\n"c"'
        records = list(tokenize_stream(text))
        assert len(records) == 3
        # Check start and end line numbers
        assert records[0][1] == 1  # start_line
        assert records[1][1] == 2
        assert records[2][1] == 3
        assert records[0][2] == 1  # end_line
        assert records[1][2] == 2
        assert records[2][2] == 3

    def test_line_numbers_crlf(self) -> None:
        """Test that CRLF line endings count as a single newline."""
        text = '"a"\r\n"b"\r\n"c"'
        records = list(tokenize_stream(text))
        assert [r[1] for r in records] == [1, 2, 3]
        assert [r[2] for r in records] == [1, 2, 3]

    def test_line_numbers_cr(self) -> None:
        """Test that CR-only line endings are tracked correctly."""
        text = '"a"\r"b"\r"c"'
        records = list(tokenize_stream(text))
        assert [r[1] for r in records] == [1, 2, 3]
        assert [r[2] for r in records] == [1, 2, 3]
