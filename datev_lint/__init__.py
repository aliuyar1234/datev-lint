"""
datev-lint: DATEV export file validator and linter.

A library and CLI tool for validating DATEV export files (EXTF format).
Detects encoding issues, schema violations, and data quality problems.

Usage:
    from datev_lint.core.parser import parse_file
    result = parse_file("EXTF_Buchungsstapel.csv")
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
