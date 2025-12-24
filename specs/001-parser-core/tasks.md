# Tasks: Parser Core

**Input**: Design documents from `/specs/001-parser-core/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Golden file tests included as per Constitution Principle IV.

**Organization**: Tasks grouped by user story. US1-US5 (all P1) form the Core Parsing MVP. US6-US7 (P2) are enhancements.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US7)
- Include exact file paths in descriptions

## Path Conventions

```text
datev_lint/
├── __init__.py
├── core/
│   └── parser/          # All parser modules
tests/
├── fixtures/golden/     # Golden test files
├── unit/                # Unit tests
├── integration/         # Integration tests
└── benchmark/           # Performance tests
```

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure: `datev_lint/`, `datev_lint/core/`, `datev_lint/core/parser/` directories
- [ ] T002 Create `pyproject.toml` with Python 3.11+, pydantic>=2.0, charset-normalizer>=3.0, pyyaml>=6.0
- [ ] T003 [P] Create `datev_lint/__init__.py` with version string
- [ ] T004 [P] Create `datev_lint/core/__init__.py`
- [ ] T005 [P] Create `datev_lint/core/parser/__init__.py` with public API exports
- [ ] T006 [P] Create `tests/conftest.py` with pytest fixtures for golden files
- [ ] T007 [P] Configure `ruff` for linting in `pyproject.toml`
- [ ] T008 [P] Configure `mypy` for type checking in `pyproject.toml`

**Checkpoint**: Project structure ready, dependencies installable with `pip install -e .`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and errors that ALL parser components depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 Create Severity enum and Location model in `datev_lint/core/parser/errors.py`
- [ ] T010 Create ParserError model with factory methods in `datev_lint/core/parser/errors.py`
- [ ] T011 [P] Create DetectedFormat enum in `datev_lint/core/parser/models.py`
- [ ] T012 [P] Create Dialect model in `datev_lint/core/parser/models.py`
- [ ] T013 [P] Create DateConfidence enum in `datev_lint/core/parser/models.py`
- [ ] T014 [P] Create DerivedDate model in `datev_lint/core/parser/models.py`
- [ ] T015 Create DatevHeader model (with string types for beraternummer/mandantennummer!) in `datev_lint/core/parser/models.py`
- [ ] T016 Create ColumnMapping and ColumnMappings models in `datev_lint/core/parser/models.py`
- [ ] T017 Create BookingRow model (with fields_raw as strings!) in `datev_lint/core/parser/models.py`
- [ ] T018 Create ParseResult model with streaming row factory in `datev_lint/core/parser/models.py`
- [ ] T019 Create FieldDefinition and FieldDictionary models in `datev_lint/core/parser/field_dict.py`
- [ ] T020 Create `field_dictionary.yaml` with Buchungsstapel fields in `datev_lint/core/parser/field_dictionary.yaml`
- [ ] T021 Implement YAML loader for field dictionary in `datev_lint/core/parser/field_dict.py`

**Checkpoint**: All models defined, field dictionary loadable

---

## Phase 3: Core Parsing - US1-US5 (Priority: P1) 🎯 MVP

**Goal**: Parse valid DATEV files with encoding detection, header parsing, CSV tokenization, and row conversion

**Independent Test**: `parse_file("valid_minimal_700.csv")` returns ParseResult with header and rows

### Golden Files for Core Parsing

- [ ] T022 [P] Create `tests/fixtures/golden/valid_minimal_700.csv` - minimal valid EXTF with 10 rows
- [ ] T023 [P] Create `tests/fixtures/golden/encoding_utf8_bom.csv` - UTF-8 with BOM
- [ ] T024 [P] Create `tests/fixtures/golden/encoding_windows1252.csv` - Windows-1252 with Umlaute
- [ ] T025 [P] Create `tests/fixtures/golden/broken_quotes.csv` - unbalanced quotes for error testing
- [ ] T026 [P] Create `tests/fixtures/golden/embedded_newlines.csv` - LF inside quoted fields
- [ ] T027 [P] Create `tests/fixtures/golden/leading_zero_konto.csv` - accounts like "0001234"

### Tests for Core Parsing

- [ ] T028 [P] [US2] Create `tests/unit/test_encoding.py` with BOM detection and fallback tests
- [ ] T029 [P] [US4] Create `tests/unit/test_tokenizer.py` with quote handling tests
- [ ] T030 [P] [US3] Create `tests/unit/test_header.py` with header parsing tests
- [ ] T031 [P] [US5] Create `tests/unit/test_rows.py` with type safety tests (leading zeros!)
- [ ] T032 [P] [US1] Create `tests/integration/test_parser_e2e.py` with end-to-end parsing tests

### Implementation for Core Parsing

- [ ] T033 [US2] Implement `detect_encoding()` in `datev_lint/core/parser/encoding.py`
- [ ] T034 [US2] Implement `detect_format()` in `datev_lint/core/parser/detector.py`
- [ ] T035 [US4] Implement TokenizerState enum in `datev_lint/core/parser/tokenizer.py`
- [ ] T036 [US4] Implement `tokenize_line()` state machine in `datev_lint/core/parser/tokenizer.py`
- [ ] T037 [US4] Implement `tokenize_stream()` generator in `datev_lint/core/parser/tokenizer.py`
- [ ] T038 [US3] Implement `parse_header()` in `datev_lint/core/parser/header.py`
- [ ] T039 [US3] Implement date parsing helpers (period_from, period_to) in `datev_lint/core/parser/header.py`
- [ ] T040 [US1] Implement `map_columns()` in `datev_lint/core/parser/columns.py`
- [ ] T041 [US5] Implement `parse_row()` with type conversion in `datev_lint/core/parser/rows.py`
- [ ] T042 [US5] Implement decimal parsing (comma → Decimal) in `datev_lint/core/parser/rows.py`
- [ ] T043 [US5] Implement checksum calculation in `datev_lint/core/parser/rows.py`
- [ ] T044 [US1] Implement `parse_file()` main entry point in `datev_lint/core/parser/__init__.py`
- [ ] T045 [US1] Implement `parse_bytes()` and `parse_stream()` in `datev_lint/core/parser/__init__.py`

**Checkpoint**: Core parsing works - `parse_file()` returns structured data for valid files

---

## Phase 4: TTMM Date Year Derivation - US6 (Priority: P2)

**Goal**: Derive year for TTMM dates deterministically with confidence levels

**Independent Test**: `derive_year("1503", period_from=date(2025,1,1), period_to=date(2025,12,31))` returns year=2025, confidence=HIGH

### Golden Files for TTMM

- [ ] T046 [P] Create `tests/fixtures/golden/ttmm_cross_year.csv` - dates spanning Dec/Jan
- [ ] T047 [P] Create `tests/fixtures/golden/ttmm_ambiguous.csv` - ambiguous year scenarios

### Tests for TTMM

- [ ] T048 [P] [US6] Create `tests/unit/test_dates.py` with all confidence level tests
- [ ] T049 [P] [US6] Add TTMM edge case tests to `tests/unit/test_dates.py`

### Implementation for TTMM

- [ ] T050 [US6] Implement `derive_year()` algorithm in `datev_lint/core/parser/dates.py`
- [ ] T051 [US6] Implement period-based year derivation (HIGH/AMBIGUOUS/FAILED) in `datev_lint/core/parser/dates.py`
- [ ] T052 [US6] Implement fiscal-year-based derivation (MEDIUM) in `datev_lint/core/parser/dates.py`
- [ ] T053 [US6] Implement UNKNOWN confidence handling in `datev_lint/core/parser/dates.py`
- [ ] T054 [US6] Integrate TTMM derivation into `parse_row()` in `datev_lint/core/parser/rows.py`

**Checkpoint**: TTMM dates are derived with correct confidence levels

---

## Phase 5: Streaming & Performance - US7 (Priority: P2)

**Goal**: Stream large files (1M rows) with < 1.2GB memory peak

**Independent Test**: Parse 1M row file with memory tracking, verify peak < 1.2GB

### Golden Files for Performance

- [ ] T055 Create `tests/fixtures/golden/valid_50k_rows.csv` generator script in `tests/fixtures/generate_large_files.py`
- [ ] T056 [P] Create pytest fixture for 50k/100k/1M row files in `tests/conftest.py`

### Tests for Streaming

- [ ] T057 [P] [US7] Create `tests/benchmark/test_performance.py` with timing benchmarks
- [ ] T058 [P] [US7] Add memory tracking tests to `tests/benchmark/test_performance.py`
- [ ] T059 [P] [US7] Add CI performance gate (fail if regression > 10%) in `tests/benchmark/test_performance.py`

### Implementation for Streaming

- [ ] T060 [US7] Optimize tokenizer for streaming (avoid string concatenation) in `datev_lint/core/parser/tokenizer.py`
- [ ] T061 [US7] Implement buffer pooling in `datev_lint/core/parser/tokenizer.py`
- [ ] T062 [US7] Add `__slots__` to BookingRow for memory efficiency in `datev_lint/core/parser/models.py`
- [ ] T063 [US7] Verify streaming iterator doesn't materialize rows in `datev_lint/core/parser/__init__.py`

**Checkpoint**: Performance targets met - 50k rows < 1s, 1M rows < 1.2GB

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, edge cases, final validation

- [ ] T064 [P] Add docstrings to all public functions in `datev_lint/core/parser/`
- [ ] T065 [P] Create `py.typed` marker for PEP 561 in `datev_lint/`
- [ ] T066 Add edge case handling: empty file, header-only file in `datev_lint/core/parser/__init__.py`
- [ ] T067 Add edge case handling: NULL bytes, very long lines in `datev_lint/core/parser/tokenizer.py`
- [ ] T068 Add edge case handling: > 99,999 rows warning in `datev_lint/core/parser/rows.py`
- [ ] T069 [P] Validate all quickstart.md examples work in `tests/integration/test_quickstart.py`
- [ ] T070 [P] Run mypy and fix any type errors
- [ ] T071 [P] Run ruff and fix any linting issues
- [ ] T072 Update `datev_lint/core/parser/__init__.py` with final public API exports

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ─────────────────────────────────────────────────┐
                                                                │
Phase 2: Foundational ──────────────────────────────────────────┤
         (Models, Errors, Field Dictionary)                     │
                                                                ▼
         ┌──────────────────────────────────────────────────────┤
         │                                                      │
         ▼                                                      │
Phase 3: Core Parsing (US1-US5) ────────────────────────────────┤
         MVP - Parse valid files                                │
                                                                │
         ┌──────────────────────────────────────────────────────┤
         │                                                      │
         ▼                                                      ▼
Phase 4: TTMM (US6)                    Phase 5: Streaming (US7)
         Can run in parallel ◄────────► Can run in parallel
                                                                │
         └──────────────────────────────────────────────────────┤
                                                                ▼
Phase 6: Polish & Cross-Cutting ────────────────────────────────┘
```

### User Story Dependencies

- **US1-US5 (P1)**: Tightly coupled - implement together as Core Parsing MVP
  - US2 (Encoding) → enables file reading
  - US4 (Tokenizer) → depends on US2
  - US3 (Header) → depends on US4
  - US1 (Parse) → depends on US2, US3, US4
  - US5 (Rows) → depends on US4, field dictionary
- **US6 (P2)**: TTMM - depends on Core Parsing, can run parallel to US7
- **US7 (P2)**: Streaming - depends on Core Parsing, can run parallel to US6

### Within Each Phase

- Golden files before tests
- Tests before implementation (TDD for golden files)
- Models before services
- Lower layers before higher layers (encoding → tokenizer → header → rows → parse_file)

### Parallel Opportunities

```bash
# Phase 1 - All can run in parallel:
T003, T004, T005, T006, T007, T008

# Phase 2 - Models can run in parallel:
T011, T012, T013, T014 (after T009, T010)

# Phase 3 - Golden files can run in parallel:
T022, T023, T024, T025, T026, T027

# Phase 3 - Tests can run in parallel:
T028, T029, T030, T031, T032

# Phase 4 & 5 - Can run entirely in parallel after Phase 3

# Phase 6 - Most can run in parallel:
T064, T065, T069, T070, T071
```

---

## Implementation Strategy

### MVP First (Phase 1-3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational models
3. Complete Phase 3: Core Parsing (US1-US5)
4. **STOP and VALIDATE**: Run `parse_file("valid_minimal_700.csv")` successfully
5. Commit as "feat: implement core DATEV parser"

### Incremental Delivery

1. Setup + Foundational → Project structure ready
2. Add Core Parsing → MVP complete, can parse valid files
3. Add TTMM (US6) → Date derivation works
4. Add Streaming (US7) → Performance targets met
5. Polish → Production ready

### Critical Path

```
T001 → T002 → T009 → T015 → T019 → T033 → T035 → T038 → T044
Setup → Deps → Errors → Header Model → Field Dict → Encoding → Tokenizer → Header Parser → parse_file()
```

---

## Summary

| Phase | Tasks | Parallel | Purpose |
|-------|-------|----------|---------|
| 1. Setup | T001-T008 | 6 | Project structure |
| 2. Foundational | T009-T021 | 5 | Models, errors, field dict |
| 3. Core Parsing | T022-T045 | 12 | MVP - parse valid files |
| 4. TTMM | T046-T054 | 4 | Date year derivation |
| 5. Streaming | T055-T063 | 4 | Performance optimization |
| 6. Polish | T064-T072 | 6 | Docs, edge cases, validation |

**Total Tasks**: 72
**MVP Tasks (Phase 1-3)**: 45
**Parallel Opportunities**: 37 tasks marked [P]

---

## Notes

- All account numbers (konto, gegenkonto, beraternummer, mandantennummer) MUST be strings - NEVER convert to int!
- Golden files are essential - create them before writing tests
- Performance benchmarks should be part of CI to prevent regressions
- Each phase has a checkpoint for validation before proceeding
