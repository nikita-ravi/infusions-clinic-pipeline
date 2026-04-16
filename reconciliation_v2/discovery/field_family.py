"""Phase 2: Field family detection - detect relationships between fields."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from reconciliation_v2.discovery.schema import PayerSchema, DiscoveredField


class RelationType(str, Enum):
    """Type of relationship between fields."""

    SUPERSESSION_OLD = "supersession_old"  # X_old indicates X's old value
    SUPERSESSION_STATUS = "supersession_status"  # X_old_status explains deprecation
    POLICY_UPDATE = "policy_update"  # X_policy_update indicates policy change date
    NOTE = "note"  # X_note provides context
    QUALIFIER = "qualifier"  # X_specialty, X_general are variants


@dataclass
class FieldRelation:
    """A detected relationship between fields."""

    related_field: str
    relation_type: RelationType
    qualifier_name: str | None = None  # For QUALIFIER type: "specialty", "general", etc.


@dataclass
class FieldFamily:
    """A base field with all its detected relationships."""

    base_field: str
    relations: list[FieldRelation] = field(default_factory=list)

    # Discovered occurrences for the base field
    base_occurrences: list = field(default_factory=list)

    @property
    def has_supersession(self) -> bool:
        return any(
            r.relation_type in (RelationType.SUPERSESSION_OLD, RelationType.SUPERSESSION_STATUS)
            for r in self.relations
        )

    @property
    def has_policy_update(self) -> bool:
        return any(r.relation_type == RelationType.POLICY_UPDATE for r in self.relations)

    @property
    def has_qualifiers(self) -> bool:
        return any(r.relation_type == RelationType.QUALIFIER for r in self.relations)

    @property
    def has_notes(self) -> bool:
        return any(r.relation_type == RelationType.NOTE for r in self.relations)

    def get_relations_by_type(self, relation_type: RelationType) -> list[FieldRelation]:
        return [r for r in self.relations if r.relation_type == relation_type]

    def get_qualifiers(self) -> list[str]:
        """Get list of qualifier names (e.g., ['specialty', 'general'])."""
        return [
            r.qualifier_name
            for r in self.relations
            if r.relation_type == RelationType.QUALIFIER and r.qualifier_name
        ]


# Patterns for detecting field relationships
# Order matters - more specific patterns first

RELATION_PATTERNS = [
    # Supersession patterns
    (r"^(.+)_old_status$", RelationType.SUPERSESSION_STATUS, None),
    (r"^(.+)_old$", RelationType.SUPERSESSION_OLD, None),

    # Policy update pattern
    (r"^(.+)_policy_update$", RelationType.POLICY_UPDATE, None),

    # Note pattern
    (r"^(.+)_note$", RelationType.NOTE, None),

    # Qualifier patterns - extract qualifier name
    (r"^(.+)_(specialty|general|recommended)$", RelationType.QUALIFIER, 2),

    # Turnaround qualifiers - only match turnaround_* patterns
    # These are the only field families where method qualifiers make sense
    (r"^(turnaround)_(standard|urgent|emergency)_(days|hours)$", RelationType.QUALIFIER, 2),
    (r"^(turnaround)_(portal|fax|phone)_(days|hours)?$", RelationType.QUALIFIER, 2),
]


def detect_field_families(schema: PayerSchema) -> tuple[dict[str, FieldFamily], set[str]]:
    """
    Detect field families from discovered schema.

    Groups related fields (X, X_old, X_note, X_specialty, etc.) into families.
    Returns tuple of:
        - dict mapping base field name to FieldFamily
        - set of field names that were processed as related fields (not bases)

    Smart matching: when a relation field like 'chart_note_policy_update' is found,
    we look for actual data fields that start with 'chart_note' (like 'chart_note_window_days')
    and link the relation to the actual field.
    """
    all_field_names = set(schema.fields.keys())
    families: dict[str, FieldFamily] = {}
    processed_as_related: set[str] = set()

    # First pass: identify all relation fields and their extracted bases
    relation_fields: list[tuple[str, str, RelationType, str | None]] = []
    # (field_name, extracted_base, relation_type, qualifier_name)

    for field_name in all_field_names:
        for pattern, relation_type, qualifier_group in RELATION_PATTERNS:
            match = re.match(pattern, field_name)
            if match:
                extracted_base = match.group(1)
                qualifier_name = None
                if qualifier_group is not None:
                    qualifier_name = match.group(qualifier_group)

                relation_fields.append((field_name, extracted_base, relation_type, qualifier_name))
                processed_as_related.add(field_name)
                break

    # Second pass: find actual base fields for each relation
    # A relation with extracted_base "chart_note" should link to "chart_note_window_days"
    for rel_field, extracted_base, relation_type, qualifier_name in relation_fields:
        # Find the best matching actual field
        # Priority:
        # 1. Exact match: extracted_base == actual field name
        # 2. Prefix match: actual field starts with extracted_base + "_"

        actual_base = None

        # Check for exact match first
        if extracted_base in all_field_names and extracted_base not in processed_as_related:
            actual_base = extracted_base
        else:
            # Look for prefix matches
            candidates = []
            for field_name in all_field_names:
                if field_name not in processed_as_related:
                    if field_name.startswith(extracted_base + "_"):
                        # Don't match other relation patterns
                        is_relation = False
                        for pat, _, _ in RELATION_PATTERNS:
                            if re.match(pat, field_name):
                                is_relation = True
                                break
                        if not is_relation:
                            candidates.append(field_name)

            if candidates:
                # Pick the most specific match (longest common prefix)
                actual_base = min(candidates, key=len)  # shortest field name is usually the base

        # If no actual base found, use the extracted base anyway
        # (it might be a standalone relation without a base field)
        if actual_base is None:
            actual_base = extracted_base

        # Create or update family
        if actual_base not in families:
            families[actual_base] = FieldFamily(base_field=actual_base)

        families[actual_base].relations.append(
            FieldRelation(
                related_field=rel_field,
                relation_type=relation_type,
                qualifier_name=qualifier_name,
            )
        )

    # Third pass: ensure all non-related fields have a family
    for field_name in all_field_names:
        if field_name not in processed_as_related:
            if field_name not in families:
                families[field_name] = FieldFamily(base_field=field_name)

            # Add base occurrences
            if field_name in schema.fields:
                families[field_name].base_occurrences = schema.fields[field_name].occurrences

    # Fourth pass: add base occurrences to families that have relations
    for base_field, family in families.items():
        if base_field in schema.fields and not family.base_occurrences:
            family.base_occurrences = schema.fields[base_field].occurrences

    return families, processed_as_related


def print_schema_summary(schemas: dict[str, PayerSchema]) -> None:
    """Print a summary of discovered schemas for verification."""
    for payer_key, schema in schemas.items():
        print(f"\n{'=' * 60}")
        print(f"PAYER: {schema.payer} ({payer_key})")
        print(f"{'=' * 60}")
        print(f"Sources: {len(schema.sources)}")
        print(f"Total fields discovered: {len(schema.fields)}")

        families, _ = detect_field_families(schema)

        # Group by relationship type for clearer output
        supersession_families = []
        policy_update_families = []
        qualifier_families = []
        note_families = []
        plain_families = []

        for base_field, family in sorted(families.items()):
            if family.has_supersession:
                supersession_families.append((base_field, family))
            if family.has_policy_update:
                policy_update_families.append((base_field, family))
            if family.has_qualifiers:
                qualifier_families.append((base_field, family))
            if family.has_notes:
                note_families.append((base_field, family))
            if not (family.has_supersession or family.has_policy_update or
                    family.has_qualifiers or family.has_notes):
                if not base_field.startswith("drugs."):
                    plain_families.append((base_field, family))

        # Print supersession families
        if supersession_families:
            print(f"\n[SUPERSESSION] ({len(supersession_families)} families)")
            for base_field, family in supersession_families:
                relations = family.get_relations_by_type(RelationType.SUPERSESSION_OLD)
                relations += family.get_relations_by_type(RelationType.SUPERSESSION_STATUS)
                rel_str = ", ".join(r.related_field for r in relations)
                print(f"  {base_field} <- [{rel_str}]")

        # Print policy update families
        if policy_update_families:
            print(f"\n[POLICY UPDATE] ({len(policy_update_families)} families)")
            for base_field, family in policy_update_families:
                relations = family.get_relations_by_type(RelationType.POLICY_UPDATE)
                rel_str = ", ".join(r.related_field for r in relations)
                print(f"  {base_field} <- [{rel_str}]")

        # Print qualifier families
        if qualifier_families:
            print(f"\n[QUALIFIER SPLIT] ({len(qualifier_families)} families)")
            for base_field, family in qualifier_families:
                qualifiers = family.get_qualifiers()
                print(f"  {base_field} -> {{{', '.join(qualifiers)}}}")

        # Print note families
        if note_families:
            print(f"\n[NOTES] ({len(note_families)} families)")
            for base_field, family in note_families:
                relations = family.get_relations_by_type(RelationType.NOTE)
                rel_str = ", ".join(r.related_field for r in relations)
                print(f"  {base_field} <- [{rel_str}]")

        # Print drug fields summary
        drug_fields = [f for f in schema.fields.keys() if f.startswith("drugs.")]
        if drug_fields:
            drugs = set()
            for f in drug_fields:
                parts = f.split(".")
                if len(parts) >= 2:
                    drugs.add(parts[1])
            print(f"\n[DRUGS] ({len(drugs)} drugs, {len(drug_fields)} fields)")
            for drug in sorted(drugs):
                drug_field_count = len([f for f in drug_fields if f.startswith(f"drugs.{drug}.")])
                print(f"  {drug}: {drug_field_count} fields")
