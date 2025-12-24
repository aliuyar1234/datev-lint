# Quickstart: Parser Core

**Feature**: 001-parser-core
**Date**: 2025-12-24

## Installation

```bash
pip install datev-lint
```

## Basic Usage

### Parse a DATEV File

```python
from datev_lint.core.parser import parse_file

# Parse a DATEV EXTF file
result = parse_file("EXTF_Buchungsstapel.csv")

# Access header information
print(f"Version: {result.header.header_version}")
print(f"Mandant: {result.header.mandantennummer}")
print(f"Zeitraum: {result.header.period_from} - {result.header.period_to}")
print(f"Encoding: {result.encoding}")

# Iterate over booking rows (streaming)
for item in result.rows:
    if isinstance(item, ParserError):
        print(f"Error in row: {item.code} - {item.message}")
    else:
        row = item
        print(f"Row {row.row_no}: Konto={row.konto}, Betrag={row.umsatz}")
```

### Handle Errors

```python
from datev_lint.core.parser import parse_file, ParserError, Severity

result = parse_file("EXTF_Buchungsstapel.csv")

# Check for fatal header errors
for error in result.header_errors:
    if error.severity == Severity.FATAL:
        print(f"FATAL: {error.code} - {error.message}")
        exit(1)

# Collect all rows and errors
rows, errors = result.materialize()

print(f"Parsed {len(rows)} rows with {len(errors)} errors")

# Filter by severity
fatal_errors = [e for e in errors if e.severity == Severity.FATAL]
warnings = [e for e in errors if e.severity == Severity.WARN]
```

### Access Raw vs Typed Values

```python
from datev_lint.core.parser import parse_file

result = parse_file("EXTF_Buchungsstapel.csv")

for row in result.rows:
    if isinstance(row, BookingRow):
        # Raw string values (for roundtrip writing)
        konto_raw = row.fields_raw["konto"]  # "0001234" - preserves leading zeros!
        betrag_raw = row.fields_raw["umsatz"]  # "1234,56" - original format

        # Typed values (for validation)
        umsatz = row.fields_typed["umsatz"]  # Decimal("1234.56")
        belegdatum = row.fields_typed["belegdatum"]  # DerivedDate object

        # Convenience properties
        print(f"Konto: {row.konto}")  # String, leading zeros preserved
        print(f"Umsatz: {row.umsatz}")  # Decimal
        print(f"Datum: {row.belegdatum.derived_date}")  # date object
```

### TTMM Date Handling

```python
from datev_lint.core.parser import derive_year, DateConfidence
from datetime import date

# Derive year from TTMM format
result = derive_year(
    ttmm="1503",  # March 15
    period_from=date(2025, 1, 1),
    period_to=date(2025, 12, 31)
)

print(f"Date: {result.derived_date}")  # 2025-03-15
print(f"Confidence: {result.confidence}")  # DateConfidence.HIGH

# Handle ambiguous dates (Dec/Jan crossover)
result = derive_year(
    ttmm="0101",  # January 1
    period_from=date(2024, 12, 1),
    period_to=date(2025, 1, 31)
)

if result.confidence == DateConfidence.AMBIGUOUS:
    print(f"Warning: {result.warning_code}")  # DVL-DATE-AMBIG-001
    print(f"Assumed year: {result.year}")  # 2025 (or 2024)
```

### Encoding Detection

```python
from datev_lint.core.parser import detect_encoding

with open("EXTF_Buchungsstapel.csv", "rb") as f:
    first_8kb = f.read(8192)

encoding = detect_encoding(first_8kb)
print(f"Detected encoding: {encoding}")  # "windows-1252" or "utf-8" or "utf-8-sig"
```

### Parse from Bytes or Stream

```python
from datev_lint.core.parser import parse_bytes, parse_stream

# From bytes
with open("EXTF_Buchungsstapel.csv", "rb") as f:
    data = f.read()

result = parse_bytes(data, filename="uploaded_file.csv")

# From stream (useful for uploads)
from io import BytesIO

stream = BytesIO(data)
result = parse_stream(stream, filename="uploaded_file.csv")
```

### Use Field Dictionary

```python
from datev_lint.core.parser import get_field_dictionary

fd = get_field_dictionary()

# Find field by column header synonym
field = fd.get_by_synonym("Soll/Haben-Kennzeichen")
if field:
    print(f"Canonical ID: {field.canonical_id}")  # "sh_kennz"
    print(f"Required: {field.required}")  # True
    print(f"Charset: {field.charset}")  # "SH"

# Get field by canonical ID
konto_field = fd.get_by_id("konto")
print(f"Max length: {konto_field.max_length}")  # 9
print(f"Fix strategies: {konto_field.fix_strategies}")  # ["pad_left", "truncate"]
```

## Streaming for Large Files

```python
from datev_lint.core.parser import parse_file
import tracemalloc

# Monitor memory usage
tracemalloc.start()

result = parse_file("large_file_1m_rows.csv")

row_count = 0
error_count = 0

# Stream through without materializing
for item in result.rows:
    if isinstance(item, ParserError):
        error_count += 1
    else:
        row_count += 1

current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"Processed {row_count} rows, {error_count} errors")
print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")  # Should be < 1200 MB for 1M rows
```

## Common Patterns

### Validate Before Processing

```python
from datev_lint.core.parser import parse_file, Severity

def validate_file(path: str) -> bool:
    result = parse_file(path)

    # Check header
    if result.header.format_category != 21:
        print("Not a Buchungsstapel!")
        return False

    # Check for fatal errors
    fatal_errors = [e for e in result.header_errors if e.severity == Severity.FATAL]
    if fatal_errors:
        for e in fatal_errors:
            print(f"FATAL: {e.message}")
        return False

    return True
```

### Extract Summary Statistics

```python
from datev_lint.core.parser import parse_file
from decimal import Decimal
from collections import Counter

result = parse_file("EXTF_Buchungsstapel.csv")

total_soll = Decimal("0")
total_haben = Decimal("0")
konten = Counter()

for item in result.rows:
    if isinstance(item, BookingRow):
        sh = item.fields_raw.get("sh_kennz", "")
        umsatz = item.umsatz or Decimal("0")

        if sh == "S":
            total_soll += umsatz
        elif sh == "H":
            total_haben += umsatz

        if item.konto:
            konten[item.konto] += 1

print(f"Summe Soll: {total_soll}")
print(f"Summe Haben: {total_haben}")
print(f"Top 5 Konten: {konten.most_common(5)}")
```

## Error Handling Best Practices

```python
from datev_lint.core.parser import parse_file, ParserError, Severity
from pathlib import Path

def safe_parse(path: str) -> tuple[list, list]:
    """Parse file with comprehensive error handling."""
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if file_path.stat().st_size == 0:
        raise ValueError("File is empty")

    result = parse_file(path)

    # Abort on fatal header errors
    for error in result.header_errors:
        if error.severity == Severity.FATAL:
            raise RuntimeError(f"Cannot parse file: {error.message}")

    # Collect rows and errors
    rows, errors = result.materialize()

    # Log warnings
    for error in errors:
        if error.severity == Severity.WARN:
            print(f"Warning at row {error.location.get('line_no')}: {error.message}")

    return rows, errors
```

## Next Steps

After parsing, you can:

1. **Validate** with Rule Engine (002-rule-engine)
2. **Fix** issues with Fix Engine (003-fix-engine)
3. **Output** results via CLI (004-cli-outputs)

```python
# Example: Parse → Validate → Report
from datev_lint.core.parser import parse_file
from datev_lint.core.rules import validate
from datev_lint.core.reports import to_json

result = parse_file("EXTF_Buchungsstapel.csv")
findings = validate(result, profile="de.skr03.default")
report = to_json(findings)
print(report)
```
