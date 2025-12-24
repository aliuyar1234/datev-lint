# Tasks: CLI & Output Adapters

**Input**: Design documents from `/specs/004-cli-outputs/`
**Prerequisites**: 001-parser-core, 002-rule-engine, 003-fix-engine
**Depends on**: All core libraries

## Phase 1: Setup

- [ ] T001 Create `datev_lint/cli/` directory structure
- [ ] T002 [P] Create `datev_lint/cli/__init__.py`
- [ ] T003 [P] Create `datev_lint/cli/commands/` directory
- [ ] T004 [P] Create `datev_lint/cli/output/` directory
- [ ] T005 [P] Add `typer>=0.9.0` and `rich>=13.0` to dependencies
- [ ] T006 Add CLI entry point to `pyproject.toml`

---

## Phase 2: Foundational

- [ ] T007 Create OutputFormat enum in `datev_lint/cli/output/base.py`
- [ ] T008 Create ExitCode enum in `datev_lint/cli/context.py`
- [ ] T009 [P] Create CliContext model in `datev_lint/cli/context.py`
- [ ] T010 Create OutputAdapter protocol in `datev_lint/cli/output/base.py`

**Checkpoint**: Base types defined

---

## Phase 3: Main App - US8 (Priority: P1)

**Goal**: CLI entry point with --help

- [ ] T011 [P] [US8] Create `tests/unit/test_cli_main.py`
- [ ] T012 [US8] Create Typer app in `datev_lint/cli/main.py`
- [ ] T013 [US8] Add --version option in `datev_lint/cli/main.py`
- [ ] T014 [US8] Add --help for all commands in `datev_lint/cli/main.py`

---

## Phase 4: Terminal Output - US1 (Priority: P1) 🎯 MVP

**Goal**: Colored terminal output

- [ ] T015 [P] [US1] Create `tests/fixtures/cli/expected_terminal.txt`
- [ ] T016 [P] [US1] Create `tests/unit/test_terminal_output.py`
- [ ] T017 [US1] Implement TerminalOutput in `datev_lint/cli/output/terminal.py`
- [ ] T018 [US1] Implement severity colors in `datev_lint/cli/output/terminal.py`
- [ ] T019 [US1] Implement summary formatting in `datev_lint/cli/output/terminal.py`
- [ ] T020 [US1] Add TTY detection in `datev_lint/cli/output/terminal.py`

---

## Phase 5: Validate Command - US1, US3, US5 (Priority: P1)

**Goal**: validate command with options

- [ ] T021 [P] [US1] Create `tests/integration/test_cli_validate.py`
- [ ] T022 [US1] Implement validate command in `datev_lint/cli/commands/validate.py`
- [ ] T023 [US5] Add --profile option in `datev_lint/cli/commands/validate.py`
- [ ] T024 [US3] Implement exit code logic in `datev_lint/cli/commands/validate.py`
- [ ] T025 [US3] Add --fail-on option in `datev_lint/cli/commands/validate.py`

**Checkpoint**: validate command works

---

## Phase 6: JSON Output - US2 (Priority: P1)

**Goal**: JSON output format

- [ ] T026 [P] [US2] Create `tests/fixtures/cli/expected_json.json`
- [ ] T027 [P] [US2] Create `tests/unit/test_json_output.py`
- [ ] T028 [US2] Implement JsonOutput in `datev_lint/cli/output/json.py`
- [ ] T029 [US2] Add --format json option in `datev_lint/cli/commands/validate.py`
- [ ] T030 [US2] Add --out option for file output in `datev_lint/cli/commands/validate.py`

---

## Phase 7: SARIF Output - US4 (Priority: P2)

**Goal**: SARIF 2.1.0 for GitHub

- [ ] T031 [P] [US4] Create `tests/fixtures/cli/expected_sarif.json`
- [ ] T032 [P] [US4] Create `tests/unit/test_sarif_output.py`
- [ ] T033 [US4] Implement SarifOutput in `datev_lint/cli/output/sarif.py`
- [ ] T034 [US4] Add --format sarif option in `datev_lint/cli/commands/validate.py`

---

## Phase 8: Fix Command (Priority: P1)

**Goal**: fix command with dry-run and apply

- [ ] T035 [P] Create `tests/integration/test_cli_fix.py`
- [ ] T036 Implement fix command in `datev_lint/cli/commands/fix.py`
- [ ] T037 Add --dry-run option (default) in `datev_lint/cli/commands/fix.py`
- [ ] T038 Add --apply option (Pro) in `datev_lint/cli/commands/fix.py`
- [ ] T039 Add --write-mode option in `datev_lint/cli/commands/fix.py`
- [ ] T040 Add --accept-risk option in `datev_lint/cli/commands/fix.py`
- [ ] T041 Add --yes option in `datev_lint/cli/commands/fix.py`

---

## Phase 9: Utility Commands (Priority: P1)

**Goal**: profiles, rules, explain commands

- [ ] T042 [P] Implement profiles list in `datev_lint/cli/commands/profiles.py`
- [ ] T043 [P] Implement rules list in `datev_lint/cli/commands/rules.py`
- [ ] T044 Implement explain command in `datev_lint/cli/commands/explain.py`

---

## Phase 10: Fingerprinting - US6 (Priority: P2)

**Goal**: Auto-detect exporter

- [ ] T045 [P] [US6] Create `tests/unit/test_fingerprint.py`
- [ ] T046 [US6] Create ExporterFingerprint model in `datev_lint/cli/fingerprint/detector.py`
- [ ] T047 [US6] Implement detection signals in `datev_lint/cli/fingerprint/signals.py`
- [ ] T048 [US6] Implement fingerprint command in `datev_lint/cli/commands/fingerprint.py`
- [ ] T049 [US6] Add --auto-profile option to validate in `datev_lint/cli/commands/validate.py`

---

## Phase 11: Report Command (Pro) - US7 (Priority: P3)

**Goal**: PDF/HTML reports

- [ ] T050 [P] [US7] Add `jinja2>=3.0` and `weasyprint>=60.0` to pro dependencies
- [ ] T051 [P] [US7] Create report template in `datev_lint/templates/report.html.j2`
- [ ] T052 [US7] Implement PdfOutput in `datev_lint/cli/output/pdf.py`
- [ ] T053 [US7] Implement report command in `datev_lint/cli/commands/report.py`

---

## Phase 12: Rollback Command (Pro)

**Goal**: rollback fix operations

- [ ] T054 Implement rollback command in `datev_lint/cli/commands/rollback.py`

---

## Phase 13: Performance

**Goal**: 1000 findings terminal output ≤ 1s

- [ ] T055 [P] Create `tests/benchmark/test_cli_performance.py`
- [ ] T056 Optimize terminal output in `datev_lint/cli/output/terminal.py`

---

## Phase 14: Polish

- [ ] T057 [P] Add docstrings to all commands
- [ ] T058 [P] Run mypy and fix type errors
- [ ] T059 [P] Run ruff and fix linting issues
- [ ] T060 [P] Create example GitHub Action in `examples/github-action.yml`
- [ ] T061 Update CLI entry point exports

---

## Summary

| Phase | Tasks | Purpose |
|-------|-------|---------|
| 1. Setup | T001-T006 | Directory structure |
| 2. Foundational | T007-T010 | Base types |
| 3. Main App | T011-T014 | Entry point |
| 4. Terminal | T015-T020 | Colored output (MVP) |
| 5. Validate | T021-T025 | Main command |
| 6. JSON | T026-T030 | Machine output |
| 7. SARIF | T031-T034 | GitHub integration |
| 8. Fix | T035-T041 | Fix command |
| 9. Utilities | T042-T044 | Helper commands |
| 10. Fingerprint | T045-T049 | Auto-profile |
| 11. Report | T050-T053 | PDF/HTML (Pro) |
| 12. Rollback | T054 | Undo fixes (Pro) |
| 13. Performance | T055-T056 | Optimization |
| 14. Polish | T057-T061 | Docs, CI |

**Total Tasks**: 61
**MVP Tasks (Phase 1-9)**: 44
