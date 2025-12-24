# Tasks: Rule Engine

**Input**: Design documents from `/specs/002-rule-engine/`
**Prerequisites**: 001-parser-core must be complete
**Depends on**: Parser Core (parse_file, ParseResult, BookingRow)

## Phase 1: Setup

- [ ] T001 Create `datev_lint/core/rules/` directory structure
- [ ] T002 [P] Create `datev_lint/core/rules/__init__.py` with public API
- [ ] T003 [P] Create `datev_lint/rules/` directory for YAML rules
- [ ] T004 [P] Create `datev_lint/rules/profiles/` directory
- [ ] T005 [P] Add `pybloom-live>=4.0` to dependencies in `pyproject.toml`

---

## Phase 2: Foundational

- [ ] T006 Create Stage enum in `datev_lint/core/rules/models.py`
- [ ] T007 Create Severity enum in `datev_lint/core/rules/models.py`
- [ ] T008 [P] Create Constraint model in `datev_lint/core/rules/models.py`
- [ ] T009 [P] Create FixStrategy model in `datev_lint/core/rules/models.py`
- [ ] T010 Create Rule base model in `datev_lint/core/rules/models.py`
- [ ] T011 Create Finding model (with rule_version!) in `datev_lint/core/rules/models.py`
- [ ] T012 Create Profile model in `datev_lint/core/rules/models.py`
- [ ] T013 Create ValidationSummary model in `datev_lint/core/rules/models.py`

**Checkpoint**: All models defined

---

## Phase 3: Rule Loading - US3, US4 (Priority: P1)

**Goal**: Load rules from YAML and profiles with inheritance

- [ ] T014 [P] [US3] Create `tests/fixtures/rules/test_rule.yaml` golden file
- [ ] T015 [P] [US4] Create `tests/fixtures/rules/test_profile.yaml` golden file
- [ ] T016 [P] [US3] Create `tests/unit/test_loader.py` for YAML loading
- [ ] T017 [US3] Implement ConstraintRegistry in `datev_lint/core/rules/constraints.py`
- [ ] T018 [US3] Implement RegexConstraint in `datev_lint/core/rules/constraints.py`
- [ ] T019 [P] [US3] Implement MaxLengthConstraint in `datev_lint/core/rules/constraints.py`
- [ ] T020 [P] [US3] Implement EnumConstraint in `datev_lint/core/rules/constraints.py`
- [ ] T021 [P] [US3] Implement RequiredConstraint in `datev_lint/core/rules/constraints.py`
- [ ] T022 [US3] Implement YAML rule loader in `datev_lint/core/rules/loader.py`
- [ ] T023 [US4] Implement profile loader with inheritance in `datev_lint/core/rules/loader.py`
- [ ] T024 [US4] Implement profile override application in `datev_lint/core/rules/loader.py`

**Checkpoint**: YAML rules and profiles load correctly

---

## Phase 4: Execution Pipeline - US1, US2 (Priority: P1) 🎯 MVP

**Goal**: Run rules in stages, abort on FATAL

- [ ] T025 [P] [US2] Create `tests/unit/test_pipeline.py` for stage execution
- [ ] T026 [P] [US1] Create `tests/fixtures/rules/missing_konto.csv` golden file
- [ ] T027 [P] [US1] Create `tests/fixtures/rules/invalid_belegfeld.csv` golden file
- [ ] T028 [US2] Implement ExecutionPipeline in `datev_lint/core/rules/pipeline.py`
- [ ] T029 [US2] Implement stage ordering in `datev_lint/core/rules/pipeline.py`
- [ ] T030 [US2] Implement FATAL abort logic in `datev_lint/core/rules/pipeline.py`
- [ ] T031 [US1] Implement RuleRegistry in `datev_lint/core/rules/registry.py`
- [ ] T032 [US1] Implement rule discovery (built-in + plugins) in `datev_lint/core/rules/registry.py`
- [ ] T033 [US1] Implement `validate()` main entry point in `datev_lint/core/rules/__init__.py`
- [ ] T034 [P] [US1] Create `tests/integration/test_validate_e2e.py`

**Checkpoint**: validate() works with basic rules

---

## Phase 5: Built-in Rules - US1 (Priority: P1)

**Goal**: Implement 30 baseline rules

### Encoding/Header Rules (5)
- [ ] T035 [P] [US1] Create `datev_lint/rules/base.yaml` with DVL-ENC-* rules
- [ ] T036 [P] [US1] Create `datev_lint/core/rules/builtin/encoding.py` for DVL-ENC-001
- [ ] T037 [P] [US1] Create `datev_lint/core/rules/builtin/header.py` for DVL-HDR-001 to DVL-HDR-003

### Schema Rules (10)
- [ ] T038 [P] [US1] Add DVL-FIELD-001 to DVL-FIELD-011 in `datev_lint/rules/base.yaml`
- [ ] T039 [US1] Create `datev_lint/core/rules/builtin/fields.py` for field validation

### Date Rules (5)
- [ ] T040 [P] [US1] Add DVL-DATE-* rules to `datev_lint/rules/base.yaml`
- [ ] T041 [US1] Create `datev_lint/core/rules/builtin/dates.py` for date validation

### Semantic Rules (5)
- [ ] T042 [P] [US1] Add DVL-ROW-* rules to `datev_lint/rules/base.yaml`
- [ ] T043 [US1] Create `datev_lint/core/rules/builtin/rows.py` for row validation

### Cross-Row Rules (5)
- [ ] T044 [US7] Create `datev_lint/core/rules/builtin/cross.py` for cross-row rules
- [ ] T045 [US7] Implement DuplicateBelegfeld1Rule with Bloom filter
- [ ] T046 [US7] Implement RowCountRule (DVL-CROSS-002)

**Checkpoint**: 30 baseline rules implemented

---

## Phase 6: Profiles - US4 (Priority: P1)

**Goal**: Create built-in profiles

- [ ] T047 [P] [US4] Create `datev_lint/rules/profiles/de.datev700.bookingbatch.yaml`
- [ ] T048 [P] [US4] Create `datev_lint/rules/profiles/de.skr03.default.yaml`
- [ ] T049 [P] [US4] Create `datev_lint/rules/profiles/de.skr04.default.yaml`
- [ ] T050 [P] [US4] Create `tests/unit/test_profiles.py`

---

## Phase 7: Python Plugin API - US5 (Priority: P2)

**Goal**: Support custom Python rules

- [ ] T051 [P] [US5] Create `tests/unit/test_plugin_rules.py`
- [ ] T052 [US5] Create base Rule class in `datev_lint/core/rules/base.py`
- [ ] T053 [US5] Implement entry point discovery in `datev_lint/core/rules/registry.py`
- [ ] T054 [US5] Document plugin API in `datev_lint/core/rules/base.py`

---

## Phase 8: Rule Versioning - US6 (Priority: P2)

**Goal**: Include versions in all findings

- [ ] T055 [P] [US6] Create `tests/unit/test_versioning.py`
- [ ] T056 [US6] Add engine_version to all findings in `datev_lint/core/rules/pipeline.py`
- [ ] T057 [US6] Add profile_version to ValidationSummary in `datev_lint/core/rules/pipeline.py`

---

## Phase 9: Performance - US7 (Priority: P2)

**Goal**: 20k rows/s throughput, 1M cross-row ≤ 30s

- [ ] T058 [P] [US7] Create `tests/benchmark/test_rule_performance.py`
- [ ] T059 [US7] Optimize constraint checking in `datev_lint/core/rules/constraints.py`
- [ ] T060 [US7] Optimize Bloom filter for duplicates in `datev_lint/core/rules/builtin/cross.py`
- [ ] T061 [US7] Add performance CI gate (fail if regression > 10%)

---

## Phase 10: Polish

- [ ] T062 [P] Add docstrings to all public functions
- [ ] T063 [P] Run mypy and fix type errors
- [ ] T064 [P] Run ruff and fix linting issues
- [ ] T065 Update public API exports in `datev_lint/core/rules/__init__.py`

---

## Summary

| Phase | Tasks | Purpose |
|-------|-------|---------|
| 1. Setup | T001-T005 | Directory structure |
| 2. Foundational | T006-T013 | Models |
| 3. Rule Loading | T014-T024 | YAML + Profiles |
| 4. Pipeline | T025-T034 | Execution (MVP) |
| 5. Built-in Rules | T035-T046 | 30 rules |
| 6. Profiles | T047-T050 | SKR03/SKR04 |
| 7. Plugin API | T051-T054 | Python rules |
| 8. Versioning | T055-T057 | Audit trail |
| 9. Performance | T058-T061 | Optimization |
| 10. Polish | T062-T065 | Docs, types |

**Total Tasks**: 65
**MVP Tasks (Phase 1-5)**: 46
