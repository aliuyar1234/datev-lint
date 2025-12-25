# datev-lint

DATEV export file validator and linter.

## Installation

```bash
pip install datev-lint
```

## Usage

### CLI

```bash
datev-lint validate EXTF_Buchungsstapel.csv
datev-lint validate EXTF_Buchungsstapel.csv --format json --out report.json
datev-lint validate EXTF_Buchungsstapel.csv --format sarif --out report.sarif
datev-lint validate EXTF_Buchungsstapel.csv --format junit --out report.xml  # Pro
datev-lint profiles
datev-lint rules --profile default
```

### Limits

- Default max input size is **100MiB** (override with `--max-bytes` or `DATEV_LINT_MAX_BYTES`; `0` disables).

### Library

```python
from datev_lint.core.parser import parse_file

result = parse_file("EXTF_Buchungsstapel.csv")
print(f"Header version: {result.header.header_version}")

for row in result.rows:
    print(f"Konto: {row.konto}")
```

## Development

```bash
pip install -e ".[dev]"
python -m ruff format --check .
python -m ruff check .
python -m mypy datev_lint
pytest
```

- Optional: `pip install pre-commit && pre-commit install`

## Pro licensing (optional)

- Install: `pip install "datev-lint[pro]"`
- Env vars:
  - `DATEV_LINT_LICENSE_PATH`: points to your license JSON
  - `DATEV_LINT_PUBLIC_KEY_PATH`: Ed25519 public key PEM used to verify license signatures

## Integration tests (optional)

- Set `DATEV_LINT_INTEGRATION_DIR` to a directory with real `.csv` exports, then run `pytest`.

## License

MIT
