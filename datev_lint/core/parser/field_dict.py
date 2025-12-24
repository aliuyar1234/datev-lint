"""
Field Dictionary - Single Source of Truth for DATEV fields.

This module provides the field dictionary that defines all DATEV fields
with their canonical IDs, synonyms, types, and validation rules.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class FieldDefinition(BaseModel, frozen=True):
    """Definition of a DATEV field from the Field Dictionary."""

    canonical_id: str = Field(description="Canonical field identifier")
    synonyms: list[str] = Field(
        default_factory=list,
        description="Alternative names/labels for this field",
    )
    required: bool = Field(default=False, description="Whether field is required")
    type: str = Field(description="Field type: string, decimal, ttmm, enum, integer")
    max_length: int | None = Field(default=None, description="Maximum string length")
    charset: str | None = Field(
        default=None,
        description="Character set name (e.g., 'belegfeld1', 'alphanumeric')",
    )
    charset_pattern: str | None = Field(
        default=None,
        description="Regex pattern for validation",
    )
    decimal_places: int | None = Field(
        default=None,
        description="Decimal places for decimal type",
    )
    enum_values: list[str] | None = Field(
        default=None,
        description="Allowed values for enum type",
    )
    fix_strategies: list[str] = Field(
        default_factory=list,
        description="Available fix strategies for this field",
    )
    description: str | None = Field(default=None, description="Field description")

    model_config = {"frozen": True}


class FieldDictionary(BaseModel, frozen=True):
    """Complete field dictionary loaded from YAML."""

    fields: dict[str, FieldDefinition]
    version: str

    model_config = {"frozen": True}

    def get_by_synonym(self, label: str) -> FieldDefinition | None:
        """
        Find field definition by synonym (case-insensitive).

        Also matches canonical_id.
        """
        label_lower = label.lower().strip()

        # First check canonical IDs
        for field in self.fields.values():
            if field.canonical_id.lower() == label_lower:
                return field

        # Then check synonyms
        for field in self.fields.values():
            for syn in field.synonyms:
                if syn.lower().strip() == label_lower:
                    return field

        return None

    def get_by_id(self, canonical_id: str) -> FieldDefinition | None:
        """Get field definition by canonical ID."""
        return self.fields.get(canonical_id)

    def get_required_fields(self) -> list[FieldDefinition]:
        """Get all required fields."""
        return [f for f in self.fields.values() if f.required]


def _load_field_dictionary_from_yaml(path: Path) -> FieldDictionary:
    """Load field dictionary from YAML file."""
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    version = data.get("version", "1.0.0")
    fields_data = data.get("fields", {})

    fields: dict[str, FieldDefinition] = {}
    for field_id, field_data in fields_data.items():
        # Ensure canonical_id is set
        field_data["canonical_id"] = field_id
        fields[field_id] = FieldDefinition(**field_data)

    return FieldDictionary(fields=fields, version=version)


@lru_cache(maxsize=1)
def get_field_dictionary() -> FieldDictionary:
    """
    Get the Field Dictionary (Single Source of Truth).

    The dictionary is cached after first load.

    Returns:
        FieldDictionary with all field definitions
    """
    # Look for field_dictionary.yaml in the same directory as this module
    module_dir = Path(__file__).parent
    yaml_path = module_dir / "field_dictionary.yaml"

    if not yaml_path.exists():
        # Return a minimal dictionary if YAML not found
        # This allows the module to load even without the YAML file
        return _get_minimal_field_dictionary()

    return _load_field_dictionary_from_yaml(yaml_path)


def _get_minimal_field_dictionary() -> FieldDictionary:
    """Get a minimal field dictionary for when YAML is not available."""
    return FieldDictionary(
        version="1.0.0-minimal",
        fields={
            "umsatz": FieldDefinition(
                canonical_id="umsatz",
                synonyms=["Umsatz", "Betrag", "Amount"],
                required=True,
                type="decimal",
                decimal_places=2,
                description="Buchungsbetrag",
            ),
            "soll_haben": FieldDefinition(
                canonical_id="soll_haben",
                synonyms=["S/H", "Soll/Haben", "SH"],
                required=True,
                type="enum",
                enum_values=["S", "H"],
                description="Soll/Haben-Kennzeichen",
            ),
            "konto": FieldDefinition(
                canonical_id="konto",
                synonyms=["Konto", "Account", "Kontonummer"],
                required=True,
                type="string",
                max_length=9,
                charset="digits",
                charset_pattern=r"^\d+$",
                description="Kontonummer (Soll-Konto)",
            ),
            "gegenkonto": FieldDefinition(
                canonical_id="gegenkonto",
                synonyms=["Gegenkonto", "Gegen-Konto", "Counter Account"],
                required=True,
                type="string",
                max_length=9,
                charset="digits",
                charset_pattern=r"^\d+$",
                description="Gegenkonto (Haben-Konto)",
            ),
            "belegdatum": FieldDefinition(
                canonical_id="belegdatum",
                synonyms=["Belegdatum", "Datum", "Date", "Beleg-Datum"],
                required=True,
                type="ttmm",
                max_length=4,
                charset_pattern=r"^\d{4}$",
                description="Belegdatum im TTMM-Format",
            ),
            "belegfeld1": FieldDefinition(
                canonical_id="belegfeld1",
                synonyms=["Belegfeld 1", "Belegfeld1", "Belegnummer", "Beleg-Nr"],
                required=False,
                type="string",
                max_length=36,
                charset="belegfeld1",
                charset_pattern=r"^[A-Z0-9_$&%*+\-/]*$",
                fix_strategies=["upper", "sanitize_chars", "truncate"],
                description="Belegnummer (nur Großbuchstaben, Zahlen, Sonderzeichen)",
            ),
            "belegfeld2": FieldDefinition(
                canonical_id="belegfeld2",
                synonyms=["Belegfeld 2", "Belegfeld2"],
                required=False,
                type="string",
                max_length=12,
                description="Zusätzliches Belegfeld",
            ),
            "buchungstext": FieldDefinition(
                canonical_id="buchungstext",
                synonyms=["Buchungstext", "Text", "Beschreibung"],
                required=False,
                type="string",
                max_length=60,
                description="Buchungstext",
            ),
            "wkz": FieldDefinition(
                canonical_id="wkz",
                synonyms=["WKZ", "Währung", "Currency"],
                required=False,
                type="string",
                max_length=3,
                description="Währungskennzeichen",
            ),
            "kurs": FieldDefinition(
                canonical_id="kurs",
                synonyms=["Kurs", "Exchange Rate"],
                required=False,
                type="decimal",
                description="Wechselkurs",
            ),
            "bu_schluessel": FieldDefinition(
                canonical_id="bu_schluessel",
                synonyms=["BU-Schlüssel", "BU Schlüssel", "Buchungsschlüssel"],
                required=False,
                type="string",
                max_length=4,
                description="Buchungsschlüssel",
            ),
            "skonto": FieldDefinition(
                canonical_id="skonto",
                synonyms=["Skonto", "Discount"],
                required=False,
                type="decimal",
                description="Skontobetrag",
            ),
        },
    )


def clear_field_dictionary_cache() -> None:
    """Clear the field dictionary cache (for testing)."""
    get_field_dictionary.cache_clear()
