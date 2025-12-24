"""
Column mapping for DATEV files.

Maps column headers from line 2 to canonical field IDs using the field dictionary.
"""

from __future__ import annotations

from .errors import Location, ParserError
from .field_dict import FieldDictionary, get_field_dictionary
from .models import ColumnMapping, ColumnMappings


def map_columns(
    tokens: list[str],
    field_dict: FieldDictionary | None = None,
    filename: str | None = None,
) -> tuple[ColumnMappings, list[ParserError]]:
    """
    Map column headers to canonical field IDs.

    Args:
        tokens: Tokenized column header line
        field_dict: Optional field dictionary (defaults to built-in)
        filename: Optional filename for error locations

    Returns:
        Tuple of (ColumnMappings, list of errors/warnings)
    """
    if field_dict is None:
        field_dict = get_field_dictionary()

    errors: list[ParserError] = []
    mappings: list[ColumnMapping] = []
    seen_ids: set[str] = set()

    for index, label in enumerate(tokens):
        label = label.strip()
        location = Location(file=filename, line_no=2, column=index + 1)

        # Look up in field dictionary
        field_def = field_dict.get_by_synonym(label)

        if field_def:
            canonical_id = field_def.canonical_id

            # Check for duplicates
            if canonical_id in seen_ids:
                errors.append(
                    ParserError.warn(
                        code="DVL-COL-002",
                        title="Duplicate column",
                        message=f"Column '{label}' maps to '{canonical_id}' which already exists",
                        location=location,
                        context={"label": label, "canonical_id": canonical_id},
                    )
                )
            else:
                seen_ids.add(canonical_id)
                mappings.append(
                    ColumnMapping(
                        index=index,
                        canonical_id=canonical_id,
                        original_label=label,
                    )
                )
        else:
            # Unknown column - still include it with original label as ID
            # Use lowercase, replace spaces with underscores
            generated_id = label.lower().replace(" ", "_").replace("-", "_")

            errors.append(
                ParserError.info(
                    code="DVL-COL-003",
                    title="Unknown column",
                    message=f"Column '{label}' not found in field dictionary",
                    location=location,
                    context={"label": label, "generated_id": generated_id},
                )
            )

            mappings.append(
                ColumnMapping(
                    index=index,
                    canonical_id=generated_id,
                    original_label=label,
                )
            )

    # Check for required fields
    required_fields = field_dict.get_required_fields()
    for field in required_fields:
        if field.canonical_id not in seen_ids:
            errors.append(
                ParserError.error(
                    code="DVL-COL-001",
                    title="Missing required column",
                    message=f"Required column '{field.canonical_id}' not found",
                    location=Location(file=filename, line_no=2),
                    context={"canonical_id": field.canonical_id, "synonyms": field.synonyms},
                )
            )

    return ColumnMappings(mappings=mappings, raw_labels=tokens), errors
