# Research: Parser Core

**Feature**: 001-parser-core
**Date**: 2025-12-24
**Status**: Complete

## Research Questions

### RQ-1: Encoding Detection Library

**Question**: Welche Library für automatische Encoding-Detection verwenden?

**Decision**: `charset-normalizer`

**Rationale**:
- Moderne Alternative zu `chardet` (schneller, aktiv maintained)
- Gute Erkennung von Windows-1252 vs UTF-8
- MIT License, keine Dependencies
- Performance: ~10x schneller als chardet

**Alternatives Considered**:
| Library | Pro | Contra |
|---------|-----|--------|
| `chardet` | Weit verbreitet, stabil | Langsam, weniger aktiv maintained |
| `cchardet` | C-basiert, schnell | Kompilierung nötig, weniger portable |
| Manual BOM Check | Keine Dependency | Nur BOM-Detection, kein Fallback |

**Implementation Notes**:
```python
from charset_normalizer import from_bytes

def detect_encoding(data: bytes) -> str:
    # 1. Check BOM first (deterministic)
    if data.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'

    # 2. Try charset_normalizer
    result = from_bytes(data).best()
    if result:
        return result.encoding

    # 3. Fallback to Windows-1252 (DATEV default)
    return 'windows-1252'
```

---

### RQ-2: CSV Parsing Strategy

**Question**: Standard `csv` Module oder Custom Parser für DATEV-spezifisches CSV?

**Decision**: Custom Streaming Tokenizer mit State Machine

**Rationale**:
- Standard `csv` Module unterstützt keine Embedded CR/LF korrekt
- DATEV verwendet CR als Record-Ende, LF kann in Quotes vorkommen
- Streaming für 1M+ Zeilen ohne OOM erforderlich
- Roundtrip-Fähigkeit erfordert Raw-Token-Erhalt

**Alternatives Considered**:
| Approach | Pro | Contra |
|----------|-----|--------|
| `csv.reader` | Einfach, Standard | Kein Streaming, CR/LF Probleme |
| `pandas.read_csv` | Schnell, viele Features | Hoher Memory-Footprint, Overkill |
| `polars.read_csv` | Sehr schnell | Keine Kontrolle über Quoting Edge Cases |
| Custom Tokenizer | Volle Kontrolle, Streaming | Mehr Code, mehr Tests |

**Implementation Notes**:
```python
class TokenizerState(Enum):
    FIELD_START = auto()
    IN_UNQUOTED = auto()
    IN_QUOTED = auto()
    QUOTE_IN_QUOTED = auto()  # After " inside quoted field

def tokenize_stream(file: BinaryIO, encoding: str) -> Iterator[tuple[int, list[str]]]:
    """Yields (line_no, tokens) for each record."""
    # State machine handles:
    # - Semicolon as delimiter
    # - Double-quote escaping ("")
    # - CR as record terminator
    # - LF inside quotes (preserved)
```

---

### RQ-3: Data Model Library

**Question**: Pydantic, dataclasses, oder attrs für typisierte Models?

**Decision**: `pydantic` v2

**Rationale**:
- Validation + Serialization in einem
- Gute IDE-Unterstützung (Type Hints)
- `frozen=True` für Immutability
- JSON-Export für Findings built-in
- v2 ist deutlich schneller als v1

**Alternatives Considered**:
| Library | Pro | Contra |
|---------|-----|--------|
| `dataclasses` | Standard Library, einfach | Keine Validation |
| `attrs` | Schnell, flexibel | Extra Dependency ohne Mehrwert |
| `msgspec` | Extrem schnell | Weniger verbreitet, weniger Features |

**Implementation Notes**:
```python
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date

class DatevHeader(BaseModel, frozen=True):
    kennzeichen: str = Field(pattern=r'^EXTF$')
    header_version: int = Field(ge=500, le=999)
    format_category: int
    format_name: str
    format_version: int
    beraternummer: str  # NEVER int!
    mandantennummer: str  # NEVER int!
    fiscal_year_start: date | None = None
    period_from: date | None = None
    period_to: date | None = None
    account_length: int | None = None
    raw_tokens: list[str]  # For roundtrip
```

---

### RQ-4: TTMM Date Derivation Algorithm

**Question**: Wie deterministisch das Jahr für TTMM-Daten ableiten?

**Decision**: Dreistufiger Algorithmus mit Konfidenz-Levels

**Rationale**:
- Spec v2.1 definiert den Algorithmus explizit
- Konfidenz-Levels ermöglichen differenzierte Warnings
- Deterministisch = gleicher Input → gleiches Output

**Algorithm**:
```
1. IF period_from AND period_to available:
   - Try both years (period_from.year, period_to.year)
   - Check which puts date in range
   - If exactly one: HIGH confidence
   - If both valid (Dec/Jan crossover): AMBIGUOUS + Warning
   - If none valid: FAILED + Error

2. ELSE IF fiscal_year_start available:
   - Month >= fiscal_year_start.month → fiscal_year_start.year
   - Month < fiscal_year_start.month → fiscal_year_start.year + 1
   - MEDIUM confidence

3. ELSE:
   - Cannot derive year
   - UNKNOWN + Warning
```

**Edge Cases**:
| Case | Input | Output |
|------|-------|--------|
| Normal | TTMM=1503, period=2025-01-01 to 2025-12-31 | 2025-03-15, HIGH |
| Cross-year | TTMM=0101, period=2024-12-01 to 2025-01-31 | 2025-01-01, AMBIGUOUS |
| Out of range | TTMM=1507, period=2025-01-01 to 2025-03-31 | None, FAILED |
| Fiscal year | TTMM=0115, fiscal_start=2024-07-01 | 2025-01-15, MEDIUM |

---

### RQ-5: Streaming vs Buffered Parsing

**Question**: Wie Streaming für große Dateien implementieren?

**Decision**: Generator-basiertes Streaming mit optionalem Buffering

**Rationale**:
- 1M Zeilen × ~500 Bytes = 500MB Raw
- Mit Parsed Objects: ~1-1.5GB möglich
- Streaming hält Memory konstant
- Optional: Buffer für Cross-Row-Checks

**Implementation**:
```python
def parse_file(path: Path) -> ParseResult:
    """Returns streaming iterator + header."""
    with open(path, 'rb') as f:
        encoding = detect_encoding(f.read(8192))
        f.seek(0)

        tokenizer = tokenize_stream(f, encoding)

        # Line 1: Header (consumed immediately)
        _, header_tokens = next(tokenizer)
        header = parse_header(header_tokens)

        # Line 2: Column headers (consumed immediately)
        _, column_tokens = next(tokenizer)
        columns = map_columns(column_tokens)

        # Line 3+: Booking rows (streamed)
        def row_iterator():
            for line_no, tokens in tokenizer:
                yield parse_row(line_no, tokens, columns, header)

        return ParseResult(
            header=header,
            columns=columns,
            rows=row_iterator(),  # Lazy!
            encoding=encoding
        )
```

---

### RQ-6: Field Dictionary Structure

**Question**: Wie das Field Dictionary als Single Source of Truth strukturieren?

**Decision**: YAML-Datei + Python-Loader mit Validation

**Rationale**:
- YAML ist lesbar und editierbar
- Kann für Docs, Parser, Rules verwendet werden
- Python-Loader validiert beim Start
- Synonyme für unterschiedliche Exporter

**Structure**:
```yaml
# field_dictionary.yaml
fields:
  umsatz:
    canonical_id: umsatz
    synonyms: ["Umsatz", "Umsatz (ohne Soll/Haben-Kz)"]
    required: true
    type: decimal
    max_length: null
    charset: "0-9,"
    fix_strategies: [normalize_decimal]

  konto:
    canonical_id: konto
    synonyms: ["Konto", "Kontonummer"]
    required: true
    type: string  # NEVER int!
    max_length: 9  # Depends on header.account_length
    charset: "0-9"
    fix_strategies: [pad_left, truncate]

  belegdatum:
    canonical_id: belegdatum
    synonyms: ["Belegdatum", "Beleg-Datum"]
    required: true
    type: ttmm
    max_length: 4
    charset: "0-9"
    fix_strategies: [derive_year]
```

---

### RQ-7: Error Handling Strategy

**Question**: Wie Parser-Errors strukturiert zurückgeben?

**Decision**: Typed Error Objects mit Error Codes aus Error Taxonomy

**Rationale**:
- Einheitliches Error-Format für Parser und Rules
- Error Codes (DVL-XXX-NNN) ermöglichen Dokumentation
- Severity Levels (FATAL, ERROR, WARN) steuern Abort-Verhalten

**Implementation**:
```python
from enum import Enum
from pydantic import BaseModel

class Severity(Enum):
    FATAL = "fatal"   # Cannot continue parsing
    ERROR = "error"   # Likely import failure
    WARN = "warn"     # Risky, might cause issues
    INFO = "info"     # Informational

class ParserError(BaseModel, frozen=True):
    code: str  # e.g., "DVL-ENC-001"
    severity: Severity
    message: str
    location: dict  # {file, line_no, column, field}
    context: dict  # {raw_value, expected, ...}

# Parser yields errors as it streams
def parse_rows(...) -> Iterator[BookingRow | ParserError]:
    ...
```

---

## Performance Considerations

### Memory Targets

| File Size | Target Memory | Strategy |
|-----------|---------------|----------|
| 10k rows | < 50 MB | Full materialization OK |
| 50k rows | < 200 MB | Streaming recommended |
| 100k rows | < 400 MB | Streaming required |
| 1M rows | < 1.2 GB | Streaming + partial materialization |

### Optimization Techniques

1. **Lazy Tokenization**: Don't parse fields until needed
2. **String Interning**: Reuse common strings (field names)
3. **Slots on Models**: Reduce memory overhead
4. **Generator Chains**: Avoid intermediate lists
5. **Buffer Pooling**: Reuse byte buffers

### Benchmark Targets

```python
# tests/benchmark/test_performance.py

def test_parse_50k_under_1s(benchmark, fixture_50k):
    result = benchmark(lambda: list(parse_file(fixture_50k).rows))
    assert benchmark.stats['mean'] < 1.0

def test_parse_1m_memory(fixture_1m):
    import tracemalloc
    tracemalloc.start()

    for row in parse_file(fixture_1m).rows:
        pass  # Stream through

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert peak < 1.2 * 1024 * 1024 * 1024  # 1.2 GB
```

---

## Dependencies Summary

### Production Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "pydantic>=2.0",
    "charset-normalizer>=3.0",
    "pyyaml>=6.0",
]
```

### Development Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-benchmark>=4.0",
    "pytest-cov>=4.0",
]
```

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Which encoding library? | charset-normalizer |
| Custom vs standard CSV? | Custom tokenizer (streaming + DATEV quirks) |
| Data model library? | pydantic v2 |
| TTMM algorithm? | 3-tier with confidence levels |
| Field dictionary format? | YAML with Python loader |

---

## Next Steps

1. Create `data-model.md` with Pydantic models
2. Create `contracts/` with Python API definitions
3. Create `quickstart.md` with usage examples
4. Generate `tasks.md` via `/speckit.tasks`
