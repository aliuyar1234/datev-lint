# datev-lint

DATEV export file validator and linter.

## Installation

```bash
pip install datev-lint
```

## Usage

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
pytest
```

## License

MIT
