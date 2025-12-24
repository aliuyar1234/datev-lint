# Tasks: Fix Engine

**Input**: Design documents from `/specs/003-fix-engine/`
**Prerequisites**: 001-parser-core, 002-rule-engine must be complete
**Depends on**: Parser, Rule Engine (Finding with fix_candidates)

## Phase 1: Setup

- [ ] T001 Create `datev_lint/core/fix/` directory structure
- [ ] T002 [P] Create `datev_lint/core/fix/__init__.py` with public API
- [ ] T003 [P] Create `audit/` directory for audit logs
- [ ] T004 [P] Create `tests/fixtures/fix/` directory for test files

---

## Phase 2: Foundational

- [ ] T005 Create RiskLevel enum in `datev_lint/core/fix/models.py`
- [ ] T006 Create PatchOperation enum in `datev_lint/core/fix/models.py`
- [ ] T007 [P] Create Patch model in `datev_lint/core/fix/models.py`
- [ ] T008 [P] Create Conflict model in `datev_lint/core/fix/models.py`
- [ ] T009 Create PatchPlan model in `datev_lint/core/fix/models.py`
- [ ] T010 Create WriteMode enum in `datev_lint/core/fix/models.py`
- [ ] T011 [P] Create WriteResult model in `datev_lint/core/fix/models.py`
- [ ] T012 Create AuditEntry model in `datev_lint/core/fix/models.py`
- [ ] T013 [P] Create RollbackResult model in `datev_lint/core/fix/models.py`

**Checkpoint**: All models defined

---

## Phase 3: Patch Planning - US1 (Priority: P1) 🎯 MVP

**Goal**: Generate patch plan from findings

- [ ] T014 [P] [US1] Create `tests/fixtures/fix/before_belegfeld_fix.csv`
- [ ] T015 [P] [US1] Create `tests/fixtures/fix/after_belegfeld_fix.csv`
- [ ] T016 [P] [US1] Create `tests/unit/test_planner.py`
- [ ] T017 [US1] Implement PatchPlanner in `datev_lint/core/fix/planner.py`
- [ ] T018 [US1] Implement patch extraction from fix_candidates in `datev_lint/core/fix/planner.py`
- [ ] T019 [US1] Implement `plan_fixes()` in `datev_lint/core/fix/__init__.py`

**Checkpoint**: plan_fixes() returns PatchPlan

---

## Phase 4: Dry-Run Preview - US1 (Priority: P1)

**Goal**: Preview diff without applying

- [ ] T020 [P] [US1] Create `tests/unit/test_preview.py`
- [ ] T021 [US1] Implement diff generation in `datev_lint/core/fix/preview.py`
- [ ] T022 [US1] Implement `preview_diff()` in `datev_lint/core/fix/__init__.py`

---

## Phase 5: Patch Operations - US1, US3 (Priority: P1)

**Goal**: Implement patch operation types

- [ ] T023 [P] [US1] Create `tests/unit/test_operations.py`
- [ ] T024 [US1] Implement set_field operation in `datev_lint/core/fix/operations.py`
- [ ] T025 [P] [US1] Implement normalize_decimal operation in `datev_lint/core/fix/operations.py`
- [ ] T026 [P] [US1] Implement truncate operation in `datev_lint/core/fix/operations.py`
- [ ] T027 [P] [US1] Implement sanitize_chars operation in `datev_lint/core/fix/operations.py`
- [ ] T028 [P] [US1] Implement upper operation in `datev_lint/core/fix/operations.py`
- [ ] T029 [US3] Implement operation dispatcher in `datev_lint/core/fix/operations.py`

---

## Phase 6: Writer Modes - US3, US4 (Priority: P1)

**Goal**: Write files in preserve or canonical mode

- [ ] T030 [P] [US3] Create `tests/unit/test_writer.py`
- [ ] T031 [US3] Implement Writer base class in `datev_lint/core/fix/writer.py`
- [ ] T032 [US3] Implement preserve mode in `datev_lint/core/fix/writer.py`
- [ ] T033 [US4] Implement canonical mode in `datev_lint/core/fix/writer.py`
- [ ] T034 [US3] Implement fallback logic (preserve → canonical) in `datev_lint/core/fix/writer.py`

---

## Phase 7: Apply Fixes - US2 (Priority: P1 - Pro)

**Goal**: Atomic write with backup

- [ ] T035 [P] [US2] Create `tests/unit/test_backup.py`
- [ ] T036 [P] [US2] Create `tests/integration/test_fix_e2e.py`
- [ ] T037 [US2] Implement BackupManager in `datev_lint/core/fix/backup.py`
- [ ] T038 [US2] Implement atomic write (temp + rename) in `datev_lint/core/fix/writer.py`
- [ ] T039 [US2] Implement `apply_fixes()` in `datev_lint/core/fix/__init__.py`
- [ ] T040 [US2] Add re-validation after apply in `datev_lint/core/fix/__init__.py`

**Checkpoint**: apply_fixes() works with backup

---

## Phase 8: Conflict Detection - US8 (Priority: P3)

**Goal**: Detect and resolve patch conflicts

- [ ] T041 [P] [US8] Create `tests/unit/test_conflicts.py`
- [ ] T042 [US8] Implement ConflictDetector in `datev_lint/core/fix/conflicts.py`
- [ ] T043 [US8] Implement first-write-wins resolution in `datev_lint/core/fix/conflicts.py`
- [ ] T044 [US8] Add conflict info to PatchPlan in `datev_lint/core/fix/planner.py`

---

## Phase 9: Audit Log - US6 (Priority: P2)

**Goal**: Log all fix operations with versions

- [ ] T045 [P] [US6] Create `tests/unit/test_audit.py`
- [ ] T046 [US6] Implement AuditLogger in `datev_lint/core/fix/audit.py`
- [ ] T047 [US6] Add version info to audit entries in `datev_lint/core/fix/audit.py`
- [ ] T048 [US6] Implement `get_audit_entry()` in `datev_lint/core/fix/__init__.py`
- [ ] T049 [US6] Implement `list_audit_entries()` in `datev_lint/core/fix/__init__.py`

---

## Phase 10: Rollback - US5 (Priority: P2)

**Goal**: Restore from backup

- [ ] T050 [P] [US5] Create `tests/unit/test_rollback.py`
- [ ] T051 [US5] Implement checksum verification in `datev_lint/core/fix/backup.py`
- [ ] T052 [US5] Implement `rollback()` in `datev_lint/core/fix/__init__.py`
- [ ] T053 [US5] Log rollback to audit in `datev_lint/core/fix/audit.py`

---

## Phase 11: Risk Management - US7 (Priority: P2)

**Goal**: Risk levels and approval

- [ ] T054 [P] [US7] Create `tests/unit/test_risk.py`
- [ ] T055 [US7] Implement risk level definitions in `datev_lint/core/fix/risk.py`
- [ ] T056 [US7] Implement should_apply() logic in `datev_lint/core/fix/risk.py`
- [ ] T057 [US7] Add interactive approval to `apply_fixes_interactive()` in `datev_lint/core/fix/__init__.py`

---

## Phase 12: Performance

**Goal**: 50k rows + 100 fixes ≤ 2s

- [ ] T058 [P] Create `tests/benchmark/test_fix_performance.py`
- [ ] T059 Optimize patch application in `datev_lint/core/fix/operations.py`
- [ ] T060 Add performance CI gate

---

## Phase 13: Polish

- [ ] T061 [P] Add docstrings to all public functions
- [ ] T062 [P] Run mypy and fix type errors
- [ ] T063 [P] Run ruff and fix linting issues
- [ ] T064 Update public API exports in `datev_lint/core/fix/__init__.py`

---

## Summary

| Phase | Tasks | Purpose |
|-------|-------|---------|
| 1. Setup | T001-T004 | Directory structure |
| 2. Foundational | T005-T013 | Models |
| 3. Patch Planning | T014-T019 | Generate plan (MVP) |
| 4. Dry-Run | T020-T022 | Preview diff |
| 5. Operations | T023-T029 | Patch types |
| 6. Writer | T030-T034 | Write modes |
| 7. Apply | T035-T040 | Atomic write (Pro) |
| 8. Conflicts | T041-T044 | Detection |
| 9. Audit | T045-T049 | Logging |
| 10. Rollback | T050-T053 | Restore |
| 11. Risk | T054-T057 | Approval |
| 12. Performance | T058-T060 | Optimization |
| 13. Polish | T061-T064 | Docs, types |

**Total Tasks**: 64
**MVP Tasks (Phase 1-7)**: 40
