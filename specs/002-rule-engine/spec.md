# Feature Specification: Rule Engine

**Feature Branch**: `002-rule-engine`
**Created**: 2025-12-24
**Status**: Draft
**Input**: Product Specification v2.1 - Section 6 (Rule Engine Design), Section 8 (Error Taxonomy)

## User Scenarios & Testing

### User Story 1 - Run Baseline Rules on Parsed File (Priority: P1)

Als Buchhalter möchte ich eine DATEV-Datei gegen die Baseline-Regeln validieren, damit ich Fehler vor dem Upload erkenne.

**Why this priority**: Kernfunktionalität - ohne Regeln keine Validierung.

**Independent Test**: Eine Datei mit bekannten Fehlern liefert die erwarteten Findings.

**Acceptance Scenarios**:

1. **Given** eine Datei mit fehlendem Pflichtfeld "Konto", **When** Regeln ausgeführt werden, **Then** Finding `DVL-FIELD-001` mit Severity ERROR.
2. **Given** eine Datei mit Belegfeld1 "RE-2025/001" (enthält Slash), **When** Regeln ausgeführt werden, **Then** Finding `DVL-FIELD-011` mit korrekter Zeilennummer.
3. **Given** eine valide Datei ohne Fehler, **When** Regeln ausgeführt werden, **Then** leere Finding-Liste, Exit Code 0.

---

### User Story 2 - Stage-based Execution Pipeline (Priority: P1)

Als Rule Engine möchte ich Regeln in Stages ausführen (parse → header → schema → semantic → cross-row), damit fatale Fehler früh abbrechen.

**Why this priority**: Strukturierte Pipeline verhindert unnötige Arbeit bei fatalen Fehlern.

**Independent Test**: Bei FATAL in parse-Stage werden keine schema-Regeln ausgeführt.

**Acceptance Scenarios**:

1. **Given** Datei mit Encoding-Fehler (FATAL in parse), **When** Pipeline läuft, **Then** nur parse-Stage Findings, keine schema-Findings.
2. **Given** Datei mit Header-Fehler (FATAL in header), **When** Pipeline läuft, **Then** parse + header Findings, keine row-Findings.
3. **Given** Datei mit schema-Errors (non-fatal), **When** Pipeline läuft, **Then** alle Stages werden durchlaufen, alle Findings gesammelt.

---

### User Story 3 - Define Rules via YAML DSL (Priority: P1)

Als Entwickler möchte ich Regeln in YAML definieren können, damit einfache Feld-Validierungen ohne Python-Code möglich sind.

**Why this priority**: 80% der Regeln sind einfache Feld-Checks, die in YAML abbildbar sind.

**Independent Test**: Eine YAML-Regel für Belegfeld-Länge erzeugt korrektes Finding.

**Acceptance Scenarios**:

1. **Given** YAML-Regel mit `constraint.type: regex` und `pattern: ^[A-Z0-9]+$`, **When** Feld "abc123" geprüft wird, **Then** Finding weil lowercase.
2. **Given** YAML-Regel mit `constraint.type: max_length` und `value: 36`, **When** Feld mit 40 Zeichen, **Then** Finding mit korrektem Code.
3. **Given** YAML-Regel mit `severity: warning`, **When** Regel matcht, **Then** Finding hat Severity WARNING (nicht ERROR).

---

### User Story 4 - Profile System with Overrides (Priority: P1)

Als Steuerberater möchte ich Profile nutzen können (z.B. SKR03, SKR04), die Regel-Konfigurationen bündeln.

**Why this priority**: Unterschiedliche Mandanten brauchen unterschiedliche Regel-Sets.

**Independent Test**: Profile `de.skr03.default` aktiviert andere Regeln als `de.skr04.default`.

**Acceptance Scenarios**:

1. **Given** Profile mit `enable: ["DVL-*"]` und `disable: ["DVL-AT-*"]`, **When** Profile geladen, **Then** alle DVL-Regeln aktiv außer AT-spezifische.
2. **Given** Profile mit `overrides.severity.DVL-FIELD-011: warning`, **When** Regel matcht, **Then** Finding hat Severity WARNING statt ERROR.
3. **Given** Profile mit `base: "de.datev700.bookingbatch"`, **When** Profile geladen, **Then** Base-Regeln werden geerbt, Overrides angewendet.

---

### User Story 5 - Python Plugin Rules for Complex Logic (Priority: P2)

Als Entwickler möchte ich komplexe Regeln in Python schreiben können, wenn YAML nicht ausreicht.

**Why this priority**: Cross-Row-Logik und komplexe Validierungen brauchen Python.

**Independent Test**: Python-Regel erkennt doppelte Belegfeld-1-Werte.

**Acceptance Scenarios**:

1. **Given** Python-Regel `DuplicateBelegfeld1Rule`, **When** zwei Zeilen mit gleichem Belegfeld1, **Then** Finding `DVL-CROSS-001` mit `related` Referenz.
2. **Given** Python-Regel mit `stage = "cross_row"`, **When** Pipeline läuft, **Then** Regel wird nach allen row-level Regeln ausgeführt.
3. **Given** Python-Regel mit `yield Finding(...)`, **When** Regel matcht, **Then** Finding enthält `rule_version` aus Klassen-Attribut.

---

### User Story 6 - Rule Versioning for Audit (Priority: P2)

Als Auditor möchte ich sehen, welche Regel-Version ein Finding erzeugt hat, damit Validierungen reproduzierbar sind.

**Why this priority**: Constitution Principle VI - Audit & Versioning.

**Independent Test**: Finding enthält `rule_version` und `engine_version`.

**Acceptance Scenarios**:

1. **Given** Regel mit `version: "1.0.0"`, **When** Finding erzeugt wird, **Then** Finding enthält `rule_version: "1.0.0"`.
2. **Given** Engine Version 1.2.3, **When** Findings erzeugt werden, **Then** alle Findings enthalten `engine_version: "1.2.3"`.
3. **Given** Profile mit `version: "1.0.0"`, **When** Validation läuft, **Then** Summary enthält `profile_version: "1.0.0"`.

---

### User Story 7 - Cross-Row Validation (Priority: P2)

Als Validator möchte ich Prüfungen über mehrere Zeilen durchführen (Duplikate, Summen), damit logische Fehler erkannt werden.

**Why this priority**: Doppelte Belegnummern sind häufige Fehlerursache.

**Independent Test**: Doppelte Belegfeld-1-Werte werden erkannt.

**Acceptance Scenarios**:

1. **Given** Datei mit Belegfeld1 "RE-001" in Zeile 5 und 12, **When** Cross-Row-Regeln laufen, **Then** Finding mit `location.row_no: 12` und `related: [{row_no: 5}]`.
2. **Given** Datei mit > 99.999 Zeilen, **When** Cross-Row-Regeln laufen, **Then** Finding `DVL-CROSS-002` (Row count exceeded).
3. **Given** Datei mit 50.000 Zeilen, **When** Cross-Row-Duplikat-Check läuft, **Then** Ausführungszeit ≤ 5s.

---

### Edge Cases

- Was passiert bei Regeln mit ungültiger YAML-Syntax?
- Wie werden zirkuläre Profile-Vererbungen behandelt?
- Was passiert bei Regeln ohne Version?
- Wie verhält sich die Engine bei 1000+ Findings?

## Requirements

### Functional Requirements

- **FR-001**: Engine MUSS Regeln in definierten Stages ausführen (parse, header, schema, row_semantic, cross_row, policy)
- **FR-002**: Engine MUSS bei FATAL-Findings in parse/header Stages abbrechen
- **FR-003**: Engine MUSS YAML-basierte Regel-Definitionen unterstützen
- **FR-004**: Engine MUSS Python-Plugin-Regeln über Entry Points laden
- **FR-005**: Engine MUSS Profile mit Vererbung (`base`) und Overrides unterstützen
- **FR-006**: Engine MUSS Rule-Versionen in Findings aufnehmen
- **FR-007**: Engine MUSS mindestens 30 Baseline-Regeln enthalten (MVP)
- **FR-008**: Engine MUSS Finding-Objekte mit vollständiger Location (file, row_no, field) erzeugen
- **FR-009**: Engine MUSS Fix-Kandidaten in Findings aufnehmen (wenn verfügbar)
- **FR-010**: Engine MUSS Cross-Row-Validierungen performant ausführen (Bloom Filter für Duplikate)

### Key Entities

- **Rule**: Abstrakte Regel mit id, version, stage, severity, constraint, fix
- **Finding**: Validierungsergebnis mit code, rule_version, severity, message, location, fix_candidates
- **Profile**: Regel-Bundle mit id, version, base, enable/disable, overrides
- **ExecutionPipeline**: Orchestriert Stage-basierte Regelausführung
- **RuleRegistry**: Lädt und verwaltet alle verfügbaren Regeln

## Success Criteria

### Measurable Outcomes

- **SC-001**: ≥ 30 Baseline-Regeln implementiert und getestet
- **SC-002**: 20k Zeilen/s Validate-Throughput (row-level Regeln)
- **SC-003**: Cross-Row-Check für 1M Zeilen ≤ 30s
- **SC-004**: 100% der Findings enthalten rule_version
- **SC-005**: Profile-Loading + Override-Anwendung ≤ 100ms
