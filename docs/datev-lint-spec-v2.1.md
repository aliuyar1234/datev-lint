# datev-lint – Erweiterte Produktspezifikation (v2.1)

**Preflight validation for DATEV exports**

Erweiterte Spezifikation mit technischer Tiefe, DATEV-Spezifika, Akzeptanzkriterien und Monetarisierungs-Architektur.

*v2.1 Changelog: Regex-Fix, Konto als String, TTMM-Algorithmus, Writer-Modi, Packaging-Entscheidung, Field Dictionary, Exporter Fingerprinting, Rule Versioning, Telemetrie-Defaults*

---

## 0. Kritische Einschätzung der v1.0

### Korrektur: "Keine dedizierte Lösung" ist nicht haltbar

Es existiert ein DATEV-Format-Prüfprogramm im Ökosystem (teils als Bestandteil/Download über DATEV Developer Portal/Partner-Kontext).

**→ Dein Moat kann daher nicht "als erster Validator" sein, sondern:**

- Bessere UX (actionable, kontextuell)
- Auto-Fix + Diffs
- CI/DevTool-Integration
- Rule-Packs pro Exporter/ERP
- Team/Audit/Workflow
- On-Prem/Enterprise API

### Timeline-Korrektur

14 Wochen bis "Production SaaS + Payment Integration" ist für 1 Person realistisch nur als "Thin Slice".

**Vertikaler Schnitt:**
- **Woche 1–6:** CLI + Rules + Fix + JSON/SARIF + License Gate = zahlende Kunden möglich
- **Woche 7–14:** Web UI/SaaS/Team/Enterprise als Ausbau

### Parser ist der Engpass

DATEV-Format ist "CSV", aber nicht "normales CSV":
- Quotes, Semikolon, ANSI/Windows-Encoding
- TTMM-Datum ohne Jahr
- Header-Zeile 1 als Datensatz + Spaltenüberschriften in Zeile 2

**→ Parser + Golden Files sind dein Engpass, nicht Regeln.**

### ⚠️ Kritischer Pfad: Sample Files

**Das echte Risiko ist nicht Code, sondern Daten.**

Ohne echte Exporte aus 2–3 Systemen baust du "gegen die Spec", aber nicht gegen die Realität.

**Deliverable Woche 1–2:**
- 10 reale (redacted) Files aus 2 Exportern + 1 Kanzlei-Policy
- Compatibility Matrix v0.1

---

## 1. Zielbild & Outcome-Metriken

### 1.1 Ziel (12 Monate)

- **€5k MRR** über Pro/Team Subscriptions + 1–2 OEM/Enterprise Deals
- **Wertversprechen:** "Import-Fails & Back-and-Forth vor dem Upload eliminieren" + "Auditierbare Korrektur-Chain"

### 1.2 Key Metrics

| Metric | MVP (Woche 6) | Month 3 | Month 12 |
|--------|---------------|---------|----------|
| Median Validate-Time (50k Zeilen) | ≤ 2s | ≤ 1.5s | ≤ 1s |
| 95p Validate-Time (1M Zeilen) | ≤ 60s | ≤ 45s | ≤ 30s |
| Memory Peak (1M Zeilen) | ≤ 1.2 GB | ≤ 1.0 GB | ≤ 0.8 GB |
| Actionable Error Rate | ≥ 70% | ≥ 80% | ≥ 90% |
| Conversion Free→Paid | ≥ 3% | ≥ 5% | ≥ 8% |

### 1.3 Performance-Messmethodik

Um die Ziele glaubwürdig und reproduzierbar zu machen:

| Parameter | Spezifikation |
|-----------|---------------|
| **Baseline Hardware** | 8 cores, 16 GB RAM, SSD |
| **Test Files** | Golden perf fixtures (10k, 50k, 100k, 1M rows) |
| **Metriken** | Parse time, validate time, peak RSS, allocations |
| **CI Gate** | Fail build wenn Regression > 10% |

---

## 2. DATEV-Formate & Versions-Support

### 2.1 Unterstützte Input-Arten

| Artefakt | Beschreibung |
|----------|--------------|
| **DATEV-Format (EXTF_*.CSV)** | Buchungsstapel + perspektivisch Stammdaten (Deb/Kred, Kontenbeschriftungen) |
| **ASCII Standardformate** | Felddefinitionen/Constraints aus DATEV Serviceinfo |
| **ZIP-Pakete** | Mehrere CSVs + ggf. Beleglinks (üblich beim Versand an Steuerberater) |

### 2.2 Versions-Support

**Minimum (für Marktfähigkeit):**
- Header Hauptversion **700** (de-facto Standard)
- Formatkategorie **21** = Buchungsstapel
- Formatversion Buchungsstapel = **12**
- Header Hauptversion **510** (Legacy/Kompatibilität)

**Support-Matrix:**

| Dimension | MVP (W6) | Month 3 | Month 12 |
|-----------|----------|---------|----------|
| Header Hauptversion | 700 + 510 (read) | 700+510 (full) | + Legacy (read) |
| Buchungsstapel | full | full | full + splitting |
| Deb/Kred Stammdaten | read+validate | full | full + fix |
| Kontenbeschriftungen | validate | full | full |
| Zahlungsbedingungen | validate | full | full |
| ZIP Bundles | validate single csv | validate zip | zip + attachments |

### 2.3 DATEV-Header – Erwartete Struktur

```
Zeile 1: Header (EXTF, Version, Kategorie, Formatname, ...)
Zeile 2: Spaltenüberschriften
Zeile 3+: Buchungsdaten
```

**Header-Felder (Pflicht):**
- Feld 1: `EXTF` (Kennzeichen)
- Feld 2: Versionsnummer (700/510)
- Feld 3: Formatkategorie (21 = Buchungsstapel)
- Feld 4: Formatname
- Feld 15/16: Zeitraum (muss im Geschäftsjahr liegen)

**Design-Entscheidung:**
- Parser akzeptiert **strict** für Pflichtfelder
- **Tolerant** für zusätzliche/reservierte Felder
- Header-Parsing liefert typed `Header`-Objekt + Raw-Token-Liste (für Roundtripping)

### 2.4 Format-Limits

- **Max. 99.999 Buchungssätze pro Stapel** (DATEV-Limit)
- → datev-lint prüft das und bietet optional Auto-Splitting (Pro/Team Paywall)

---

## 3. Systemarchitektur

### 3.1 High-Level Komponenten

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI: datev-lint                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    Core Library                             │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│  Parser  │  Rule    │  Fix     │  Report  │  Output        │
│  Layer   │  Engine  │  Engine  │  Engine  │  Adapters      │
└──────────┴──────────┴──────────┴──────────┴────────────────┘
     │           │          │          │           │
     ▼           ▼          ▼          ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│Encoding │ │Rule     │ │Fix      │ │Jinja2   │ │Terminal │
│Detector │ │Registry │ │Candidates│ │Templates│ │(Rich)   │
├─────────┤ ├─────────┤ ├─────────┤ └─────────┘ ├─────────┤
│CSV      │ │Profile  │ │Patch    │             │JSON     │
│Tokenizer│ │Resolver │ │Planner  │             ├─────────┤
├─────────┤ ├─────────┤ ├─────────┤             │SARIF    │
│Header   │ │Execution│ │Atomic   │             ├─────────┤
│Parser   │ │Pipeline │ │Writer   │             │HTML/PDF │
├─────────┤ ├─────────┤ ├─────────┤             └─────────┘
│Row      │ │Finding  │ │Rollback │
│Parser   │ │Store    │ │+ Audit  │
└─────────┘ └─────────┘ └─────────┘
```

### 3.2 "Library-first" als strategisches Design

- `datev_lint/core` muss **isoliert nutzbar** sein (für OEM/ERP-Integrationen)
- CLI & SaaS sind "Shells" um denselben Core
- **Moat-Implikation:** OEM/Enterprise kauft nicht "CLI", sondern "kompilierbare Validierungs-Engine + Rule Packs + Support"

---

## 4. Parser-Architektur (EXTF/ASCII)

### 4.1 Anforderungen (nicht verhandelbar)

| Anforderung | Beschreibung |
|-------------|--------------|
| **Streaming-fähig** | Große Stapel (bis 1M Zeilen) ohne OOM |
| **CSV nicht naiv** | Quotes, escaped quotes, embedded line breaks |
| **Encoding robust** | ANSI/Windows-1252 vs UTF-8 (mit/ohne BOM) |
| **Header-Semantik** | Zeile 1 ≠ Spaltenheader, Zeile 2 = Spaltenüberschriften |
| **Roundtrip** | `--fix` muss minimale Diff-Writes erzeugen (siehe Writer-Modi) |

### 4.2 CSV/ASCII Konventionen

| Eigenschaft | Wert |
|-------------|------|
| Zeichensatz | ANSI (Windows-1252) |
| Feldtrenner | Semikolon `;` |
| Dezimaltrennzeichen | Komma `,` |
| Datumsformat | TTMM (für Buchungsstapel) |
| Textfelder | In Anführungszeichen, Quotes werden verdoppelt |
| Zeilenende | CR beendet Datensatz, LF kann innerhalb Textfeld vorkommen |

### 4.3 Parser Layers

#### Layer 0: File Type Detection

**Heuristiken:**
- Dateiname beginnt mit `EXTF` und Endung `.csv`/`.txt`
- Erste Zeile beginnt mit `"EXTF"` oder `EXTF;`

**Output:**
```python
DetectedFormat = DATEV_FORMAT | ASCII_STANDARD | UNKNOWN
Dialect = { delimiter=';', quote='"', escape='""', newline='CRLF|LF|CR' }
```

#### Layer 1: Encoding Handling

**Algorithmus:**
1. Check BOM: UTF-8 BOM → UTF-8
2. Try UTF-8 strict decode
3. If fails: try Windows-1252 (ANSI)
4. If both fail: mark as `DVL-ENC-001` fatal

**Fix Option:**
- `--fix encoding`: Re-encode zu ANSI oder UTF-8 (configurable)
- Warnung bei Zeichenverlust (lossy)
- Audit log: replaced chars count + positions

#### Layer 2: Tokenizer (Streaming CSV)

**Muss unterstützen:**
- Semicolon delimiter
- Quoted fields
- Doubled quotes inside quoted fields
- Embedded CR/LF inside quotes

**Output:**
```python
(row_index, raw_line_span, tokens[])
# raw_line_span ist essenziell für exakte Report-Referenzen
```

#### Layer 3: Header Parser (Zeile 1)

```python
@dataclass(frozen=True)
class DatevHeader:
    kennzeichen: str         # "EXTF"
    header_version: int      # 700 / 510
    format_category: int     # 21 = Buchungsstapel
    format_name: str         # "Buchungsstapel"
    format_version: int      # 12
    created_at: datetime | None
    beraternummer: str | None      # ⚠️ IMMER string, nie int
    mandantennummer: str | None    # ⚠️ IMMER string, nie int
    fiscal_year_start: date | None
    period_from: date | None
    period_to: date | None
    account_length: int | None
    currency: str | None     # WKZ
    festschreibung: int | None  # 0/1
    raw_tokens: list[str]    # for roundtrip
```

#### Layer 4: Column Header Row (Zeile 2)

- Enthält Feldnamen (Spaltenüberschriften)
- Groß/Klein & Leerzeichen werden beim Abgleich ignoriert

**Mapping:**
- Canonical Field IDs: `umsatz`, `sh_kennz`, `konto`, `gegenkonto`, `bu_schluessel`, `belegdatum`
- Synonyme: "Soll/Haben-Kennzeichen" vs "Soll/Haben-Kz"

#### Layer 5: Row Parser + Typed Conversion

```python
@dataclass
class BookingRow:
    row_no: int
    line_span: tuple[int, int]      # start_line, end_line
    fields_raw: dict[str, str]      # ⚠️ IMMER original strings
    fields_typed: dict[str, Any]    # Derived, nie für Writeback
    checksum: str                   # stable hash
```

### 4.4 ⚠️ Type Conversion Rules (KRITISCH)

| Feld | Storage Type | Validation | Hinweis |
|------|--------------|------------|---------|
| **Konto** | `str` | `is_digits() + len <= account_length` | ⚠️ NIEMALS int (leading zeros!) |
| **Gegenkonto** | `str` | `is_digits() + len <= account_length` | ⚠️ NIEMALS int |
| **Beraternummer** | `str` | `is_digits()` | ⚠️ NIEMALS int |
| **Mandantennummer** | `str` | `is_digits()` | ⚠️ NIEMALS int |
| **Betrag** | `Decimal` | 2 Nachkommastellen | Komma als Dezimaltrennzeichen |
| **Belegdatum** | `PartialDate(TTMM)` | Siehe TTMM-Algorithmus | Jahr wird abgeleitet |
| **Belegfeld 1** | `str` | Regex + max 36 | Siehe Field Dictionary |

**Design-Regel:** Konten und IDs sind **Identifikatoren**, keine Zahlen. Sie werden als String gespeichert, validiert mit `is_digits()` und Längenprüfung. Ein `account_int` Derived Field ist optional für Sortierung, aber **niemals für Writeback**.

### 4.5 ⚠️ TTMM-Datum Algorithmus (KRITISCH)

Das Belegdatum im DATEV-Format ist TTMM (Tag+Monat) ohne Jahr. Der Algorithmus zur Jahresableitung muss **deterministisch** sein.

```python
def derive_year(
    ttmm: str,  # "0115" = 15. Januar
    fiscal_year_start: date | None,
    period_from: date | None,
    period_to: date | None
) -> DerivedDate:
    """
    Leitet das Jahr für ein TTMM-Datum ab.
    
    Returns:
        DerivedDate mit year, confidence, und ggf. warning
    """
    day = int(ttmm[0:2])
    month = int(ttmm[2:4])
    
    # Fall 1: period_from und period_to vorhanden
    if period_from and period_to:
        # Prüfe welches Jahr das Datum in den Zeitraum bringt
        candidates = []
        for year in [period_from.year, period_to.year]:
            try:
                candidate = date(year, month, day)
                if period_from <= candidate <= period_to:
                    candidates.append(year)
            except ValueError:
                pass  # Ungültiges Datum (z.B. 30.02)
        
        if len(candidates) == 1:
            return DerivedDate(year=candidates[0], confidence="high")
        elif len(candidates) == 2:
            # Ambig: Dez/Jan über Jahresgrenze
            return DerivedDate(
                year=candidates[0],  # Default: früheres Jahr
                confidence="ambiguous",
                warning="DVL-DATE-AMBIG-001"
            )
        else:
            return DerivedDate(
                year=None,
                confidence="failed",
                error="DVL-DATE-RANGE-001"
            )
    
    # Fall 2: Nur fiscal_year_start
    elif fiscal_year_start:
        # Ordne ins Wirtschaftsjahr ein
        # WJ 01.07.2024–30.06.2025: Juli-Dez → 2024, Jan-Juni → 2025
        if month >= fiscal_year_start.month:
            year = fiscal_year_start.year
        else:
            year = fiscal_year_start.year + 1
        return DerivedDate(year=year, confidence="medium")
    
    # Fall 3: Keine Ankerdaten
    else:
        return DerivedDate(
            year=None,
            confidence="unknown",
            warning="DVL-DATE-NOCTX-001"
        )
```

**Regeln für Findings:**
- `confidence="high"`: Kein Finding
- `confidence="ambiguous"`: WARN mit "Datum könnte 2024 oder 2025 sein"
- `confidence="medium"`: INFO (aus Wirtschaftsjahr abgeleitet)
- `confidence="failed"`: ERROR (Datum außerhalb Zeitraum)
- `confidence="unknown"`: WARN (keine Kontextdaten, Jahr nicht ableitbar)

### 4.6 Writer-Modi (Roundtrip vs Canonical)

**Problem:** "Minimale Diff-Writes" ist in CSV/Quoted/Newlines-Hölle schnell teuer.

**Lösung: Zwei Writer-Modi**

| Modus | Flag | Verhalten | Use Case |
|-------|------|-----------|----------|
| **preserve** | `--write-mode preserve` | Best-effort minimale Diffs, behält Original-Quoting/Whitespace wo möglich | Git-friendly, Review |
| **canonical** | `--write-mode canonical` | Deterministisch: standardisierte Quotes, CRLF, Encoding | Sauberer Output |

**Default:** `preserve` (User erwarten minimale Änderungen)

**Fallback:** Wenn `preserve` nicht garantiert werden kann (z.B. Encoding-Wechsel), automatischer Fallback auf `canonical` mit Warning.

```bash
# Beispiele
datev-lint fix file.csv --write-mode preserve  # Default
datev-lint fix file.csv --write-mode canonical # Normalisiert alles
```

**Garantien:**
- `canonical`: 100% deterministisch, identischer Input → identischer Output
- `preserve`: Best-effort, kann in Edge Cases auf canonical zurückfallen

---

## 5. Field Dictionary (Single Source of Truth)

Das Field Dictionary ist das **zentrale normative Artefakt** für Parser, Rules, Fixes und Docs.

### 5.1 Buchungsstapel Felder

| field_id | Header-Labels (Synonyme) | Pflicht | Type | Max Len | Charset | Fix Strategies |
|----------|--------------------------|---------|------|---------|---------|----------------|
| `umsatz` | "Umsatz", "Umsatz (ohne Soll/Haben-Kz)" | ✅ | Decimal | - | `0-9,` | `normalize_decimal` |
| `sh_kennz` | "Soll/Haben-Kennzeichen", "Soll/Haben-Kz", "S/H" | ✅ | Enum | 1 | `SH` | `map_value` |
| `konto` | "Konto", "Kontonummer" | ✅ | String | 9* | `0-9` | `truncate`, `pad_left` |
| `gegenkonto` | "Gegenkonto", "Gegen-Konto" | ✅ | String | 9* | `0-9` | `truncate`, `pad_left` |
| `bu_schluessel` | "BU-Schlüssel", "BU", "Steuerschlüssel" | ❌ | String | 4 | `0-9` | `lookup_suggest` |
| `belegdatum` | "Belegdatum", "Beleg-Datum" | ✅ | TTMM | 4 | `0-9` | `derive_year` |
| `belegfeld1` | "Belegfeld 1", "Belegnummer", "Rechnungsnr" | ❌** | String | 36 | `A-Z0-9_$&%*+\-/` | `sanitize_chars`, `truncate` |
| `belegfeld2` | "Belegfeld 2" | ❌ | String | 12 | `A-Z0-9_$&%*+\-/` | `sanitize_chars` |
| `buchungstext` | "Buchungstext", "Text" | ❌ | String | 60 | printable | `truncate` |
| `kostenstelle` | "Kostenstelle", "KOST1" | ❌ | String | 8 | `A-Z0-9` | `truncate` |
| `kostentraeger` | "Kostenträger", "KOST2" | ❌ | String | 8 | `A-Z0-9` | `truncate` |

*) Abhängig von Header `account_length`
**) Pflicht für OP-Verarbeitung

### 5.2 Charset Definitionen

| Charset ID | Pattern (Regex) | Beschreibung |
|------------|-----------------|--------------|
| `0-9` | `^[0-9]+$` | Nur Ziffern |
| `0-9,` | `^[0-9]+,[0-9]{2}$` | Dezimal mit Komma |
| `SH` | `^[SH]$` | Soll oder Haben |
| `A-Z0-9` | `^[A-Z0-9]+$` | Alphanumerisch uppercase |
| `A-Z0-9_$&%*+\-/` | `^[A-Z0-9_$&%*+\-/]*$` | Belegfeld-Zeichen (ASCII only!) |
| `printable` | `^[\x20-\x7E\xC0-\xFF]*$` | Druckbare Zeichen (ANSI) |

### 5.3 ⚠️ Belegfeld 1 Regex (KORRIGIERT)

**Problem in v2.0:** `\w` matcht Unicode-Wordchars → Umlaute gehen durch.

**Korrigierte Regex (ASCII-only):**

```yaml
# FALSCH (v2.0):
pattern: '^[\w$&%*+\-/]{0,36}$'  # ❌ \w matcht ä/ö/ü

# RICHTIG (v2.1):
pattern: '^[A-Za-z0-9_$&%*+\-/]{0,36}$'  # ✅ ASCII only

# STRIKT (uppercase only, empfohlen):
pattern: '^[A-Z0-9_$&%*+\-/]{0,36}$'  # ✅ + Fix: upper()
```

**Fix Strategy für Belegfeld 1:**
```yaml
fix:
  type: "sanitize"
  steps:
    - action: "upper"           # risk: low
    - action: "replace"         # risk: medium
      mapping:
        "ä": "AE"
        "ö": "OE"
        "ü": "UE"
        "ß": "SS"
        " ": ""
        ".": ""
        ",": ""
    - action: "truncate"        # risk: medium
      max_length: 36
  overall_risk: "medium"
  requires_approval: true
```

---

## 6. Rule Engine Design

### 6.1 Execution Pipeline (Stages)

| Stage | Zweck | Beispiele | Stop-on-fatal? |
|-------|-------|-----------|----------------|
| `parse` | Datei lesbar? | Encoding, CSV-Tokenisierung | ✅ |
| `header` | Header plausibel? | EXTF, Version, Kategorie=21 | ✅ |
| `schema` | Feldtypen & Pflichtfelder | Konto vorhanden, Betrag parsebar | ❌ |
| `row_semantic` | Zeilenlogik | Soll/Haben vs Betrag | ❌ |
| `cross_row` | Konsistenz über Zeilen | Doppelte Belegfeld 1, Summen | ❌ |
| `policy` | Mandantenspezifisch | Belegdatum im Zeitraum | optional |

### 6.2 Rule Definition Format

#### A) YAML DSL (80% der Regeln)

**Profile Beispiel (`profiles/skr03.yaml`):**

```yaml
profile:
  id: "de.skr03.default"
  version: "1.0.0"  # ⚠️ NEU: Versionierung
  label: "Deutschland SKR03 – Standard"
  base: "de.datev700.bookingbatch"
  overrides:
    severity:
      DVL-FIELD-011: "error"
    params:
      DVL-PERIOD-001:
        max_future_days: 0

rules:
  enable:
    - "DVL-*"
  disable:
    - "DVL-AT-*"
```

**Rule Beispiel (KORRIGIERT):**

```yaml
rules:
  - id: "DVL-FIELD-011"
    version: "1.0.0"  # ⚠️ NEU: Rule-Versionierung
    title: "Belegfeld 1 enthält unzulässige Zeichen"
    stage: "schema"
    severity: "error"
    applies_to: "row"
    selector:
      field: "belegfeld1"
    constraint:
      type: "regex"
      # ⚠️ KORRIGIERT: ASCII-only, keine Unicode-Wordchars
      pattern: '^[A-Z0-9_$&%*+\-/]{0,36}$'
    message:
      de: "Belegfeld 1 darf nur A-Z, 0-9 und _$&%*+-/ enthalten (max 36 Zeichen)."
    fix:
      type: "sanitize"
      steps:
        - action: "upper"
        - action: "replace"
          mapping:
            "ä": "AE"
            "ö": "OE"
            "ü": "UE"
            "ß": "SS"
            " ": ""
            ".": ""
      risk: "medium"
      requires_approval: true
```

#### B) Python Plugin Rules (komplexe Semantik)

```python
from datev_lint.api import Rule, Finding, Severity

class DuplicateBelegfeld1Rule(Rule):
    id = "DVL-CROSS-001"
    version = "1.0.0"  # ⚠️ NEU
    stage = "cross_row"
    severity = Severity.WARNING
    title = "Doppelte Belegfeld-1 Werte"

    def run(self, ctx, rows):
        seen = {}
        for r in rows:
            v = r.fields_raw.get("belegfeld1", "").strip()
            if not v:
                continue
            if v in seen:
                yield Finding(
                    code=self.id,
                    rule_version=self.version,  # ⚠️ NEU
                    severity=self.severity,
                    message=f"Belegfeld 1 '{v}' ist doppelt.",
                    location={"row_no": r.row_no},
                    related=[{"row_no": seen[v]}],
                    fix_candidates=[]
                )
            else:
                seen[v] = r.row_no
```

### 6.3 Rule/Profile Versioning (NEU)

Für Audit & Reproduzierbarkeit muss jede Validierung reproduzierbar sein.

**Versionierte Komponenten:**

| Komponente | Version Format | Beispiel |
|------------|----------------|----------|
| `engine_version` | SemVer | `1.2.3` |
| `ruleset_version` | SemVer | `1.0.0` |
| `profile_version` | SemVer | `1.0.0` |
| `plugin_versions` | Map | `{"sevdesk-pack": "2.1.0"}` |

**Finding enthält Rule-Version:**

```json
{
  "code": "DVL-FIELD-011",
  "rule_version": "1.0.0",
  "engine_version": "1.2.3",
  "profile_version": "1.0.0",
  ...
}
```

**Audit Log enthält alle Versionen:**

```json
{
  "run_id": "abc123",
  "timestamp": "2025-01-15T10:30:00Z",
  "versions": {
    "engine": "1.2.3",
    "ruleset": "1.0.0",
    "profile": "de.skr03.default@1.0.0",
    "plugins": {"sevdesk-pack": "2.1.0"}
  },
  "file_checksums": {...},
  "findings_summary": {...}
}
```

---

## 7. Exporter Fingerprinting & Auto-Profile (NEU)

### 7.1 Motivation

Setup-Friction reduzieren → mehr Adoption → mehr Conversions.

### 7.2 Fingerprint Detection

```python
@dataclass
class ExporterFingerprint:
    exporter_id: str           # z.B. "sevdesk", "lexware", "sage"
    confidence: float          # 0.0 - 1.0
    detected_by: list[str]     # Welche Signale
    suggested_profile: str     # z.B. "de.skr03.sevdesk.v2"
```

**Signale für Fingerprinting:**

| Signal | Gewicht | Beispiel |
|--------|---------|----------|
| Header-Felder (spezifische Positionen) | hoch | sevDesk setzt Feld 17 immer auf "0" |
| Spaltenreihenfolge | mittel | Lexware hat andere Reihenfolge als DATEV Standard |
| Typische Default-Werte | mittel | Sage: BU-Schlüssel immer 4-stellig |
| Dateiname-Pattern | niedrig | `EXTF_sevDesk_*.csv` |
| Encoding-Präferenz | niedrig | Manche Exporter immer UTF-8 |

### 7.3 CLI Integration

```bash
$ datev-lint validate buchungen.csv

🔍 Exporter erkannt: sevDesk (Konfidenz: 87%)
   Empfohlenes Profil: de.skr03.sevdesk.v2
   
   Verwende: datev-lint validate buchungen.csv --profile de.skr03.sevdesk.v2
   
   Oder mit Auto-Profil: datev-lint validate buchungen.csv --auto-profile
```

### 7.4 Moat-Implikation

- **Kostenlos:** Fingerprinting + Profil-Vorschlag
- **Paid:** Exporter-spezifische Rule Packs mit optimierten Fixes
- **Community:** "Bring deinen Exporter" → Fingerprint-Contributions

---

## 8. Error Taxonomy

### 8.1 Severity Levels

| Level | Bedeutung | CLI Exit Code | Rendering |
|-------|-----------|---------------|-----------|
| **FATAL** | Nicht verarbeitbar | 2 | 🔴 rot + abort |
| **ERROR** | Wahrscheinlich Import-Reject | 1 | 🔴 rot |
| **WARN** | Riskant / vermutlich Nacharbeit | 0 (config) | 🟡 gelb |
| **INFO** | Hinweis | 0 | 🔵 blau |
| **HINT** | Best Practice | 0 | ⚪ grau |

### 8.2 Error Codes

**Schema:** `DVL-{DOMAIN}-{NNN}`

| Domain | Beispiele |
|--------|-----------|
| `ENC` | Encoding/BOM |
| `CSV` | Delimiter/Quotes/Spaltenanzahl |
| `HDR` | Header Version/Kategorie/Zeitraum |
| `FIELD` | Feldlänge/Regex/Enum |
| `ROW` | Zeilenlogik Soll/Haben |
| `CROSS` | Dedupe, Summenabgleich |
| `DATE` | Datumsableitung (NEU) |
| `POL` | Mandanten-/Kanzlei-Policy |
| `FIX` | Fix-Apply/Conflict/Rollback |

### 8.3 Error Object (JSON/SARIF/API)

```json
{
  "code": "DVL-FIELD-011",
  "rule_version": "1.0.0",
  "severity": "ERROR",
  "title": "Belegfeld 1 enthält unzulässige Zeichen",
  "message": "Belegfeld 1 darf nur A-Z, 0-9 und _$&%*+-/ enthalten.",
  "location": {
    "file": "EXTF_Buchungsstapel.csv",
    "row_no": 3912,
    "field": "belegfeld1"
  },
  "context": {
    "raw_value": "RE-2025 001.1",
    "expected": "regex ^[A-Z0-9_$&%*+\\-/]{0,36}$"
  },
  "docs_url": "https://docs.datev-lint.dev/rules/DVL-FIELD-011",
  "fix": {
    "available": true,
    "risk": "medium",
    "requires_approval": true,
    "preview": "RE-2025001"
  }
}
```

---

## 9. Fix-Engine Architektur

### 9.1 Patch Operations

| Operation | Beschreibung |
|-----------|--------------|
| `set_field(row_no, field, new_value)` | Feldwert setzen |
| `normalize_decimal(row_no, field)` | Dezimalformat korrigieren |
| `truncate(row_no, field, max_len)` | Feld kürzen |
| `sanitize_chars(row_no, field, mapping)` | Zeichen ersetzen |
| `upper(row_no, field)` | Uppercase (NEU) |
| `insert_row(after_row_no, row)` | Zeile einfügen |
| `delete_row(row_no)` | Zeile löschen |
| `split_file(max_rows=99999)` | Datei aufteilen |

### 9.2 Apply Flow

```
User/CI
   │
   ▼
validate --fix --dry-run
   │
   ├──► Parser: parse + normalize
   ├──► Rule Engine: run rules
   ├──► Fix Engine: plan patches (detect conflicts)
   │
   ▼
Patch Plan + Diff Preview
   │
   ▼
--apply (or --yes)
   │
   ├──► Fix Engine: apply atomically (temp + rename)
   ├──► Backup + Audit Log (mit Versionen)
   ├──► Re-parse fixed file
   ├──► Re-run rules
   │
   ▼
Post-fix Summary + Exit Code
```

### 9.3 Rollback Mechanismus

1. **Vor Apply:** `original_path` → copy nach `original_path.bak.{timestamp}`
2. **Apply:** Schreibt in `original_path.tmp`, dann atomic rename
3. **Audit Log:** `audit/{run_id}.json` mit:
   - File checksum before/after
   - Patch list
   - **Alle Versionen** (engine, ruleset, profile, plugins)
   - License tier

**Rollback Command:**
```bash
datev-lint rollback --run-id <id>
# verify checksum matches "after"
# restore .bak
# write rollback audit entry
```

### 9.4 Fix Safety Model

| Risk Level | Beschreibung | Policy |
|------------|--------------|--------|
| **low** | Rein formatierend (BOM entfernen, Dezimalpunkt→Komma) | Auto-apply erlaubt |
| **medium** | Truncation, Uppercase, Umlaut-Ersetzung | Approval empfohlen |
| **high** | Semantikänderung (Belegfeld-IDs, OP-Referenzen) | `requires_approval: true` |

---

## 10. DATEV-Spezifika: Felder, Edge Cases, Profile

### 10.1 Kritische Felder (Buchungsstapel)

**Pflichtfelder:**
- Umsatz
- Soll/Haben-Kz
- Konto
- Gegenkonto
- Belegdatum

**Operativ kritisch (Import-Fails / große Folgekosten):**
- Konto, Gegenkonto (Länge/Typ, **als String speichern!**)
- BU-Schlüssel (USt-Logik)
- Belegdatum (TTMM / Zeitraum / Jahreszuordnung)
- Belegfeld 1 (OP-Schlüssel, max 36 Zeichen, **ASCII-only!**)
- Header: Zeitraum (Feld15/16), Kategorie 21, Kennzeichen EXTF

### 10.2 Gemeine Fallstricke (Edge Cases)

| Edge Case | Problem | Regel |
|-----------|---------|-------|
| **Belegdatum ohne Jahr** | TTMM, Jahr wird abgeleitet | `derive_year()` Algorithmus (siehe 4.5) |
| **CR vs LF** | CR = Record-Ende, LF kann in Text vorkommen | Tokenizer toleriert LF in Quotes |
| **Belegfeld-Längen** | v5.1 = 12 Zeichen, v7.0 = 36 Zeichen | Regeln berücksichtigen Header-Version |
| **Stapelgröße** | Max 99.999 Buchungssätze | Pro-Fix: Split in mehrere Dateien |
| **Leading Zeros** | Konto "0001234" → "1234" bei int | **Konto als String speichern!** |

### 10.3 SKR03 vs SKR04 vs AT (RLG)

| Dimension | SKR03 | SKR04 | AT (RLG) |
|-----------|-------|-------|----------|
| Kontenrahmen | Prozess-/Ablauforientiert | Bilanz-/Abschlussorientiert | Eigener Kontenplan |
| Konto-Validierung | Andere Nummernbereiche | Andere Nummernbereiche | Landesspezifisch |
| Automatik-Konten (USt) | Verbreitet | Verbreitet | AT Import-Logik |
| Profile Default | `de.skr03.*` | `de.skr04.*` | `at.*` |

**Konsequenz:**
- Kontenrahmen-Regeln nicht hart-coden
- Built-in: Heuristiken + Strukturchecks (Länge, `is_digits()`)
- **Paid Add-on:** Exporter Packs mit validierten Konten-Maps

---

## 11. CLI-Interface

### 11.1 Commands

```bash
# Validate
datev-lint validate EXTF_Buchungsstapel.csv \
  --profile de.skr03.default \
  --format terminal

datev-lint validate EXTF_Buchungsstapel.csv \
  --auto-profile \  # NEU: Auto-Detection
  --format json \
  --out findings.json \
  --fail-on error

# Fix
datev-lint fix EXTF_Buchungsstapel.csv \
  --profile de.skr03.default \
  --dry-run \
  --write-mode preserve  # NEU: Writer-Modus

datev-lint fix EXTF_Buchungsstapel.csv \
  --profile de.skr03.default \
  --yes --accept-risk medium \
  --write-mode canonical  # NEU

# Report
datev-lint report EXTF_Buchungsstapel.csv \
  --profile de.skr03.default \
  --format pdf \
  --out report.pdf

# Utilities
datev-lint profiles list
datev-lint rules list --profile de.skr03.default
datev-lint explain DVL-FIELD-011
datev-lint fingerprint EXTF_Buchungsstapel.csv  # NEU
```

### 11.2 Exit Codes

| Code | Bedeutung |
|------|-----------|
| 0 | Keine ERROR/FATAL |
| 1 | Mind. 1 ERROR (oder WARN wenn `--fail-on warn`) |
| 2 | FATAL (Parsing/Format) |

### 11.3 Output Formate

| Format | Beschreibung | Tier |
|--------|--------------|------|
| Terminal (Rich) | Colored output | Free |
| JSON | Maschinenlesbar | Free |
| SARIF | GitHub Code Scanning | Free (basic) |
| JUnit XML | CI | Pro |
| PDF/HTML Report | Steuerberater-Kommunikation | Pro |

---

## 12. Reporting Engine

### 12.1 Report Inhalte

1. **Header Summary:** Berater/Mandant, Zeitraum, Version, Encoding, Zeilenanzahl
2. **Version Info:** Engine, Ruleset, Profile, Plugins (NEU)
3. **Findings Summary:** Count nach Severity + Top Codes
4. **Detail Pages:** Pro Finding:
   - Kontextzeile (Row excerpt)
   - Erklärung (DE)
   - Fix Vorschlag + Risiko
5. **Diff Appendix:** (bei Fix) Patch list + Checksums

### 12.2 Performance

- Report-Generierung ≤ 5s für 50k Zeilen

---

## 13. Monetarisierungs-Architektur

### 13.1 Lizenzmodell (technisch)

**Hybrid-Modell:**

1. **Signed License File (offline):**
   - JSON payload: `tier`, `expiry`, `seats`, `org_id`, `features`
   - Signiert (Ed25519) durch License Server
   - CLI verifiziert Signatur lokal (kein Always-Online)

2. **Optional Online Check-in (Pro/Team/Enterprise):**
   - 1×/24h Telemetrie "heartbeat" (keine Buchungsdaten)
   - Nutzung: counts, tool-version, anonymisierte rule-codes

3. **Feature Flags:**
   - Aus License payload: `features: ["fix_engine", "pdf_report", "sarif", "ci", "webhooks"]`

### 13.2 ⚠️ Packaging-Entscheidung (KRITISCH)

**Problem:** Wie lieferst du Paid Features aus, wenn der Kern OSS ist?

**Entscheidung: Plugin-Modell**

```
┌─────────────────────────────────────────┐
│  datev-lint (OSS)                       │
│  - Parser Core                          │
│  - 30 Baseline Rules                    │
│  - JSON/Terminal Output                 │
│  - Profile Mechanism                    │
│  - Fix dry-run                          │
└─────────────────┬───────────────────────┘
                  │
                  │ Plugin Interface
                  │
┌─────────────────▼───────────────────────┐
│  datev-lint-pro (Closed Source)         │
│  - Fix apply Engine                     │
│  - PDF/HTML Reports                     │
│  - Advanced Rule Packs                  │
│  - Splitter (>99,999)                   │
│  - SARIF full / JUnit                   │
└─────────────────────────────────────────┘
```

**Distribution:**
- `datev-lint` (OSS): PyPI public
- `datev-lint-pro` (Closed): Private PyPI / GitHub Releases
- License File schaltet Pro-Plugin frei

**Warum Plugin statt separater Build:**
- Einfachere Installation: `pip install datev-lint datev-lint-pro`
- Klare Trennung: OSS bleibt vollständig nutzbar
- Patch-Resistenz: Pro-Code nicht im OSS-Repo

### 13.3 Telemetrie (DACH-tauglich)

**Defaults:**
- **Opt-in** bei erstem Run (Prompt)
- Oder: `--telemetry=off` / `DATEV_LINT_TELEMETRY=0`

**Was wir sammeln:**
- File size bucket (<10k, 10–100k, 100k–1M, >1M)
- Enabled profile id
- Count findings per code/severity (aggregiert)
- Runtime metrics
- Tool version

**Was wir NIE sammeln:**
- Buchungstexte
- Kontonummern
- Belegnummern
- Rohdaten
- IP-Adressen (wenn möglich)

**Dokumentation:**
- `/docs/telemetry.md`: "What we collect / What we never collect"
- Link in CLI bei Opt-in Prompt

### 13.4 Feature Matrix

| Feature | Free (OSS) | Pro | Team | Enterprise |
|---------|------------|-----|------|------------|
| Validate core (30 rules) | ✅ | ✅ | ✅ | ✅ |
| JSON output | ✅ | ✅ | ✅ | ✅ |
| Exporter Fingerprinting | ✅ | ✅ | ✅ | ✅ |
| Auto-Fix apply | ❌ (nur dry-run) | ✅ | ✅ | ✅ |
| PDF/HTML Reports | ❌ | ✅ | ✅ | ✅ |
| Rule Profiles (built-in) | ✅ (basic) | ✅ (advanced) | ✅ | ✅ |
| CI outputs (SARIF/JUnit) | ✅ (basic) | ✅ (full) | ✅ | ✅ |
| Shared profiles + audit log | ❌ | ❌ | ✅ | ✅ |
| API (validate/fix/report) | ❌ | ❌ | limited | ✅ |
| On-Prem, SLA, SSO, custom rules | ❌ | ❌ | ❌ | ✅ |

### 13.5 Pricing

| Tier | Preis | Zielgruppe |
|------|-------|------------|
| **Free / OSS** | €0 | Developers, Evaluators |
| **Pro** | €29/Monat | KMU Buchhaltung |
| **Team** | €79/Monat | Steuerberater (5 User) |
| **Enterprise** | Custom | Software-Anbieter, Konzerne |

---

## 14. Enterprise API Design

### 14.1 Use Cases

- ERP exportiert EXTF → ruft validate → blockiert Versand wenn errors
- Kanzlei-Workflow: Upload ZIP → Report + Webhook an Slack/Teams
- OEM: Integrierte Validierung im Export Wizard
- **DATEV API Integration:** "Pre-validate before DATEV accounting:extf-files upload"

### 14.2 REST Endpoints (v1)

```
POST /v1/jobs/validate
  Body: profile_id, options, file upload (multipart)

POST /v1/jobs/fix
  Body: profile_id, fix_policy, file

GET  /v1/jobs/{id}
  Response: status, progress, results, versions

GET  /v1/jobs/{id}/artifact
  Response: fixed file / report

GET  /v1/profiles
POST /v1/profiles (Team+)

POST /v1/webhooks (Team+)

GET  /v1/audit (Team+)
```

### 14.3 Job Processing

- Async by default (large files)
- Synchronous nur für kleine Payloads
- Queue: Redis + worker pool (FastAPI + RQ/Celery/Arq)
- **SLA (Enterprise):** 99.9% monthly

---

## 15. Erweiterungspunkte

### 15.1 Plugin-System für Community Rules

**Mechanik:**
- Python entry points: `datev_lint.rules` und `datev_lint.fixes`
- Plugin manifest mit metadata: compatibility, profile suggestions, license flags

**Security:**
- Plugins laufen als Code → Risiko
- Enterprise: Optional "sandbox mode" (nur YAML rules) oder signierte Plugins

### 15.2 Integration Points (Priorisierung)

**Priorität 1 (Early Revenue):**
- sevDesk (DATEV Export + "Steuerberater-Workflow")
- Lexware (breite KMU-Basis)
- Sage

**Priorität 2 (AT / Mid-Market):**
- BMD (AT)
- dvo/AT Import-Welt

**Priorität 3 (OEM/Enterprise):**
- Microsoft Dynamics BC / NAV
- SAP (ByDesign)
- Odoo

### 15.3 CI/CD Integration

```yaml
# GitHub Action
- uses: datev-lint/action@v1
  with:
    profile: de.skr03.default
    fail-on: error
```

### 15.4 Webhooks (Team+)

**Events:**
- `validation.completed`
- `fix.completed`
- `report.generated`
- `policy.violation`

**Targets:** Slack, MS Teams, Email, generic webhook

---

## 16. Performance-Anforderungen

### 16.1 Baseline Hardware

"Typical accounting laptop": 8 cores, 16 GB RAM, SSD

### 16.2 Throughput Ziele

| Operation | MVP | 12 Monate |
|-----------|-----|-----------|
| Parse (CSV decode + tokenize) | ≥ 50k Zeilen/s | ≥ 120k Zeilen/s |
| Validate (30 rules, row-level) | ≥ 20k Zeilen/s | ≥ 60k Zeilen/s |
| Cross-row (duplicates, sums) | 1M rows ≤ 30s | 1M rows ≤ 15s |

### 16.3 Memory Constraints

| Datenmenge | Max Memory |
|------------|------------|
| 50k Zeilen | < 200 MB |
| 1M Zeilen | < 1.2 GB |

**Optimierung:** Bloom filters, streaming aggregates, partial materialization

### 16.4 Big File Modes

- `--mode fast`: Weniger Kontext, keine full row snapshots
- `--mode strict`: Volle Checks + richer context (langsamer)

---

## 17. Roadmap: 14 Wochen Sprint Plan

| Woche | Ziel | Deliverables | Definition of Done | Dependencies |
|-------|------|--------------|-------------------|--------------|
| 1 | Parser Skeleton + **Sample Files** | Detector + Encoding + Header + Row parse + **10 reale Files** | 3 Golden Files, Parser tolerant, **Compatibility Matrix v0.1** | DATEV samples |
| 2 | Core Rules v1 | 15 Regeln, Error taxonomy, CLI validate, **Field Dictionary v1** | Stable error codes, exit codes | Parser v0 |
| 3 | Core Rules v2 | 30 Regeln inkl. Belegfeld, Konto, Datum, **TTMM-Algorithmus** | 20 Golden negative tests | Woche 2 |
| 4 | Rule Engine DSL | YAML rules + profiles + **Versionierung** | Profile load, enable/disable | Woche 2–3 |
| 5 | Fix Engine v1 | dry-run patches + diff preview + **Writer-Modi** | Patch planner, conflict detection | Rule engine |
| 6 | Monetize Early | License verification + **Pro Plugin** + Pro gating | Paid flow end-to-end testbar | Fix v1 |
| 7 | Reporting v1 | HTML + PDF report (Pro) | 50k rows report <5s | Week 6 |
| 8 | CI Outputs + **Fingerprinting** | SARIF + JUnit + --fail-on + **Auto-Profile** | GitHub Action example | Week 2 |
| 9 | Web UI Thin Slice | FastAPI upload → validate → report | Docker image, auth stub | Core stable |
| 10 | Batch + ZIP | Multiple files / zip bundle | Artifacts output + summary | Parser multi-file |
| 11 | Team Features v1 | Shared profiles + audit log (SaaS) | Multi-tenant db, RBAC | Web UI |
| 12 | Webhooks | Webhook system + retries | At-least-once delivery | Week 11 |
| 13 | Enterprise API v1 | /jobs validate/fix/report + tokens | Rate limits, async jobs | Week 9–12 |
| 14 | Hardening | Perf profiling, security, docs, **Telemetrie-Docs** | 1st paid customers | Everything |

### Kritischer Pfad zum ersten zahlenden Kunden

**Woche 1–6 = "Money Path":**
1. **Sample Files** (Woche 1) ← Echter kritischer Pfad!
2. Parser solide + Field Dictionary
3. 30 Regeln + TTMM-Algorithmus
4. Fix dry-run + diff + Writer-Modi
5. Fix apply (Pro Plugin)
6. Lizenzierung + Checkout

---

## 18. MoSCoW Feature-Liste

### Must (MVP-relevant, zahlungsfähig)

- [ ] Parser: EXTF header + Buchungsstapel rows, Encoding (ANSI/UTF-8), robust CSV
- [ ] **Field Dictionary** als Single Source of Truth
- [ ] 30 Core Regeln (parse/header/schema/row_semantic)
- [ ] **TTMM-Algorithmus** deterministisch
- [ ] Error taxonomy + stabile Error Codes + **Rule Versioning**
- [ ] JSON output + exit codes
- [ ] Profiles: SKR03/SKR04/AT-baseline
- [ ] Fix engine: dry-run + diff + apply (Pro) + **Writer-Modi**
- [ ] Backup + audit log + rollback command
- [ ] License system (offline signed) + **Pro Plugin Distribution**
- [ ] **Telemetrie opt-in + Dokumentation**

### Should (schnell hoher Wert)

- [ ] PDF/HTML Reports (Pro)
- [ ] SARIF + JUnit outputs
- [ ] **Exporter Fingerprinting + Auto-Profile**
- [ ] Zip/batch validation
- [ ] "Split batch >99,999" Fix (Pro)
- [ ] Web UI thin slice

### Could (Differenzierung / Growth)

- [ ] Rule marketplace (signed rule packs)
- [ ] Webhooks/Slack/Teams
- [ ] ERP-specific packs (sevDesk/Lexware/Sage/BMD)
- [ ] "Explain with AI" (opt-in, redacted fields)

### Won't (jetzt nicht)

- [ ] Vollständige Buchhaltungssoftware ersetzen
- [ ] Vollautomatische Kontenrahmen-Abstimmung ohne User-input

---

## 19. Technische Akzeptanzkriterien MVP

### Parser Robustness

- [ ] Kann EXTF mit Header (Zeile 1) + Spaltenheader (Zeile 2) + 50k rows verarbeiten
- [ ] Embedded line breaks in quoted text lösen keinen Row-Shift aus
- [ ] Erkennt UTF-8 BOM, UTF-8, Windows-1252
- [ ] **Konto/Gegenkonto als String (keine leading zero loss)**
- [ ] **TTMM-Algorithmus implementiert mit Konfidenz-Levels**

### Rules

- [ ] ≥ 30 Regeln:
  - ≥ 10 structural/schema
  - ≥ 10 field constraints (**korrigierte Regex!**)
  - ≥ 5 semantic
  - ≥ 5 cross-row
- [ ] Mindestens 10 Regeln haben konkrete "how to fix" Hinweise
- [ ] **Alle Rules haben Version**

### Fix Engine

- [ ] `--dry-run` erzeugt Patch Plan + Unified Diff
- [ ] `--apply` schreibt atomisch, erzeugt Backup
- [ ] **Writer-Modi: preserve (default) und canonical**
- [ ] `rollback` stellt Backup wieder her
- [ ] Re-validate nach apply
- [ ] **Audit Log enthält alle Versionen**

### Outputs

- [ ] Terminal + JSON
- [ ] Exit codes korrekt
- [ ] Machine-readable error objects **mit rule_version**

### Performance

- [ ] 50k rows validate ≤ 2s
- [ ] 1M rows validate ≤ 60s (fast mode)
- [ ] **CI-Gate: Regression > 10% = Build fail**

### Monetization

- [ ] **Pro Plugin separat distributed**
- [ ] Pro License schaltet fix apply frei
- [ ] Ohne License: `fix --dry-run` erlaubt, `fix --apply` blockt mit CTA
- [ ] **Telemetrie opt-in mit Dokumentation**

---

## 20. Externe Dependencies

### Open Source Libraries

| Library | Zweck |
|---------|-------|
| Typer + Rich | CLI UX |
| Polars/Pandas | Data ops |
| Jinja2 + WeasyPrint | Reports |
| charset-normalizer | Encoding detect |
| cryptography | Ed25519 verify |
| pydantic | Typed configs & API |

### Commercial / SaaS (später)

- Stripe / LemonSqueezy (billing)
- PostHog (privacy-friendly product analytics)
- Sentry (crash reporting)

### DATEV APIs (Enterprise)

- DATEV "accounting:extf-files" API für Upload
- → Enterprise Play: "validated before upload"

---

## 21. Test-Strategie

### 21.1 Golden File Tests

```
tests/fixtures/golden/
├── valid_minimal_700_10rows.csv
├── invalid_encoding.csv
├── broken_quotes.csv
├── wrong_delimiter.csv
├── invalid_belegfeld_chars.csv
├── leading_zero_konto.csv          # NEU
├── ttmm_ambiguous_date.csv         # NEU
├── ttmm_cross_year.csv             # NEU
└── large_file_generator.py
```

**Golden outputs:**
- JSON findings snapshot
- Terminal snapshot (optional)
- Fixed file snapshot

### 21.2 Unit Tests

- Tokenizer state machine edge cases
- Type conversions (decimal comma, TTMM)
- **TTMM derive_year() alle Fälle**
- Patch planner conflict detection
- **Writer-Modi preserve vs canonical**

### 21.3 Integration Tests

- End-to-end: validate → fix dry-run → fix apply → revalidate
- Profile overrides (severity/params)
- Multi-file ZIP flows
- **Exporter Fingerprinting accuracy**

### 21.4 Property-Based / Fuzz

- Fuzz CSV mit random quotes/semicolons/newlines
- Must not crash, must produce FATAL with stable code

### 21.5 Performance Regression Tests

- Golden perf fixtures (10k, 50k, 100k, 1M)
- CI gate: fail if regression > 10%

---

## 22. Competitive Moat

### 22.1 Warum nicht kopierbar in 3 Monaten?

| Moat | Beschreibung |
|------|--------------|
| **Golden Corpus** | Ständig wachsende Sammlung anonymisierter Exportprobleme + Exporter Fingerprints |
| **Exporter Fingerprinting** | Auto-Profile reduziert Setup-Friction (NEU) |
| **Rule Packs** | Pro Exporter / Kanzlei-Policy Packs (bezahlbar, spart Supportkosten) |
| **CI/DevTool Integration** | "Fail build if DATEV export breaks" |
| **Auditierbarer Fix-Chain** | Backup + patch logs + **versionierte** diffs = Vertrauensvorteil |

### 22.2 Open-Source Strategie

**OSS (für Adoption):**
- Parser core
- Baseline rules (30)
- JSON output
- Profile mechanism (basic profiles)
- Exporter Fingerprinting
- Fix dry-run

**Proprietär (für Umsatz) via `datev-lint-pro` Plugin:**
- Fix apply engine
- PDF reports
- Splitter (>99,999)
- Advanced exporter packs
- Full SARIF/JUnit
- SaaS team features
- Enterprise API + SLA

### 22.3 Community Building

- Public "Rule RFCs" (wie PEPs)
- "Exporter Support Matrix" im README
- Bounties: "Bring a broken file → get Pro 6 months"
- **Fingerprint Contributions** für neue Exporter

---

## Appendix A: MVP Rule Set (Startliste)

### Parse/Header (Fatal)

| Code | Beschreibung |
|------|--------------|
| `DVL-ENC-001` | Encoding unknown/unreadable |
| `DVL-CSV-001` | Delimiter mismatch / malformed quotes |
| `DVL-HDR-001` | Missing EXTF / wrong format category (≠21) |

### Schema

| Code | Beschreibung |
|------|--------------|
| `DVL-FIELD-001` | Pflichtfeld missing (Umsatz, Konto, Gegenkonto, Belegdatum) |
| `DVL-FIELD-002` | Konto/Gegenkonto length invalid vs Header account length |
| `DVL-FIELD-003` | Betrag decimal normalization (dot vs comma) |
| `DVL-FIELD-011` | Belegfeld 1 unzulässige Zeichen (**ASCII-only Regex!**) |

### Datum (NEU)

| Code | Beschreibung |
|------|--------------|
| `DVL-DATE-AMBIG-001` | TTMM-Datum ambig (könnte 2 Jahre sein) |
| `DVL-DATE-RANGE-001` | Datum außerhalb Header-Zeitraum |
| `DVL-DATE-NOCTX-001` | Keine Kontextdaten für Jahresableitung |

### Semantik

| Code | Beschreibung |
|------|--------------|
| `DVL-ROW-001` | Soll/Haben Kennzeichen inconsistent |
| `DVL-HDR-PRD-001` | Belegdatum outside header period |

### Cross-row

| Code | Beschreibung |
|------|--------------|
| `DVL-CROSS-001` | Duplicate Belegfeld 1 |
| `DVL-CROSS-002` | Row count > 99,999 |

---

## Appendix B: Haftungs-Disclaimer (Template)

```
HAFTUNGSAUSSCHLUSS

datev-lint ist ein Validierungs- und Korrekturvorschlagstool. 
Die automatischen Korrekturen ("Fixes") sind VORSCHLÄGE und 
ersetzen keine fachliche Prüfung.

Der Nutzer ist verantwortlich für:
- Die Prüfung aller vorgeschlagenen Korrekturen vor Anwendung
- Die Sicherung der Originaldaten
- Die finale Freigabe der korrigierten Dateien

Der Anbieter haftet nicht für:
- Fehlerhafte Buchungen durch angewandte Fixes
- Steuerliche oder rechtliche Konsequenzen
- Datenverlust (obwohl Backups automatisch erstellt werden)

Durch Nutzung von --fix --apply bestätigt der Nutzer, dass er 
die vorgeschlagenen Änderungen geprüft und akzeptiert hat.
```

---

*datev-lint Product Specification v2.1 | Confidential*

*Changelog v2.1:*
- *Regex Belegfeld 1 korrigiert (ASCII-only)*
- *Konto/Gegenkonto als String (nie int)*
- *TTMM-Algorithmus deterministisch spezifiziert*
- *Writer-Modi preserve/canonical definiert*
- *Packaging-Entscheidung: Pro als Plugin*
- *Field Dictionary als Single Source of Truth*
- *Exporter Fingerprinting + Auto-Profile*
- *Rule/Profile Versioning für Audit*
- *Telemetrie DACH-tauglich (opt-in)*
- *Performance-Messmethodik + CI-Gate*
- *Haftungs-Disclaimer Template*
