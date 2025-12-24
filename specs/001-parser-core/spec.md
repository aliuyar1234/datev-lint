# Feature Specification: Parser Core

**Feature Branch**: `001-parser-core`
**Created**: 2025-12-24
**Status**: Draft
**Input**: Product Specification v2.1 - Sections 4 (Parser-Architektur), 5 (Field Dictionary)

## User Scenarios & Testing

### User Story 1 - Parse Valid DATEV Export (Priority: P1)

Als Buchhalter möchte ich eine DATEV-Exportdatei (EXTF) laden können, damit ich sie validieren kann.

**Why this priority**: Ohne Parser funktioniert nichts. Dies ist das absolute Fundament.

**Independent Test**: Eine gültige EXTF-Datei mit 100 Zeilen kann geladen werden und liefert strukturierte Daten zurück.

**Acceptance Scenarios**:

1. **Given** eine gültige EXTF_Buchungsstapel.csv mit Header Version 700, **When** ich die Datei parse, **Then** erhalte ich ein `DatevHeader`-Objekt mit allen Pflichtfeldern und eine Liste von `BookingRow`-Objekten.
2. **Given** eine EXTF-Datei mit Windows-1252 Encoding, **When** ich die Datei parse, **Then** werden Umlaute (ä, ö, ü, ß) korrekt erkannt.
3. **Given** eine EXTF-Datei mit UTF-8 BOM, **When** ich die Datei parse, **Then** wird das BOM erkannt und die Datei korrekt gelesen.

---

### User Story 2 - Handle Encoding Variations (Priority: P1)

Als Entwickler möchte ich, dass der Parser verschiedene Encodings automatisch erkennt, damit Dateien aus verschiedenen Exportern funktionieren.

**Why this priority**: Encoding-Fehler sind die häufigste Fehlerursache bei DATEV-Importen.

**Independent Test**: Dateien in UTF-8, UTF-8-BOM und Windows-1252 werden alle korrekt geparst.

**Acceptance Scenarios**:

1. **Given** eine Datei mit UTF-8 BOM (EF BB BF), **When** Encoding Detection läuft, **Then** wird UTF-8 erkannt.
2. **Given** eine Datei ohne BOM mit gültigen UTF-8 Bytes, **When** Encoding Detection läuft, **Then** wird UTF-8 erkannt.
3. **Given** eine Datei mit Windows-1252 spezifischen Bytes (0x80-0x9F Range), **When** UTF-8 Decode fehlschlägt, **Then** Fallback auf Windows-1252.
4. **Given** eine Datei mit ungültigem Encoding, **When** beide Decodings fehlschlagen, **Then** wird `DVL-ENC-001` FATAL Error erzeugt.

---

### User Story 3 - Parse DATEV Header (Priority: P1)

Als Validator möchte ich den DATEV-Header (Zeile 1) strukturiert auslesen, damit ich Metadaten wie Version, Zeitraum und Mandant kenne.

**Why this priority**: Header-Informationen steuern die Validierungslogik (z.B. Kontenlänge, Zeitraum).

**Independent Test**: Header-Zeile wird in typisiertes `DatevHeader`-Objekt konvertiert.

**Acceptance Scenarios**:

1. **Given** Header mit `EXTF;700;21;Buchungsstapel;12;...`, **When** Header geparst wird, **Then** `header_version=700`, `format_category=21`, `format_version=12`.
2. **Given** Header mit Beraternummer "0012345", **When** Header geparst wird, **Then** `beraternummer="0012345"` (String, nicht int!).
3. **Given** Header mit Zeitraum 01.01.2025-31.12.2025, **When** Header geparst wird, **Then** `period_from` und `period_to` sind korrekte `date`-Objekte.
4. **Given** Header ohne EXTF-Kennzeichen, **When** Header geparst wird, **Then** `DVL-HDR-001` FATAL Error.

---

### User Story 4 - Tokenize CSV with DATEV Conventions (Priority: P1)

Als Parser möchte ich CSV-Zeilen korrekt tokenisieren (Semikolon, Quotes, Escaped Quotes), damit auch komplexe Buchungstexte funktionieren.

**Why this priority**: DATEV-CSV hat Sonderregeln (Semikolon statt Komma, CR als Record-Ende).

**Independent Test**: Zeile mit Quoted Fields und Embedded Newlines wird korrekt in Tokens zerlegt.

**Acceptance Scenarios**:

1. **Given** Zeile `"Feld1";"Feld2";"Feld3"`, **When** tokenisiert, **Then** 3 Tokens ohne Quotes.
2. **Given** Zeile mit `"Text mit ""Anführungszeichen"""`, **When** tokenisiert, **Then** Token enthält `Text mit "Anführungszeichen"`.
3. **Given** Zeile mit embedded LF in Quotes `"Zeile1\nZeile2"`, **When** tokenisiert, **Then** ein Token mit Newline.
4. **Given** Zeile mit unbalanced Quotes, **When** tokenisiert, **Then** `DVL-CSV-001` Error mit Zeilennummer.

---

### User Story 5 - Parse Booking Rows with Type Safety (Priority: P1)

Als Validator möchte ich Buchungszeilen in typisierte Objekte konvertieren, wobei Kontonummern als Strings erhalten bleiben.

**Why this priority**: Type Safety für Identifikatoren verhindert Leading-Zero-Verlust.

**Independent Test**: Konto "0001234" bleibt nach Parsing "0001234" (nicht 1234).

**Acceptance Scenarios**:

1. **Given** Buchungszeile mit Konto "0001234", **When** Row geparst wird, **Then** `fields_raw["konto"] == "0001234"`.
2. **Given** Buchungszeile mit Betrag "1234,56", **When** Row geparst wird, **Then** `fields_typed["umsatz"] == Decimal("1234.56")`.
3. **Given** Buchungszeile mit Belegdatum "1503" (TTMM), **When** Row geparst wird, **Then** `fields_raw["belegdatum"] == "1503"` und Jahr wird später abgeleitet.
4. **Given** Buchungszeile mit fehlendem Pflichtfeld, **When** Row geparst wird, **Then** Row enthält `None` für fehlendes Feld (Validierung kommt später).

---

### User Story 6 - TTMM Date Year Derivation (Priority: P2)

Als Validator möchte ich das Jahr für TTMM-Datumsangaben deterministisch ableiten, damit Buchungsdaten korrekt zugeordnet werden.

**Why this priority**: Falsche Jahreszuordnung führt zu falschen Buchungsperioden.

**Independent Test**: TTMM "0115" mit Zeitraum 01.01.2025-31.12.2025 ergibt 15.01.2025.

**Acceptance Scenarios**:

1. **Given** TTMM "1503" mit period_from=2025-01-01 und period_to=2025-12-31, **When** Jahr abgeleitet wird, **Then** `year=2025`, `confidence="high"`.
2. **Given** TTMM "0101" mit period_from=2024-12-01 und period_to=2025-01-31, **When** Jahr abgeleitet wird, **Then** `year` ist ambig → `confidence="ambiguous"`, Warning `DVL-DATE-AMBIG-001`.
3. **Given** TTMM "1507" mit period_from=2025-01-01 und period_to=2025-03-31, **When** Datum außerhalb Zeitraum, **Then** `confidence="failed"`, Error `DVL-DATE-RANGE-001`.
4. **Given** TTMM ohne Kontextdaten (kein period_from/to), **When** Jahr nicht ableitbar, **Then** `confidence="unknown"`, Warning `DVL-DATE-NOCTX-001`.

---

### User Story 7 - Stream Large Files (Priority: P2)

Als Buchhalter mit großen Exporten (100k+ Zeilen) möchte ich, dass der Parser streaming-fähig ist, damit mein System nicht abstürzt.

**Why this priority**: Performance-Anforderung aus Constitution (1M Zeilen ≤ 1.2GB RAM).

**Independent Test**: 1M-Zeilen-Datei wird mit < 1.2GB RAM Peak geparst.

**Acceptance Scenarios**:

1. **Given** Datei mit 1M Buchungszeilen, **When** geparst mit Iterator-API, **Then** Memory Peak < 1.2GB.
2. **Given** Datei mit 50k Zeilen, **When** vollständig geparst, **Then** Parse-Zeit ≤ 1s.
3. **Given** Streaming Parser, **When** Zeile 500.000 fehlerhaft, **Then** Error enthält exakte Zeilennummer.

---

### Edge Cases

- Was passiert bei einer leeren Datei (0 Bytes)?
- Wie verhält sich der Parser bei Dateien mit nur Header (keine Daten)?
- Was passiert bei Dateien mit mehr als 99.999 Zeilen?
- Wie werden NULL-Bytes in der Datei behandelt?
- Was passiert bei sehr langen Zeilen (> 10.000 Zeichen)?

## Requirements

### Functional Requirements

- **FR-001**: Parser MUSS Encoding automatisch erkennen (UTF-8 BOM, UTF-8, Windows-1252)
- **FR-002**: Parser MUSS DATEV-Header (Zeile 1) in typisiertes `DatevHeader`-Objekt konvertieren
- **FR-003**: Parser MUSS Spaltenüberschriften (Zeile 2) auf kanonische Field-IDs mappen
- **FR-004**: Parser MUSS Buchungszeilen (Zeile 3+) in `BookingRow`-Objekte konvertieren
- **FR-005**: Parser MUSS Konto/Gegenkonto/Beraternummer/Mandantennummer als String speichern (nie int)
- **FR-006**: Parser MUSS TTMM-Datum Jahr ableiten mit dokumentiertem Algorithmus
- **FR-007**: Parser MUSS CSV-Sonderzeichen korrekt behandeln (Semikolon, Quotes, Escaped Quotes, Embedded Newlines)
- **FR-008**: Parser MUSS Streaming-fähig sein (Iterator-API für große Dateien)
- **FR-009**: Parser MUSS Raw-Token-Liste für Roundtripping erhalten
- **FR-010**: Parser MUSS bei Fehlern strukturierte Error-Objekte mit Zeilennummer erzeugen

### Key Entities

- **DatevHeader**: Metadaten aus Zeile 1 (Version, Kategorie, Zeitraum, Berater/Mandant)
- **BookingRow**: Eine Buchungszeile mit `row_no`, `line_span`, `fields_raw`, `fields_typed`, `checksum`
- **DetectedFormat**: Erkanntes Format (DATEV_FORMAT, ASCII_STANDARD, UNKNOWN)
- **Dialect**: CSV-Dialekt (delimiter, quote, escape, newline)
- **DerivedDate**: Abgeleitetes Datum mit Jahr, Konfidenz und ggf. Warning

## Success Criteria

### Measurable Outcomes

- **SC-001**: Parser verarbeitet 50k Zeilen in ≤ 1s (Parse-only, ohne Validierung)
- **SC-002**: Parser verarbeitet 1M Zeilen mit ≤ 1.2GB Memory Peak
- **SC-003**: 100% der Golden File Tests bestehen
- **SC-004**: Kein Leading-Zero-Verlust bei Kontonummern (0 Fehler in Regression Tests)
- **SC-005**: TTMM-Algorithmus liefert korrektes Jahr in 95%+ der realen Fälle
