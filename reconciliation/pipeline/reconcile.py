"""Main reconciliation pipeline (Phases 2-6)."""

from typing import Any

from reconciliation.models.decision import DecisionPath, FieldReconciliation, PayerReconciliation
from reconciliation.models.source import PayerData, SourceRecord
from reconciliation.pipeline.conditionals import apply_field_conditionals
from reconciliation.pipeline.normalize import are_values_equivalent, normalize_value
from reconciliation.pipeline.scoring import calculate_confidence
from reconciliation.pipeline.supersession import detect_supersession, is_value_deprecated


def _detect_conflicts(normalized_values: dict) -> bool:
    """Detect if there are conflicts among normalized values (handles unhashable types)."""
    if len(normalized_values) <= 1:
        return False

    values = list(normalized_values.values())
    first_value = values[0]

    # Check if all values are equivalent to the first
    for value in values[1:]:
        if value != first_value:
            # For lists and other types, do deep comparison
            if isinstance(value, (list, dict)) or isinstance(first_value, (list, dict)):
                if value != first_value:
                    return True
            else:
                return True

    return False


class FieldCandidate:
    """A candidate value for a field with metadata."""

    def __init__(
        self,
        value: Any,
        source: SourceRecord,
        confidence: float,
        decision_path: DecisionPath,
    ):
        self.value = value
        self.source = source
        self.confidence = confidence
        self.decision_path = decision_path


def reconcile_field(
    field_name: str,
    sources: list[SourceRecord],
) -> FieldReconciliation:
    """
    Reconcile a single field across multiple sources.

    Pipeline:
    1. Collect all values for this field
    2. Normalize values
    3. Detect supersession
    4. Apply conditional logic
    5. Score all candidates
    6. Select best value
    """
    decision_path = DecisionPath()

    # Phase 2: Collect and normalize values
    raw_values = {}
    normalized_values = {}

    for source in sources:
        if field_name in source.data:
            raw_value = source.data[field_name]
            normalized = normalize_value(field_name, raw_value)
            raw_values[source.source_id] = raw_value
            normalized_values[source.source_id] = normalized

    if not raw_values:
        # No data for this field
        return FieldReconciliation(
            field_name=field_name,
            value=None,
            confidence=0.0,
            decision_path=["no_data: No sources contain this field"],
            contributing_sources=[],
            superseded_sources=[],
            conflicts_detected=False,
        )

    decision_path.add(
        rule_name="collect_values",
        description=f"Collected {len(raw_values)} values from sources",
        outcome=f"Sources: {list(raw_values.keys())}",
        count=len(raw_values),
    )

    # Phase 3: Detect supersession
    supersession_info = detect_supersession(field_name, sources, decision_path)

    # Phase 4: Apply conditional logic
    conditional_value, conditional_source_id = apply_field_conditionals(
        field_name, sources, decision_path
    )

    # If conditional logic provides a value, use it with high confidence
    if conditional_value is not None and conditional_source_id is not None:
        conditional_source = next(s for s in sources if s.source_id == conditional_source_id)

        return FieldReconciliation(
            field_name=field_name,
            value=conditional_value,
            confidence=0.95,  # High confidence for conditional rules
            decision_path=decision_path.to_list(),
            contributing_sources=[conditional_source_id],
            superseded_sources=[],
            conflicts_detected=_detect_conflicts(normalized_values),
            raw_values=raw_values,
        )

    # Phase 5: Score all candidates
    candidates = []

    for source in sources:
        if field_name in source.data:
            value = normalized_values[source.source_id]

            # Create a separate decision path for this candidate
            candidate_path = DecisionPath()
            candidate_path.rules = decision_path.rules.copy()

            confidence = calculate_confidence(
                field_name=field_name,
                value=value,
                source=source,
                all_sources=sources,
                supersession_info=supersession_info,
                decision_path=candidate_path,
            )

            candidates.append(
                FieldCandidate(
                    value=value,
                    source=source,
                    confidence=confidence,
                    decision_path=candidate_path,
                )
            )

    # Phase 6: Select best candidate
    if not candidates:
        return FieldReconciliation(
            field_name=field_name,
            value=None,
            confidence=0.0,
            decision_path=decision_path.to_list(),
            contributing_sources=[],
            superseded_sources=[],
            conflicts_detected=False,
        )

    best_candidate = max(candidates, key=lambda c: c.confidence)

    # Identify superseded sources (those with deprecated values)
    superseded_source_ids = []
    for candidate in candidates:
        if is_value_deprecated(candidate.value, supersession_info):
            superseded_source_ids.append(candidate.source.source_id)

    # Detect conflicts (different normalized values)
    candidate_values = {c.source.source_id: c.value for c in candidates}
    conflicts_detected = _detect_conflicts(candidate_values)

    return FieldReconciliation(
        field_name=field_name,
        value=best_candidate.value,
        confidence=best_candidate.confidence,
        decision_path=best_candidate.decision_path.to_list(),
        contributing_sources=[best_candidate.source.source_id],
        superseded_sources=superseded_source_ids,
        conflicts_detected=conflicts_detected,
        raw_values=raw_values,
    )


def reconcile_payer(payer_data: PayerData, focus_drug: str = "Remicade") -> PayerReconciliation:
    """
    Reconcile all fields for a payer.

    Args:
        payer_data: Full payer data with sources
        focus_drug: Drug to focus on (default: Remicade)
    """
    # Fields to reconcile (core PA submission fields)
    core_fields = [
        "submission_methods",
        "fax_number",
        "portal_url",
        "phone_urgent",
        "pa_form",
        "chart_note_window_days",
        "turnaround_standard_days",
        "turnaround_urgent_hours",
    ]

    reconciled_fields = {}

    # Reconcile core fields
    for field_name in core_fields:
        reconciled_fields[field_name] = reconcile_field(field_name, payer_data.sources)

    # Extract drug-specific requirements for focus drug
    drug_requirements = _extract_drug_requirements(payer_data.sources, focus_drug)
    if drug_requirements:
        reconciled_fields[f"{focus_drug.lower()}_requirements"] = drug_requirements

    # Generate summary
    summary = {
        "payer": payer_data.payer,
        "focus_drug": focus_drug,
        "total_sources": len(payer_data.sources),
        "sources_by_type": _count_sources_by_type(payer_data.sources),
        "fields_reconciled": len(reconciled_fields),
        "conflicts_detected": sum(1 for f in reconciled_fields.values() if f.conflicts_detected),
        "high_confidence_fields": sum(
            1 for f in reconciled_fields.values() if f.confidence >= 0.8
        ),
        "low_confidence_fields": sum(
            1 for f in reconciled_fields.values() if f.confidence < 0.5
        ),
    }

    return PayerReconciliation(
        payer=payer_data.payer,
        fields=reconciled_fields,
        summary=summary,
    )


def _extract_drug_requirements(sources: list[SourceRecord], drug: str) -> FieldReconciliation:
    """Extract drug-specific requirements across sources."""
    decision_path = DecisionPath()

    # Collect drug data from all sources
    drug_data = {}
    for source in sources:
        if "drugs" in source.data and drug in source.data["drugs"]:
            drug_data[source.source_id] = source.data["drugs"][drug]

    if not drug_data:
        return FieldReconciliation(
            field_name=f"{drug.lower()}_requirements",
            value=None,
            confidence=0.0,
            decision_path=["no_data: No drug-specific requirements found"],
            contributing_sources=[],
            superseded_sources=[],
            conflicts_detected=False,
        )

    # Merge requirements (most recent source wins for conflicts)
    most_recent_source = max(
        [s for s in sources if s.source_id in drug_data],
        key=lambda s: s.source_date,
    )

    merged_requirements = drug_data[most_recent_source.source_id].copy()

    decision_path.add(
        rule_name="drug_requirements_merged",
        description=f"Merged {drug} requirements from {len(drug_data)} sources",
        outcome=f"Used most recent source: {most_recent_source.source_id}",
        source_count=len(drug_data),
    )

    return FieldReconciliation(
        field_name=f"{drug.lower()}_requirements",
        value=merged_requirements,
        confidence=0.85,  # High confidence for drug requirements
        decision_path=decision_path.to_list(),
        contributing_sources=[most_recent_source.source_id],
        superseded_sources=[],
        conflicts_detected=len(drug_data) > 1,
        raw_values=drug_data,
    )


def _count_sources_by_type(sources: list[SourceRecord]) -> dict[str, int]:
    """Count sources by type."""
    counts = {}
    for source in sources:
        source_type = source.source_type.value
        counts[source_type] = counts.get(source_type, 0) + 1
    return counts
