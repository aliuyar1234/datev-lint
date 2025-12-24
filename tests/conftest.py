"""
Pytest configuration and fixtures for datev-lint tests.

Provides fixtures for:
- Golden test files (DATEV samples)
- Large file generation for benchmarks
- Common test utilities
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

# =============================================================================
# Path Fixtures
# =============================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return FIXTURES_DIR


@pytest.fixture
def golden_dir() -> Path:
    """Return the golden files directory path."""
    return GOLDEN_DIR


# =============================================================================
# Golden File Fixtures
# =============================================================================


@pytest.fixture
def valid_minimal_700(golden_dir: Path) -> Path:
    """Minimal valid EXTF file with 10 rows (version 700)."""
    return golden_dir / "valid_minimal_700.csv"


@pytest.fixture
def encoding_utf8_bom(golden_dir: Path) -> Path:
    """UTF-8 with BOM encoded file."""
    return golden_dir / "encoding_utf8_bom.csv"


@pytest.fixture
def encoding_windows1252(golden_dir: Path) -> Path:
    """Windows-1252 encoded file with Umlaute."""
    return golden_dir / "encoding_windows1252.csv"


@pytest.fixture
def broken_quotes(golden_dir: Path) -> Path:
    """File with unbalanced quotes for error testing."""
    return golden_dir / "broken_quotes.csv"


@pytest.fixture
def embedded_newlines(golden_dir: Path) -> Path:
    """File with LF inside quoted fields."""
    return golden_dir / "embedded_newlines.csv"


@pytest.fixture
def leading_zero_konto(golden_dir: Path) -> Path:
    """File with account numbers like '0001234'."""
    return golden_dir / "leading_zero_konto.csv"


# =============================================================================
# TTMM Test Fixtures
# =============================================================================


@pytest.fixture
def ttmm_cross_year(golden_dir: Path) -> Path:
    """File with dates spanning Dec/Jan boundary."""
    return golden_dir / "ttmm_cross_year.csv"


@pytest.fixture
def ttmm_ambiguous(golden_dir: Path) -> Path:
    """File with ambiguous year scenarios."""
    return golden_dir / "ttmm_ambiguous.csv"


# =============================================================================
# Large File Fixtures (for benchmarks)
# =============================================================================


@pytest.fixture(scope="session")
def large_file_50k(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """Generate a 50k row DATEV file for performance testing."""
    tmp_dir = tmp_path_factory.mktemp("benchmark")
    file_path = tmp_dir / "large_50k.csv"

    # Generate file content
    _generate_large_datev_file(file_path, num_rows=50_000)

    yield file_path


@pytest.fixture(scope="session")
def large_file_100k(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """Generate a 100k row DATEV file for performance testing."""
    tmp_dir = tmp_path_factory.mktemp("benchmark")
    file_path = tmp_dir / "large_100k.csv"

    _generate_large_datev_file(file_path, num_rows=100_000)

    yield file_path


def _generate_large_datev_file(path: Path, num_rows: int) -> None:
    """
    Generate a large DATEV file for benchmark testing.

    Creates a valid EXTF file with the specified number of booking rows.
    """
    # Header line 1 (metadata)
    header1 = (
        '"EXTF";700;21;"Buchungsstapel";13;'
        '20250101000000000;;;;;'
        '"12345";"67890";'  # Beraternummer, Mandantennummer
        '20250101;4;'  # WJ-Beginn, Sachkontenlänge
        '20250101;20251231;'  # Zeitraum
        '"Test Benchmark";;'  # Bezeichnung, Diktatkürzel
        '"";"";;'  # Buchungstyp, Rechnungslegung
        ';"";"EUR";'  # reserviert, WKZ
        ';;;;;'  # Derivat, Kost1, Kost2, Herkunft
        ';0'  # Festschreibung
    )

    # Header line 2 (column names)
    header2 = (
        '"Umsatz";"S/H";"WKZ";"Kurs";"Basis-Umsatz";'
        '"WKZ Basis-Umsatz";"Konto";"Gegenkonto";"BU-Schlüssel";'
        '"Belegdatum";"Belegfeld 1";"Belegfeld 2";'
        '"Skonto";"Buchungstext";"Postensperre";"Diverses Konto"'
    )

    lines = [header1, header2]

    # Generate booking rows
    for i in range(1, num_rows + 1):
        amount = f"{100 + (i % 1000)},{i % 100:02d}"
        konto = f"{1000 + (i % 9000):04d}"
        gegenkonto = f"{8000 + (i % 1000):04d}"
        belegfeld1 = f"RE{i:06d}"
        tag = (i % 28) + 1
        monat = (i % 12) + 1
        belegdatum = f"{tag:02d}{monat:02d}"

        row = (
            f'"{amount}";"S";"EUR";"";"";"";'
            f'"{konto}";"{gegenkonto}";"";'
            f'"{belegdatum}";"{belegfeld1}";"";'
            f'"";\"Buchung {i}\";"";"";'
        )
        lines.append(row)

    # Write with Windows line endings
    content = "\r\n".join(lines) + "\r\n"
    path.write_bytes(content.encode("windows-1252"))


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def sample_extf_header() -> str:
    """Return a sample EXTF header line for testing."""
    return (
        '"EXTF";700;21;"Buchungsstapel";13;'
        '20250101120000000;;;;;'
        '"00001";"00002";'
        '20250101;4;'
        '20250101;20251231;'
        '"Test";;"";"";;"";"";"EUR";;;;;;;0'
    )


@pytest.fixture
def sample_column_header() -> str:
    """Return a sample column header line for testing."""
    return (
        '"Umsatz";"S/H";"WKZ";"Kurs";"Basis-Umsatz";'
        '"WKZ Basis-Umsatz";"Konto";"Gegenkonto";"BU-Schlüssel";'
        '"Belegdatum";"Belegfeld 1";"Belegfeld 2";'
        '"Skonto";"Buchungstext"'
    )
