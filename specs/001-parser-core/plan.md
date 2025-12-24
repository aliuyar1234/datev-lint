# Implementation Plan: Parser Core

**Branch**: `001-parser-core` | **Date**: 2025-12-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-parser-core/spec.md`

## Summary

Implementierung des Parser-Layers für DATEV-Exportdateien (EXTF-Format). Der Parser ist das Fundament des gesamten datev-lint Tools und muss:

1. **Encoding automatisch erkennen** (UTF-8 BOM, UTF-8, Windows-1252)
2. **DATEV-spezifisches CSV parsen** (Semikolon-Delimiter, Quoted Fields, Embedded Newlines)
3. **Header-Zeile strukturiert auslesen** (Version, Kategorie, Zeitraum, Mandant)
4. **Buchungszeilen typsicher konvertieren** (Konten als String, Beträge als Decimal)
5. **TTMM-Datum Jahr ableiten** mit dokumentiertem deterministischen Algorithmus
6. **Streaming-fähig sein** für Dateien bis 1M Zeilen

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `charset-normalizer` - Encoding Detection
- `pydantic` - Typed Data Models
- Standard Library: `csv`, `io`, `hashlib`, `decimal`

**Storage**: N/A (Dateisystem-Input, In-Memory-Processing)
**Testing**: pytest + pytest-benchmark (Performance Tests)
**Target Platform**: Windows, Linux, macOS (CLI)
**Project Type**: Single project (Library-first)
**Performance Goals**:
- Parse 50k Zeilen ≤ 1s
- Parse 1M Zeilen mit ≤ 1.2GB Memory Peak
- Throughput ≥ 50k Zeilen/s

**Constraints**:
- Streaming-fähig (Iterator-API)
- Keine Leading-Zero-Verluste bei Kontonummern
- Roundtrip-fähig (Raw-Tokens erhalten)

**Scale/Scope**: Dateien von 10 Zeilen bis 1M Zeilen

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status |
|-----------|-------------|--------|
| **I. Library-First** | Parser als eigenständige Library in `datev_lint/core/parser/` | ✅ Planned |
| **II. Parser Robustness** | Streaming, CSV Edge Cases, Encoding Detection | ✅ Core Feature |
| **III. Type Safety** | Konto/Gegenkonto als String, nie int | ✅ Explicit in Design |
| **IV. Golden File Testing** | Golden Files für alle Parser-Funktionen | ✅ Planned |
| **V. Performance Gates** | 50k rows ≤ 1s, 1M rows ≤ 1.2GB | ✅ Benchmarks in Tests |
| **VI. Audit & Versioning** | Parser-Version in Output | ✅ Planned |
| **VII. Privacy** | Keine Datenübertragung im Parser | ✅ N/A für Parser |

**DATEV Constraints Addressed**:
- ✅ Semicolon delimiter
- ✅ TTMM date format with year derivation
- ✅ Decimal comma (`,`) handling
- ✅ CR line ending (LF in quotes)
- ✅ Windows-1252 default encoding

**Gate Status**: ✅ PASSED - No violations

## Project Structure

### Documentation (this feature)

```text
specs/001-parser-core/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (Python API)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
datev_lint/
├── __init__.py
├── core/
│   ├── __init__.py
│   └── parser/
│       ├── __init__.py
│       ├── detector.py      # Layer 0: Format & Encoding Detection
│       ├── encoding.py      # Layer 1: Encoding Handling
│       ├── tokenizer.py     # Layer 2: CSV Tokenizer (Streaming)
│       ├── header.py        # Layer 3: DATEV Header Parser
│       ├── columns.py       # Layer 4: Column Header Mapping
│       ├── rows.py          # Layer 5: Row Parser + Type Conversion
│       ├── dates.py         # TTMM Date Year Derivation
│       ├── models.py        # Pydantic Data Models
│       ├── errors.py        # Parser Error Types
│       └── field_dict.py    # Field Dictionary (Single Source of Truth)

tests/
├── conftest.py
├── fixtures/
│   └── golden/
│       ├── valid_minimal_700.csv
│       ├── valid_50k_rows.csv
│       ├── encoding_utf8_bom.csv
│       ├── encoding_windows1252.csv
│       ├── broken_quotes.csv
│       ├── embedded_newlines.csv
│       ├── leading_zero_konto.csv
│       ├── ttmm_cross_year.csv
│       └── ttmm_ambiguous.csv
├── unit/
│   ├── test_detector.py
│   ├── test_encoding.py
│   ├── test_tokenizer.py
│   ├── test_header.py
│   ├── test_columns.py
│   ├── test_rows.py
│   └── test_dates.py
├── integration/
│   └── test_parser_e2e.py
└── benchmark/
    └── test_performance.py
```

**Structure Decision**: Library-first single project. Parser lives in `datev_lint/core/parser/` as independent module. CLI will import from core.

## Complexity Tracking

> No Constitution violations - no complexity justification needed.
