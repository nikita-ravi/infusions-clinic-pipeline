"""Phase 3: Value collection with original formatting preserved."""

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from reconciliation_v2.discovery.schema import PayerSchema, DiscoveredField
from reconciliation_v2.pipeline.constants import OPERATIONAL_REALITY_PATTERNS


@dataclass
class OperationalReality:
    """Detected operational reality that differs from stated policy."""

    raw_value: str
    min_value: int | None = None
    max_value: int | None = None
    cause: str | None = None


@dataclass
class CollectedValue:
    """A collected value with full metadata."""

    value: Any  # Original value, formatting preserved
    source_id: str
    source_type: str
    source_date: date

    # Operational reality if detected
    operational_reality: OperationalReality | None = None

    # Is this a stated policy value (separate from operational reality)?
    is_stated_policy: bool = False

    # Canonical value for equality comparison
    canonical: Any = None

    @property
    def age_days(self) -> int:
        from datetime import datetime
        return (datetime.now().date() - self.source_date).days


@dataclass
class FieldValues:
    """All collected values for a field across sources."""

    field_name: str
    values: list[CollectedValue] = field(default_factory=list)

    # Related field values (notes, old values, policy updates)
    notes: list[CollectedValue] = field(default_factory=list)
    old_values: list[CollectedValue] = field(default_factory=list)
    old_status: list[CollectedValue] = field(default_factory=list)
    policy_updates: list[CollectedValue] = field(default_factory=list)

    # Qualifier variants
    qualifiers: dict[str, list[CollectedValue]] = field(default_factory=dict)

    @property
    def source_count(self) -> int:
        return len(self.values)

    @property
    def most_recent_date(self) -> date | None:
        if not self.values:
            return None
        return max(v.source_date for v in self.values)

    @property
    def has_conflicts(self) -> bool:
        """Check if there are conflicting values."""
        if len(self.values) <= 1:
            return False

        # Compare canonical values
        canonicals = set()
        for v in self.values:
            if v.canonical is not None:
                try:
                    canonicals.add(v.canonical)
                except TypeError:
                    # Unhashable type, compare differently
                    pass

        return len(canonicals) > 1


def detect_operational_reality(value: Any) -> OperationalReality | None:
    """
    Detect if a value contains operational reality information.

    Examples:
    - "10-12 (system migration delays)" -> {min: 10, max: 12, cause: "system migration"}
    - "7-10 (during transition)" -> {min: 7, max: 10, cause: "during transition"}
    """
    if not isinstance(value, str):
        return None

    # Check for range pattern with parenthetical explanation
    range_match = re.search(r"(\d+)\s*-\s*(\d+)\s*\(([^)]+)\)", value)
    if range_match:
        return OperationalReality(
            raw_value=value,
            min_value=int(range_match.group(1)),
            max_value=int(range_match.group(2)),
            cause=range_match.group(3).strip(),
        )

    # Check for range pattern without explanation
    range_match = re.search(r"(\d+)\s*-\s*(\d+)", value)
    if range_match:
        # Check if there's any operational context
        for pattern in OPERATIONAL_REALITY_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return OperationalReality(
                    raw_value=value,
                    min_value=int(range_match.group(1)),
                    max_value=int(range_match.group(2)),
                    cause=None,
                )

    return None


def collect_field_values(
    field_name: str,
    schema: PayerSchema,
    family: "FieldFamily",
) -> FieldValues:
    """
    Collect all values for a field, including related fields.

    Preserves original formatting. Detects operational reality signals.
    """
    from reconciliation_v2.discovery.field_family import RelationType
    from reconciliation_v2.pipeline.canonicalize import canonicalize_for_equality

    field_values = FieldValues(field_name=field_name)

    # Collect base field values
    # IMPORTANT: Skip null/None values - a source that doesn't mention a field
    # should not compete with sources that do
    if field_name in schema.fields:
        for occ in schema.fields[field_name].occurrences:
            # Filter out null candidates before they enter scoring
            if occ.value is None:
                continue

            op_reality = detect_operational_reality(occ.value)

            collected = CollectedValue(
                value=occ.value,
                source_id=occ.source_id,
                source_type=occ.source_type,
                source_date=occ.source_date,
                operational_reality=op_reality,
                canonical=canonicalize_for_equality(field_name, occ.value),
            )
            field_values.values.append(collected)

    # Collect related field values
    for relation in family.relations:
        rel_field = relation.related_field

        if rel_field not in schema.fields:
            continue

        for occ in schema.fields[rel_field].occurrences:
            collected = CollectedValue(
                value=occ.value,
                source_id=occ.source_id,
                source_type=occ.source_type,
                source_date=occ.source_date,
                canonical=canonicalize_for_equality(rel_field, occ.value),
            )

            if relation.relation_type == RelationType.NOTE:
                field_values.notes.append(collected)

            elif relation.relation_type == RelationType.SUPERSESSION_OLD:
                field_values.old_values.append(collected)

            elif relation.relation_type == RelationType.SUPERSESSION_STATUS:
                field_values.old_status.append(collected)

            elif relation.relation_type == RelationType.POLICY_UPDATE:
                field_values.policy_updates.append(collected)

            elif relation.relation_type == RelationType.QUALIFIER:
                qualifier_name = relation.qualifier_name or "unknown"
                if qualifier_name not in field_values.qualifiers:
                    field_values.qualifiers[qualifier_name] = []
                field_values.qualifiers[qualifier_name].append(collected)

    return field_values


def collect_all_field_values(
    schema: PayerSchema,
    families: dict[str, "FieldFamily"],
    related_fields: set[str] | None = None,
) -> dict[str, FieldValues]:
    """Collect values for all discovered fields.

    Args:
        schema: The payer schema with all discovered fields
        families: Dict of field families (base field -> FieldFamily)
        related_fields: Set of field names that are related fields (not bases)
                       These will be excluded from primary output.
    """
    from reconciliation_v2.discovery.field_family import RelationType

    if related_fields is None:
        related_fields = set()

    all_values = {}

    for field_name, family in families.items():
        # Skip drug fields for now (handled separately)
        if field_name.startswith("drugs."):
            continue

        field_values = collect_field_values(field_name, schema, family)

        # If base field has no values but has qualifiers, we still want to output it
        # The qualifiers become the primary output
        if not field_values.values and field_values.qualifiers:
            # This is a qualifier-only family (e.g., turnaround with no base)
            # Create synthetic values from qualifiers for output
            pass  # Keep the family, qualifiers will be output

        all_values[field_name] = field_values

    # Also collect standalone fields that aren't family bases
    # These are fields that weren't matched by any pattern
    # IMPORTANT: Skip fields that were detected as related fields (like fax_number_old)
    for field_name in schema.fields:
        if field_name.startswith("drugs."):
            continue
        if field_name in related_fields:
            # This is a related field (like _old, _policy_update), skip it
            continue
        if field_name not in all_values:
            # This field wasn't a family base - create a simple family for it
            from reconciliation_v2.discovery.field_family import FieldFamily
            simple_family = FieldFamily(base_field=field_name)
            field_values = collect_field_values(field_name, schema, simple_family)
            if field_values.values:  # Only if it has values
                all_values[field_name] = field_values

    return all_values
