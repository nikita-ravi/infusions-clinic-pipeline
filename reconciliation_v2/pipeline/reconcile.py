"""Main reconciliation orchestration."""

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from reconciliation_v2.discovery.schema import PayerSchema, discover_schema
from reconciliation_v2.discovery.field_family import (
    detect_field_families,
    FieldFamily,
    RelationType,
)
from reconciliation_v2.pipeline.constants import (
    MIN_SOURCES_FOR_OUTPUT,
    MAX_DAYS_FOR_SINGLE_SOURCE,
    PAYER_CONTEXT_FIELDS,
    COLLECTED_CONTEXT_FIELDS,
)
from reconciliation_v2.pipeline.value_collection import (
    collect_field_values,
    collect_all_field_values,
    FieldValues,
    CollectedValue,
)
from reconciliation_v2.pipeline.supersession import apply_supersession, SupersessionResult
from reconciliation_v2.pipeline.qualifiers import process_qualifiers, QualifiedValue
from reconciliation_v2.pipeline.scoring import score_values, select_best_value, ScoredValue
from reconciliation_v2.pipeline.raw_text_validator import (
    load_all_raw_evidence,
    cross_validate_field,
    RawTextEvidence,
)
from reconciliation_v2.llm.client import is_llm_available
from reconciliation_v2.llm.drug_requirements import extract_drug_requirements_with_llm
from reconciliation_v2.llm.executive_summary import generate_executive_summary


@dataclass
class ReconciledField:
    """A fully reconciled field with all metadata."""

    field_name: str
    value: Any  # Original formatting preserved
    confidence: float
    source_id: str
    source_type: str
    source_date: date

    # Decision path for audit trail
    decision_path: list[str] = field(default_factory=list)

    # Conflict information
    has_conflicts: bool = False
    all_values: dict[str, Any] = field(default_factory=dict)  # source_id -> value

    # Supersession information
    superseded_values: list[str] = field(default_factory=list)  # source_ids
    supersession_reasons: list[str] = field(default_factory=list)

    # Qualifier variants if present
    qualified_output: Any = None

    # Notes/context
    notes: list[str] = field(default_factory=list)

    # Operational reality warning
    operational_reality: dict | None = None


@dataclass
class DrugInfo:
    """Reconciled information for a specific drug."""

    drug_name: str
    fields: dict[str, Any] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class DataCoverage:
    """
    Documents what data was available vs what might be missing.

    Transparency about the extraction → reconciliation pipeline limitations.
    """
    # What we found in extracted JSON
    fields_extracted: int = 0
    sources_used: list[str] = field(default_factory=list)

    # What's typically needed but may be missing
    potentially_missing: list[str] = field(default_factory=list)

    # Confidence in completeness
    extraction_note: str = ""


@dataclass
class BestRoute:
    """
    The derived best route for ops/frontend consumption.

    This is the PRIMARY OUTPUT for someone filling out a PA form.
    Every field here is actionable - no ambiguity.
    """

    # Submission method
    submission: dict[str, Any] = field(default_factory=dict)
    # Example: {
    #   "preferred_method": "portal",
    #   "preferred_url": "www.availity.com",
    #   "fallback_method": "fax",
    #   "fallback_fax": "(888) 267-3300",
    #   "do_not_use": ["(888) 267-3277 (deprecated Feb 2026)"]
    # }

    # Required documents for submission
    required_documents: list[str] = field(default_factory=list)
    # Example: ["PA request form (AET-PA-2025)", "Chart notes within 90 days", ...]

    # Turnaround times - preserve ranges, don't collapse
    turnaround: dict[str, str] = field(default_factory=dict)
    # Example: {"portal": "3-5 business days", "fax": "7-10 days (during transition)", "urgent": "24 hours"}

    # Contact info
    contact: dict[str, Any] = field(default_factory=dict)
    # Example: {"status_phone": "...", "appeal_fax": "...", "appeal_deadline_days": 60}

    # Drug-specific requirements for ALL drugs (drug_name -> requirements)
    # Each drug has: step_therapy_required, auth_period_months, biosimilar_required, notes, etc.
    all_drug_requirements: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Restrictions and warnings
    restrictions: list[str] = field(default_factory=list)
    # Example: ["System migration in progress - expect delays", "Biosimilar trial required for RA indication"]

    # Data coverage - transparency about what's in extracted JSON vs what might be missing
    data_coverage: DataCoverage = field(default_factory=DataCoverage)


@dataclass
class PayerReconciliation:
    """Complete reconciliation result for a payer."""

    payer: str
    payer_key: str

    # THE PRIMARY OUTPUT - actionable route for ops/frontend
    best_route: BestRoute = field(default_factory=BestRoute)

    # Reconciled fields (detailed, for audit)
    fields: dict[str, ReconciledField] = field(default_factory=dict)

    # Raw fields (all discovered, for debug)
    raw_fields: dict[str, FieldValues] = field(default_factory=dict)

    # ALL drugs with their requirements (drug_name -> DrugInfo)
    all_drugs: dict[str, DrugInfo] = field(default_factory=dict)

    # Focus drug (highlighted for high-signal mentions, but ALL drugs are processed)
    focus_drug: str | None = None
    focus_drug_selection_reason: str = ""

    # Payer-level context/warnings
    payer_warnings: list[str] = field(default_factory=list)
    payer_context: dict[str, Any] = field(default_factory=dict)

    # Raw text validation results
    raw_text_validations: dict[str, dict] = field(default_factory=dict)

    # LLM-generated executive summary (TL;DR)
    executive_summary: str | None = None

    # Summary stats
    total_fields_discovered: int = 0
    total_fields_output: int = 0
    conflicts_detected: int = 0
    fields_validated_against_raw: int = 0
    json_raw_conflicts: int = 0


def select_focus_drug(schema: PayerSchema, override: str | None = None) -> tuple[str | None, str]:
    """
    Select focus drug based on mentions in high-signal sources.

    Strategy:
    1. Get all known drug names from the schema
    2. For each high-signal source (phone, denial), count unique drug mentions
       - Check both structured fields AND raw text
    3. Select drug with most high-signal source mentions
    4. Fallback to counting all sources if no high-signal data

    Returns (drug_name, selection_reason).
    """
    if override:
        return override, f"CLI override: --drug {override}"

    # First, collect all known drug names from the schema
    known_drugs: set[str] = set()
    for field_name in schema.fields:
        if field_name.startswith("drugs."):
            parts = field_name.split(".")
            if len(parts) >= 2:
                known_drugs.add(parts[1])

    if not known_drugs:
        return None, "No drug data available in any source"

    # Count drug mentions in high-signal sources
    # Key insight: count per SOURCE, not per field
    drug_source_counts: dict[str, set[str]] = {drug: set() for drug in known_drugs}
    high_signal_types = {"phone_transcript", "denial_letter"}

    # Load raw text evidence for high-signal sources
    from reconciliation_v2.pipeline.raw_text_validator import load_all_raw_evidence
    raw_evidence_list = load_all_raw_evidence(schema.payer_key)
    # Map source_type -> raw_text
    raw_text_by_type = {ev.source_type: ev.raw_text for ev in raw_evidence_list}

    for source in schema.sources:
        source_id = source["source_id"]
        source_type = source["source_type"]

        # Check structured drug fields
        for drug_name in known_drugs:
            prefix = f"drugs.{drug_name}."
            for field_name in schema.fields:
                if field_name.startswith(prefix):
                    for occ in schema.fields[field_name].occurrences:
                        if occ.source_id == source_id:
                            drug_source_counts[drug_name].add(source_id)
                            break  # Only count once per source

        # For high-signal sources, also check raw text for drug name mentions
        if source_type in high_signal_types:
            raw_text = raw_text_by_type.get(source_type, "").lower()
            if raw_text:
                for drug_name in known_drugs:
                    if drug_name.lower() in raw_text:
                        drug_source_counts[drug_name].add(source_id)

    # Calculate counts
    drug_counts = {drug: len(sources) for drug, sources in drug_source_counts.items()}

    # Filter to only high-signal sources for primary selection
    high_signal_counts: dict[str, int] = {}
    for drug_name in known_drugs:
        high_signal_sources = [
            s for s in drug_source_counts[drug_name]
            if any(src["source_id"] == s and src["source_type"] in high_signal_types
                   for src in schema.sources)
        ]
        if high_signal_sources:
            high_signal_counts[drug_name] = len(high_signal_sources)

    # Select based on high-signal counts if available
    if high_signal_counts:
        best_drug = max(high_signal_counts, key=high_signal_counts.get)
        count_str = ", ".join(f"{d}: {c}" for d, c in sorted(high_signal_counts.items(), key=lambda x: -x[1]))
        return best_drug, f"Data-driven (high-signal): {best_drug} ({high_signal_counts[best_drug]} mentions in phone/denial) [{count_str}]"

    # Fallback: use all sources
    if any(c > 0 for c in drug_counts.values()):
        best_drug = max(drug_counts, key=drug_counts.get)
        count_str = ", ".join(f"{d}: {c}" for d, c in sorted(drug_counts.items(), key=lambda x: -x[1]))
        return best_drug, f"Fallback: {best_drug} ({drug_counts[best_drug]} total sources) [{count_str}]"

    return None, "No drug mentions found in any source"


def _get_all_drug_names(schema: PayerSchema) -> list[str]:
    """Get all drug names from the schema."""
    drug_names: set[str] = set()
    for field_name in schema.fields:
        if field_name.startswith("drugs."):
            parts = field_name.split(".")
            if len(parts) >= 2:
                drug_names.add(parts[1])
    return sorted(drug_names)


def extract_payer_context(schema: PayerSchema) -> dict[str, Any]:
    """Extract payer-level context fields (not reconciliation targets)."""
    context = {}

    for field_name in PAYER_CONTEXT_FIELDS:
        if field_name in schema.fields:
            # Get most recent value
            occurrences = schema.fields[field_name].occurrences
            if occurrences:
                most_recent = max(occurrences, key=lambda o: o.source_date)
                context[field_name] = {
                    "value": most_recent.value,
                    "source_id": most_recent.source_id,
                    "source_date": str(most_recent.source_date),
                }

    return context


def should_output_field(field_values: FieldValues) -> bool:
    """
    Determine if a field should be in the output.

    Output if:
    - Field appears in >= 2 sources, OR
    - Field is from a source within 90 days, OR
    - Field contains structured data (dict/list) - reference data that doesn't change often, OR
    - Field is from a high-authority source (denial_letter), OR
    - Field is from provider_manual and uncontested (official policy), OR
    - Field is a qualifier-only family with multiple qualifiers
    """
    if field_values.source_count >= MIN_SOURCES_FOR_OUTPUT:
        return True

    # Check if any value is recent
    for val in field_values.values:
        if val.age_days <= MAX_DAYS_FOR_SINGLE_SOURCE:
            return True

    # Check if field contains structured data (dicts, lists)
    # These are typically reference data that should be preserved
    for val in field_values.values:
        if isinstance(val.value, (dict, list)):
            return True

    # Check if from high-authority source (denial_letter)
    for val in field_values.values:
        if val.source_type == "denial_letter":
            return True

    # Check if from provider_manual and uncontested
    # Provider manuals define official policy - if it's there and no one disputes it, include it
    for val in field_values.values:
        if val.source_type == "provider_manual":
            # Uncontested = single source, or all sources agree
            if field_values.source_count == 1 or not field_values.has_conflicts:
                return True

    # Check if this is a qualifier-only family with multiple qualifiers
    # E.g., turnaround with turnaround_standard_days, turnaround_fax_days, etc.
    if not field_values.values and field_values.qualifiers:
        # Count total qualifier values across all qualifiers
        total_qualifier_values = sum(
            len(vals) for vals in field_values.qualifiers.values()
        )
        if total_qualifier_values >= MIN_SOURCES_FOR_OUTPUT:
            return True

    return False


def reconcile_field(
    field_name: str,
    field_values: FieldValues,
    family: FieldFamily,
    schema: PayerSchema,
    raw_evidence: list[RawTextEvidence] | None = None,
) -> tuple[ReconciledField | None, dict | None]:
    """
    Reconcile a single field through the full pipeline.

    Returns: (ReconciledField, validation_result) tuple.
    validation_result is None if no raw text validation was performed.
    """
    # Handle qualifier-only families (e.g., turnaround with no base, only qualifiers)
    if not field_values.values and field_values.qualifiers:
        reconciled = _reconcile_qualifier_only_family(field_name, field_values, family, schema)
        return reconciled, None

    # Skip if no values
    if not field_values.values:
        return None, None

    # Build decision path
    decision_path = [
        f"field: {field_name}",
        f"sources: {field_values.source_count}",
    ]

    # Collect all raw values for audit
    all_values = {v.source_id: v.value for v in field_values.values}

    # Phase 4: Apply supersession
    supersession_result = apply_supersession(field_values)

    if supersession_result.supersession_reasons:
        decision_path.extend(supersession_result.supersession_reasons)

    if not supersession_result.active_values:
        decision_path.append("All values superseded - no active values remain")
        return None, None

    # Check for policy update
    has_policy_update = family.has_policy_update
    policy_source_id = None
    if has_policy_update and field_values.policy_updates:
        policy_source_id = field_values.policy_updates[0].source_id

    # Phase 5: Process qualifiers
    qualified = process_qualifiers(field_values, supersession_result)

    # Phase 6: Score active values
    scored_values = score_values(
        field_name=field_name,
        field_values=field_values,
        supersession_result=supersession_result,
        has_policy_update=has_policy_update,
        policy_source_id=policy_source_id,
    )

    # Select best value
    best = select_best_value(scored_values)
    if not best:
        return None, None

    decision_path.extend(best.decision_path)
    decision_path.append(f"selected: {best.value} from {best.source_id}")

    # Determine output value
    # If qualifiers exist, use qualified output shape
    output_value = best.value
    qualified_output = None

    if family.has_qualifiers or qualified.variants:
        qualified.default_value = best.value
        qualified.default_source_id = best.source_id
        qualified_output = qualified.to_output_dict()
        if isinstance(qualified_output, dict):
            output_value = qualified_output

    # Check for conflicts
    has_conflicts = field_values.has_conflicts

    # Collect notes
    notes = [n.value for n in field_values.notes]

    # Check for operational reality
    operational_reality = None
    if best.operational_reality:
        operational_reality = {
            "min": best.operational_reality.min_value,
            "max": best.operational_reality.max_value,
            "cause": best.operational_reality.cause,
            "raw": best.operational_reality.raw_value,
        }
    elif qualified.operational_reality:
        operational_reality = qualified.operational_reality

    # Phase 7: Cross-validate against raw text (if available)
    validation_result = None
    adjusted_confidence = best.total_score

    if raw_evidence:
        validation = cross_validate_field(
            field_name=field_name,
            json_value=best.value,
            raw_evidence=raw_evidence,
            source_type=best.source_type,
        )

        validation_result = {
            "field_name": field_name,
            "json_value": str(best.value),
            "found_in_raw": validation.found_in_raw,
            "raw_matches": validation.raw_matches,
            "confidence_adjustment": validation.confidence_adjustment,
            "note": validation.note,
        }

        # Apply confidence adjustment
        adjusted_confidence = best.total_score + validation.confidence_adjustment
        adjusted_confidence = max(0.1, min(0.95, adjusted_confidence))  # Clamp to [0.1, 0.95]

        if validation.confidence_adjustment != 0:
            decision_path.append(
                f"raw_text_validation: {validation.note} "
                f"(adjustment: {validation.confidence_adjustment:+.2f})"
            )

    return ReconciledField(
        field_name=field_name,
        value=output_value,
        confidence=adjusted_confidence,
        source_id=best.source_id,
        source_type=best.source_type,
        source_date=best.source_date,
        decision_path=decision_path,
        has_conflicts=has_conflicts,
        all_values=all_values,
        superseded_values=[v.source_id for v in supersession_result.superseded_values],
        supersession_reasons=supersession_result.supersession_reasons,
        qualified_output=qualified_output,
        notes=notes,
        operational_reality=operational_reality,
    ), validation_result


def _reconcile_qualifier_only_family(
    field_name: str,
    field_values: FieldValues,
    family: FieldFamily,
    schema: PayerSchema,
) -> ReconciledField | None:
    """
    Reconcile a qualifier-only family (no base field, only qualifiers).

    E.g., turnaround with turnaround_standard_days, turnaround_fax_days, etc.
    Output as a structured dict.

    IMPORTANT: When a qualifier has BOTH stated_policy values (clean numbers from manual/web)
    AND operational_reality values (ranges with causes from phone), PRESERVE BOTH.
    Ops needs to know the official number alongside the current reality.

    Scoring: Each qualifier component is scored independently against its sources.
    Overall confidence = minimum of component confidences.
    """
    import re
    from reconciliation_v2.pipeline.value_collection import detect_operational_reality
    from reconciliation_v2.pipeline.scoring import (
        calculate_freshness,
        calculate_authority,
        calculate_corroboration,
        calculate_confidence_floor,
    )

    decision_path = [
        f"field: {field_name}",
        f"qualifier_only_family: no base field, {len(field_values.qualifiers)} qualifiers",
    ]

    # Build output dict from qualifiers
    output_dict = {}
    stated_policy = {}
    operational_reality = {}
    all_sources = []
    all_values = {}
    notes = []
    component_confidences = []

    for qualifier_name, qualifier_values in field_values.qualifiers.items():
        if not qualifier_values:
            continue

        # Separate values into stated_policy (clean numbers) and operational_reality (ranges)
        stated_values = []
        op_reality_values = []

        for val in qualifier_values:
            op_reality = detect_operational_reality(val.value)
            if op_reality:
                op_reality_values.append((val, op_reality))
            else:
                stated_values.append(val)

        # Store all values for audit
        all_values[f"{field_name}_{qualifier_name}"] = [v.value for v in qualifier_values][0] if qualifier_values else None

        # Score and select best stated_policy value (if any)
        if stated_values:
            best_stated = None
            best_stated_score = -1
            best_stated_source = None

            for val in stated_values:
                freshness = calculate_freshness(val.source_date)
                authority = calculate_authority(val.source_type)
                corroboration, agreeing, total = calculate_corroboration(
                    val.value, f"{field_name}_{qualifier_name}", stated_values
                )
                weighted_total = freshness * 0.35 + authority * 0.35 + corroboration * 0.30
                confidence_floor, _ = calculate_confidence_floor(agreeing, total, source_type=val.source_type)
                score = max(weighted_total, confidence_floor)

                if score > best_stated_score:
                    best_stated_score = score
                    best_stated = val.value
                    best_stated_source = val

            if best_stated is not None:
                component_confidences.append(best_stated_score)
                all_sources.append(best_stated_source.source_id)

                # Preserve the value as-is (including ranges like "3-5")
                # DO NOT collapse ranges to single values - that loses precision
                if isinstance(best_stated, (int, float)):
                    stated_policy[qualifier_name] = best_stated
                elif isinstance(best_stated, str):
                    # Check if it's a simple integer
                    num_match = re.search(r"^(\d+)$", best_stated.strip())
                    if num_match:
                        stated_policy[qualifier_name] = int(num_match.group(1))
                    else:
                        # Keep range strings like "3-5" or "5-7" intact
                        range_match = re.search(r"^(\d+)-(\d+)$", best_stated.strip())
                        if range_match:
                            # Store as a range dict to preserve both values
                            stated_policy[qualifier_name] = {
                                "min": int(range_match.group(1)),
                                "max": int(range_match.group(2)),
                            }
                        else:
                            stated_policy[qualifier_name] = best_stated
                else:
                    stated_policy[qualifier_name] = best_stated

                decision_path.append(f"{qualifier_name} stated_policy: {best_stated} (conf: {best_stated_score:.2f})")

        # Score and select best operational_reality value (if any)
        if op_reality_values:
            best_op = None
            best_op_score = -1
            best_op_source = None
            best_op_reality = None

            for val, op_reality in op_reality_values:
                freshness = calculate_freshness(val.source_date)
                authority = calculate_authority(val.source_type)
                # For op_reality, use phone_transcript sources which have higher authority
                weighted_total = freshness * 0.35 + authority * 0.35 + 0.30  # High corroboration for reality signals
                score = weighted_total

                if score > best_op_score:
                    best_op_score = score
                    best_op = val.value
                    best_op_source = val
                    best_op_reality = op_reality

            if best_op_reality is not None:
                component_confidences.append(best_op_score)
                all_sources.append(best_op_source.source_id)

                operational_reality[qualifier_name] = {
                    "min": best_op_reality.min_value,
                    "max": best_op_reality.max_value,
                }
                if best_op_reality.cause:
                    operational_reality[f"{qualifier_name}_cause"] = best_op_reality.cause

                decision_path.append(
                    f"{qualifier_name} operational_reality: {best_op} (conf: {best_op_score:.2f})"
                )

        # If we have neither stated nor op_reality, just score the best overall
        if not stated_values and not op_reality_values and qualifier_values:
            best_value = max(qualifier_values, key=lambda v: v.source_date)
            decision_path.append(f"{qualifier_name}: {best_value.value} (fallback)")
            all_sources.append(best_value.source_id)

    # Build final output shape
    if stated_policy and operational_reality:
        output_dict = {
            "stated_policy": stated_policy,
            "operational_reality": operational_reality,
        }
    elif stated_policy:
        output_dict = stated_policy
    elif operational_reality:
        output_dict = {"operational_reality": operational_reality}
    else:
        return None

    # Collect notes from the family
    for note_val in field_values.notes:
        notes.append(note_val.value)
        if "emergency" in note_val.value.lower():
            output_dict["emergency_override"] = note_val.value

    # Overall confidence = weighted average of component confidences
    # Using weighted average instead of min because:
    # - Min is too harsh (one weak component tanks the whole score)
    # - Components have different importance (urgent is more critical than portal range)
    if component_confidences:
        confidence = sum(component_confidences) / len(component_confidences)
        min_conf = min(component_confidences)
        max_conf = max(component_confidences)
    else:
        confidence = 0.5
        min_conf = max_conf = 0.5

    decision_path.append(f"overall_confidence: avg of {len(component_confidences)} components -> {confidence:.3f} (range: {min_conf:.2f}-{max_conf:.2f})")
    decision_path.append(f"output: {output_dict}")

    # For composite fields, has_conflicts should be True if multiple components exist
    # (it's a reconciled composite, not a clean single-source field)
    has_conflicts = len(component_confidences) > 1

    # source_date for composite fields: use "multiple" indicator or most recent
    # Don't use runtime date - that's misleading
    composite_source_date = None
    for qualifier_values in field_values.qualifiers.values():
        for val in qualifier_values:
            if composite_source_date is None or val.source_date > composite_source_date:
                composite_source_date = val.source_date

    return ReconciledField(
        field_name=field_name,
        value=output_dict,
        confidence=confidence,
        source_id=", ".join(set(all_sources)) if all_sources else "unknown",
        source_type="composite",  # Changed from "multiple" - clearer semantics
        source_date=composite_source_date or datetime.now().date(),
        decision_path=decision_path,
        has_conflicts=has_conflicts,  # True for composite fields
        all_values=all_values,
        notes=notes,
    )


def _extract_auth_periods_from_text(text: str) -> dict[str, int]:
    """
    Extract initial and renewal auth periods from text using regex.

    Handles patterns like:
    - "Renewal: 12 months"
    - "12 months (renewal)"
    - "12 months renewal"
    - "Initial auth: 6 months. Renewal: 12 months."
    - "6 months initial, 12 months renewal"
    - "Auth period: 6 months (initial), 12 months (renewal)"
    """
    import re
    result = {}

    text_lower = text.lower()

    # Pattern 1: "Renewal: X months" or "Renewal X months"
    match = re.search(r'renewal[:\s]+(\d+)\s*months?', text_lower)
    if match:
        result['auth_period_renewal_months'] = int(match.group(1))

    # Pattern 2: "X months (renewal)" or "X months renewal"
    match = re.search(r'(\d+)\s*months?\s*\(?renewal\)?', text_lower)
    if match:
        result['auth_period_renewal_months'] = int(match.group(1))

    # Pattern 3: "Initial: X months" or "Initial auth: X months"
    match = re.search(r'initial(?:\s+auth)?[:\s]+(\d+)\s*months?', text_lower)
    if match:
        result['auth_period_initial_months'] = int(match.group(1))

    # Pattern 4: "X months initial" or "X months (initial)"
    match = re.search(r'(\d+)\s*months?\s*\(?initial\)?', text_lower)
    if match:
        result['auth_period_initial_months'] = int(match.group(1))

    return result


def _extract_drug_section_from_raw(
    payer_key: str,
    drug_name: str,
    all_known_drugs: list[str] | None = None,
) -> str:
    """
    Extract the raw text section for a specific drug from provider manual.

    Args:
        payer_key: The payer key (e.g., "aetna", "cigna")
        drug_name: The drug to extract section for
        all_known_drugs: List of all known drug names (for detecting section boundaries)
    """
    from pathlib import Path

    manual_path = Path("payer_sources") / payer_key / "provider_manual.txt"
    if not manual_path.exists():
        return ""

    text = manual_path.read_text()
    lines = text.split('\n')

    # Use provided drug list or empty list (will only detect numbered sections)
    known_drugs = all_known_drugs or []

    # Find drug section
    drug_upper = drug_name.upper()
    drug_section = []
    in_section = False

    for i, line in enumerate(lines):
        # Check if this line starts a drug section
        if drug_upper in line.upper() and ':' in line:
            in_section = True
            drug_section = [line]
        elif in_section:
            # Continue collecting until we hit another drug header or major section
            stripped = line.strip()
            if stripped.startswith('-') or stripped == '':
                drug_section.append(line)
            elif stripped and stripped[0].isdigit() and '.' in stripped[:5]:
                # New numbered section, stop
                break
            elif any(other_drug.upper() + ':' in line.upper() or other_drug.upper() + ' (' in line.upper()
                     for other_drug in known_drugs if other_drug.upper() != drug_upper):
                # Another drug's section starts, stop
                break
            else:
                drug_section.append(line)

    return '\n'.join(drug_section)


def reconcile_drug(
    drug_name: str,
    schema: PayerSchema,
    payer_name: str = "",
    all_known_drugs: list[str] | None = None,
) -> DrugInfo:
    """
    Reconcile all fields for a specific drug.

    For most fields, takes the most recent value.
    For notes, collects ALL notes from all sources to preserve information.
    Also parses raw text for auth periods and other structured data.

    Args:
        drug_name: Name of the drug to reconcile
        schema: The payer schema with all extracted data
        payer_name: Name of the payer (for LLM context)
        all_known_drugs: List of all known drug names (for section boundary detection)
    """
    drug_info = DrugInfo(drug_name=drug_name)

    # Collect all notes from all sources (not just most recent)
    all_notes: set[str] = set()
    all_sources: set[str] = set()  # Track sources for deduplication

    # Find all drug fields from extracted JSON
    prefix = f"drugs.{drug_name}."
    for field_name in schema.fields:
        if field_name.startswith(prefix):
            sub_field = field_name[len(prefix):]
            occurrences = schema.fields[field_name].occurrences

            if occurrences:
                # For notes, collect from ALL sources
                if sub_field == "notes":
                    for occ in occurrences:
                        if occ.value:
                            all_notes.add(occ.value)
                            all_sources.add(occ.source_id)
                else:
                    # For other fields, get most recent value
                    most_recent = max(occurrences, key=lambda o: o.source_date)
                    drug_info.fields[sub_field] = most_recent.value
                    all_sources.add(most_recent.source_id)

    # Add all collected notes and deduped sources
    drug_info.notes = list(all_notes)
    drug_info.sources = list(all_sources)

    # =========================================================================
    # DETERMINISTIC EXTRACTION FROM RAW TEXT
    # Extract auth periods that may be missing from JSON extraction
    # =========================================================================
    raw_section = _extract_drug_section_from_raw(
        schema.payer_key, drug_name, all_known_drugs=all_known_drugs
    )
    if raw_section:
        auth_periods = _extract_auth_periods_from_text(raw_section)
        for field, value in auth_periods.items():
            if field not in drug_info.fields or drug_info.fields[field] is None:
                drug_info.fields[field] = value

    # Also extract from notes (in case raw section didn't have it)
    for note in drug_info.notes:
        auth_periods = _extract_auth_periods_from_text(note)
        for field, value in auth_periods.items():
            if field not in drug_info.fields or drug_info.fields[field] is None:
                drug_info.fields[field] = value

    # =========================================================================
    # KEYWORD-BASED EXTRACTION (conservative - only explicit mentions)
    # =========================================================================
    combined_text = raw_section + ' ' + ' '.join(drug_info.notes)
    combined_lower = combined_text.lower()

    # Specialist required - ONLY if explicitly mentioned for THIS drug
    if any(phrase in combined_lower for phrase in
           ['specialist must', 'specialist required', 'neurologist must',
            'oncologist must', 'oncologist letter', 'neurologist must submit']):
        if "specialist_required" not in drug_info.fields:
            drug_info.fields["specialist_required"] = True

    # Prior treatment failure - ONLY if explicitly required
    if any(phrase in combined_lower for phrase in
           ['failure required', 'must document failure', 'failure documentation required',
            'trial and failure', 'failure or contraindication required']):
        if "prior_treatment_failure_required" not in drug_info.fields:
            drug_info.fields["prior_treatment_failure_required"] = True

    # Biosimilar - distinguish REQUIRED vs PREFERRED
    # Check for REQUIRED first (stronger language)
    if any(phrase in combined_lower for phrase in
           ['biosimilar required', 'biosimilar must', 'biosimilar trial required',
            'biosimilar attestation required', 'biosimilar step therapy required',
            'biosimilar step therapy is now required', 'requires biosimilar',
            'must trial biosimilar', 'biosimilar first']):
        if "biosimilar_required" not in drug_info.fields:
            drug_info.fields["biosimilar_required"] = True
    # Check for PREFERRED (weaker language) - only if not already required
    elif any(phrase in combined_lower for phrase in
             ['biosimilar preferred', 'biosimilar recommended', 'prefer biosimilar']):
        if "biosimilar_preferred" not in drug_info.fields:
            drug_info.fields["biosimilar_preferred"] = True

    # =========================================================================
    # LLM ENHANCEMENT (with strict grounding constraints)
    # =========================================================================
    if drug_info.notes and is_llm_available():
        llm_fields = extract_drug_requirements_with_llm(
            drug_name=drug_name,
            all_notes=drug_info.notes,
            payer_name=payer_name,
            existing_fields=drug_info.fields,
            raw_drug_section=raw_section,  # Pass raw text for grounding
        )
        drug_info.fields = llm_fields

    return drug_info


def derive_best_route(
    result: PayerReconciliation,
    schema: PayerSchema,
) -> BestRoute:
    """
    Derive the best_route from reconciled fields.

    This is the PRIMARY OUTPUT for ops/frontend.
    We extract the most actionable information from the detailed fields.
    """
    best = BestRoute()

    # =========================================================================
    # 1. SUBMISSION METHOD - preferred/fallback structure
    # =========================================================================
    submission = {}

    # Determine preferred method from submission_methods and notes
    if "submission_methods" in result.fields:
        methods = result.fields["submission_methods"].value
        notes = result.fields["submission_methods"].notes

        # Check for preference hints in notes or source data
        has_portal_preference = any(
            "preferred" in n.lower() or "faster" in n.lower()
            for n in notes
        )

        if isinstance(methods, list):
            # Default: prefer portal if available, then fax
            if "portal" in methods:
                submission["preferred_method"] = "portal"
                if "fax" in methods:
                    submission["fallback_method"] = "fax"
            elif "fax" in methods:
                submission["preferred_method"] = "fax"
                if "phone" in methods or "phone_urgent_only" in methods:
                    submission["fallback_method"] = "phone (urgent only)"
            else:
                submission["preferred_method"] = methods[0] if methods else "unknown"
        else:
            submission["preferred_method"] = str(methods)

    # Add portal URL if available
    if "portal_url" in result.fields:
        submission["preferred_url"] = result.fields["portal_url"].value
        # Add portal notes
        if result.fields["portal_url"].notes:
            submission["portal_notes"] = result.fields["portal_url"].notes

    # Add fax number(s)
    if "fax_number" in result.fields:
        fax_field = result.fields["fax_number"]

        # Handle structured fax (UHC has specialty/general)
        if isinstance(fax_field.value, dict):
            submission["fax_numbers"] = fax_field.value
            if "recommended" in fax_field.value:
                submission["fallback_fax"] = fax_field.value["recommended"]
            elif "specialty" in fax_field.value:
                submission["fallback_fax"] = fax_field.value["specialty"]
            elif "default" in fax_field.value:
                submission["fallback_fax"] = fax_field.value["default"]
        else:
            submission["fallback_fax"] = fax_field.value

        # Add deprecated fax numbers as do_not_use
        if fax_field.superseded_values and fax_field.all_values:
            deprecated = []
            for source_id in fax_field.superseded_values:
                if source_id in fax_field.all_values:
                    old_value = fax_field.all_values[source_id]
                    # Find deprecation reason
                    reasons = [r for r in fax_field.supersession_reasons if "Deprecation reason" in r]
                    reason_text = ""
                    if reasons:
                        reason_text = reasons[0].replace("Deprecation reason: ", "")
                    deprecated.append(f"{old_value} ({reason_text})" if reason_text else old_value)
            if deprecated:
                submission["do_not_use"] = list(set(deprecated))

        # Add fax notes
        if fax_field.notes:
            submission["fax_notes"] = fax_field.notes

    best.submission = submission

    # =========================================================================
    # 2. REQUIRED DOCUMENTS
    # =========================================================================
    required_docs = []
    seen_docs = set()  # For deduplication

    def add_doc(doc: str):
        """Add document if not already present (normalized check)."""
        normalized = doc.lower().strip()
        # Check for duplicates by key phrases
        key_phrases = ["pa request", "chart note", "lab", "letter of medical", "lmn",
                       "step therapy", "biosimilar", "prescription", "prior treatment"]
        for phrase in key_phrases:
            if phrase in normalized:
                if phrase in seen_docs:
                    return  # Skip duplicate
                seen_docs.add(phrase)
                break
        required_docs.append(doc)

    # PA form - with portal access hint
    if "pa_form" in result.fields:
        pa_form = result.fields["pa_form"].value
        pa_notes = result.fields["pa_form"].notes

        # Check for portal access hint
        has_portal_hint = False
        if best.submission.get("preferred_url"):
            has_portal_hint = True
        if pa_notes:
            for note in pa_notes:
                if "availity" in note.lower() or "portal" in note.lower():
                    has_portal_hint = True
                    break

        if has_portal_hint:
            portal_name = best.submission.get("preferred_url", "portal")
            add_doc(f"PA request form (retrieve from {portal_name}; best-known version: {pa_form})")
        else:
            add_doc(f"PA request form ({pa_form})")

    # Chart notes
    if "chart_note_window_days" in result.fields:
        days = result.fields["chart_note_window_days"].value
        add_doc(f"Chart notes within {days} days")

    # Labs - check multiple sources
    if "lab_window_days" in result.fields:
        days = result.fields["lab_window_days"].value
        add_doc(f"Lab results within {days} days")
    else:
        # Check raw fields for lab_window_days
        if "lab_window_days" in result.raw_fields and result.raw_fields["lab_window_days"].values:
            days = result.raw_fields["lab_window_days"].values[0].value
            add_doc(f"Lab results within {days} days")
        # Check common denial reasons
        elif "common_denial_reasons" in result.fields:
            denial_reasons = result.fields["common_denial_reasons"].value
            if isinstance(denial_reasons, dict) and "missing_labs" in denial_reasons:
                add_doc("Lab results (common denial reason when missing)")

    # Letter of medical necessity - check drug notes and denial reasons
    lmn_added = False
    for drug_info in result.all_drugs.values():
        for note in drug_info.notes:
            if "lmn" in note.lower() or "letter of medical necessity" in note.lower():
                add_doc("Letter of medical necessity")
                lmn_added = True
                break
        if lmn_added:
            break

    if not lmn_added:
        # Check denial context
        denial_info = result.payer_context.get("denial_reason") or result.payer_context.get("denial_reasons")
        if denial_info:
            denial_text = str(denial_info).lower()
            if "lmn" in denial_text or "letter of medical necessity" in denial_text:
                add_doc("Letter of medical necessity")

    # Drug-specific requirements (check all drugs)
    has_step_therapy = any(d.fields.get("step_therapy_required") for d in result.all_drugs.values())
    has_biosimilar_required = any(d.fields.get("biosimilar_required") for d in result.all_drugs.values())
    has_biosimilar_preferred = any(d.fields.get("biosimilar_preferred") for d in result.all_drugs.values())

    if has_step_therapy:
        add_doc("Step therapy / prior treatment failure documentation")
    if has_biosimilar_required:
        add_doc("Biosimilar trial documentation or medical justification for brand")
    elif has_biosimilar_preferred:
        add_doc("Biosimilar consideration documentation (preferred but not required)")

    # Pend period warning (from raw fields)
    if "pend_period_days" in result.raw_fields and result.raw_fields["pend_period_days"].values:
        pend_days = result.raw_fields["pend_period_days"].values[0].value
        # Add as a note, not a required doc
        if not any("pend" in r.lower() for r in best.restrictions):
            best.restrictions.append(f"Incomplete submissions pended for {pend_days} days before auto-denial")

    best.required_documents = required_docs

    # =========================================================================
    # 3. TURNAROUND - preserve ranges
    # =========================================================================
    turnaround = {}

    # Check turnaround field
    if "turnaround" in result.fields:
        ta_value = result.fields["turnaround"].value

        if isinstance(ta_value, dict):
            # Has stated_policy and/or operational_reality
            stated = ta_value.get("stated_policy", {})
            reality = ta_value.get("operational_reality", {})

            # If no stated_policy key, the dict IS the stated values
            if not stated and not reality:
                stated = ta_value

            # Portal
            if "portal" in stated:
                portal_val = stated["portal"]
                if isinstance(portal_val, dict) and "min" in portal_val:
                    turnaround["portal"] = f"{portal_val['min']}-{portal_val['max']} business days"
                else:
                    turnaround["portal"] = f"{portal_val} business days"
            elif "portal" in ta_value:
                portal_val = ta_value["portal"]
                if isinstance(portal_val, dict) and "min" in portal_val:
                    turnaround["portal"] = f"{portal_val['min']}-{portal_val['max']} business days"
                else:
                    turnaround["portal"] = f"{portal_val} business days"

            # Standard
            if "standard" in reality:
                std_reality = reality["standard"]
                cause = reality.get("standard_cause", "")
                if isinstance(std_reality, dict) and "min" in std_reality:
                    turnaround["standard"] = f"{std_reality['min']}-{std_reality['max']} days"
                    if cause:
                        turnaround["standard"] += f" ({cause})"
                else:
                    turnaround["standard"] = f"{std_reality} days"
            elif "standard" in stated:
                std_val = stated["standard"]
                if isinstance(std_val, dict) and "min" in std_val:
                    turnaround["standard"] = f"{std_val['min']}-{std_val['max']} business days"
                else:
                    turnaround["standard"] = f"{std_val} business days"

            # Fax
            if "fax" in reality:
                fax_reality = reality["fax"]
                cause = reality.get("fax_cause", "")
                if isinstance(fax_reality, dict) and "min" in fax_reality:
                    turnaround["fax"] = f"{fax_reality['min']}-{fax_reality['max']} days"
                    if cause:
                        turnaround["fax"] += f" ({cause})"
                else:
                    turnaround["fax"] = f"{fax_reality} days"
            elif "fax" in stated:
                fax_val = stated["fax"]
                if isinstance(fax_val, dict) and "min" in fax_val:
                    turnaround["fax"] = f"{fax_val['min']}-{fax_val['max']} business days"
                else:
                    turnaround["fax"] = f"{fax_val} business days"

            # Urgent
            if "urgent" in stated:
                urgent_val = stated["urgent"]
                if urgent_val <= 48:
                    turnaround["urgent"] = f"{urgent_val} hours"
                else:
                    turnaround["urgent"] = f"{urgent_val} hours"
            if "urgent_hours" in stated:
                turnaround["urgent"] = f"{stated['urgent_hours']} hours"

    # Check turnaround_stated_days (Humana style)
    if "turnaround_stated_days" in result.fields:
        ta_value = result.fields["turnaround_stated_days"].value
        if isinstance(ta_value, dict):
            stated = ta_value.get("stated_policy", {})
            reality = ta_value.get("operational_reality", {})

            if not stated and not reality:
                stated = ta_value

            if "default" in stated:
                turnaround["standard"] = f"{stated['default']} business days"
            if "urgent_hours" in stated:
                turnaround["urgent"] = f"{stated['urgent_hours']} hours"

            # Add operational reality if present
            if "standard" in reality:
                std_reality = reality["standard"]
                cause = reality.get("standard_cause", "")
                if isinstance(std_reality, dict) and "min" in std_reality:
                    turnaround["standard_actual"] = f"{std_reality['min']}-{std_reality['max']} days"
                    if cause:
                        turnaround["standard_actual"] += f" ({cause})"

            if "fax" in reality:
                fax_reality = reality["fax"]
                if isinstance(fax_reality, dict) and "min" in fax_reality:
                    turnaround["fax_actual"] = f"{fax_reality['min']}-{fax_reality['max']} days"

    best.turnaround = turnaround

    # =========================================================================
    # 4. CONTACT INFO
    # =========================================================================
    contact = {}

    # Status/help phone
    if "phone_status_only" in result.fields:
        contact["status_phone"] = result.fields["phone_status_only"].value
    elif "phone_status" in result.fields:
        contact["status_phone"] = result.fields["phone_status"].value
    elif "phone" in result.fields:
        contact["general_phone"] = result.fields["phone"].value

    # Urgent phone
    if "phone_urgent" in result.fields:
        contact["urgent_phone"] = result.fields["phone_urgent"].value

    # Appeal info
    if "appeal_fax" in result.fields:
        contact["appeal_fax"] = result.fields["appeal_fax"].value
    if "appeal_phone" in result.fields:
        contact["appeal_phone"] = result.fields["appeal_phone"].value
    if "appeal_mail" in result.fields:
        contact["appeal_mail"] = result.fields["appeal_mail"].value
    if "appeal_deadline_days" in result.fields:
        contact["appeal_deadline_days"] = result.fields["appeal_deadline_days"].value

    best.contact = contact

    # =========================================================================
    # 5. DRUG REQUIREMENTS - ALL DRUGS
    # =========================================================================
    for drug_name, drug_info in result.all_drugs.items():
        drug_req = {
            "drug_name": drug_name,
        }
        for key, val in drug_info.fields.items():
            drug_req[key] = val
        if drug_info.notes:
            drug_req["notes"] = drug_info.notes
        best.all_drug_requirements[drug_name] = drug_req

    # =========================================================================
    # 6. RESTRICTIONS AND WARNINGS
    # =========================================================================
    restrictions = []
    seen_restriction_keys = set()  # For deduplication

    def add_restriction(r: str):
        """Add restriction if not duplicate (normalized check)."""
        # Normalize for comparison
        normalized = r.lower().strip()
        # Extract key concepts for deduplication
        key_phrases = ["step therapy", "biosimilar", "system migration", "pend",
                       "conventional therapy", "prior treatment"]
        for phrase in key_phrases:
            if phrase in normalized:
                if phrase in seen_restriction_keys:
                    return  # Skip duplicate
                seen_restriction_keys.add(phrase)
                break
        restrictions.append(r)

    # Add payer-level warnings as restrictions
    for warning in result.payer_warnings:
        add_restriction(warning)

    # Add drug-specific restrictions (from ALL drugs, but deduplicated)
    for drug_name, drug_info in result.all_drugs.items():
        drug_fields = drug_info.fields
        if drug_fields.get("biosimilar_required"):
            add_restriction(f"{drug_name}: Biosimilar trial required before brand drug approval")
        if drug_fields.get("step_therapy_required"):
            add_restriction(f"{drug_name}: Step therapy / prior treatment failure required")
        if drug_fields.get("specialist_required"):
            add_restriction(f"{drug_name}: Specialist diagnosis confirmation required")

        # Add relevant drug notes (but deduplicate)
        for note in drug_info.notes:
            note_lower = note.lower()
            # Only add if it mentions restrictions and isn't redundant
            if any(kw in note_lower for kw in ["required", "must", "only"]):
                add_restriction(f"{drug_name}: {note}")

    # Add common denial reasons as restrictions to watch for
    if "common_denial_reasons" in result.fields:
        denial_reasons = result.fields["common_denial_reasons"].value
        if isinstance(denial_reasons, dict):
            top_reasons = sorted(denial_reasons.items(), key=lambda x: x[1], reverse=True)[:3]
            for reason, pct in top_reasons:
                reason_text = reason.replace("_", " ").title()
                add_restriction(f"Common denial: {reason_text} ({pct})")

    best.restrictions = restrictions

    # =========================================================================
    # 7. DATA COVERAGE - transparency about extraction limitations
    # =========================================================================
    coverage = DataCoverage()

    # What we found
    coverage.fields_extracted = result.total_fields_discovered
    coverage.sources_used = [s["source_id"] for s in schema.sources]

    # Standard PA requirements that might not be in extracted JSON
    typical_requirements = [
        "letter_of_medical_necessity",
        "prescription_order",
        "diagnosis_codes",
        "prior_treatment_history",
        "specialist_attestation",
        "clinical_rationale",
    ]

    # Check what's missing
    extracted_field_names = set(result.raw_fields.keys())
    potentially_missing = []

    for req in typical_requirements:
        # Check if anything similar exists
        found = False
        for field_name in extracted_field_names:
            if req.replace("_", "") in field_name.replace("_", "").lower():
                found = True
                break
        # Also check in drug notes (all drugs)
        if not found:
            for drug_info in result.all_drugs.values():
                for note in drug_info.notes:
                    if req.replace("_", " ") in note.lower():
                        found = True
                        break
                if found:
                    break
        if not found:
            potentially_missing.append(req.replace("_", " ").title())

    coverage.potentially_missing = potentially_missing

    # Build extraction note with raw text validation info
    validation_note = ""
    if result.fields_validated_against_raw > 0:
        if result.json_raw_conflicts > 0:
            validation_note = f" Cross-validated {result.fields_validated_against_raw} fields against raw text ({result.json_raw_conflicts} discrepancies found)."
        else:
            validation_note = f" Cross-validated {result.fields_validated_against_raw} fields against raw text (all matched)."

    coverage.extraction_note = (
        f"Based on {len(coverage.sources_used)} sources.{validation_note} "
        f"Verify with payer if additional documentation needed: {', '.join(potentially_missing[:3])}..."
        if potentially_missing else
        f"Based on {len(coverage.sources_used)} sources.{validation_note} Key requirements appear complete."
    )

    best.data_coverage = coverage

    return best


def _best_route_to_dict(best_route: BestRoute) -> dict[str, Any]:
    """Convert BestRoute dataclass to dict for LLM input."""
    return {
        "submission": best_route.submission,
        "required_documents": best_route.required_documents,
        "turnaround": best_route.turnaround,
        "contact": best_route.contact,
        "all_drug_requirements": best_route.all_drug_requirements,
        "restrictions": best_route.restrictions,
    }


def reconcile_payer(
    schema: PayerSchema,
    drug_override: str | None = None,
) -> PayerReconciliation:
    """
    Reconcile all fields for a payer.

    Iterates over ALL discovered fields, not just family members.
    Cross-validates JSON extracted data against raw .txt source files.
    """
    # Detect field families
    families, related_fields = detect_field_families(schema)

    # Collect all field values (excluding related fields from primary output)
    all_field_values = collect_all_field_values(schema, families, related_fields)

    # Load raw text evidence for cross-validation
    raw_evidence = load_all_raw_evidence(schema.payer_key)

    # Extract payer context
    payer_context = extract_payer_context(schema)

    # Build payer warnings from context
    payer_warnings = []
    if "system_migration_in_progress" in payer_context:
        ctx = payer_context["system_migration_in_progress"]
        if ctx["value"]:
            payer_warnings.append(
                f"SYSTEM MIGRATION IN PROGRESS (source: {ctx['source_id']}). "
                "Expect processing delays and potential portal issues."
            )
    if "phone_experience_note" in payer_context:
        ctx = payer_context["phone_experience_note"]
        payer_warnings.append(
            f"Phone experience: {ctx['value']} (source: {ctx['source_id']})"
        )

    # Select focus drug
    focus_drug, focus_reason = select_focus_drug(schema, drug_override)

    # Initialize result
    result = PayerReconciliation(
        payer=schema.payer,
        payer_key=schema.payer_key,
        raw_fields=all_field_values,
        focus_drug=focus_drug,
        focus_drug_selection_reason=focus_reason,
        payer_warnings=payer_warnings,
        payer_context=payer_context,
        total_fields_discovered=len(schema.fields),
    )

    # Reconcile each field
    for field_name, field_values in all_field_values.items():
        # Skip payer context fields
        if field_name in PAYER_CONTEXT_FIELDS:
            continue

        # Handle collected context fields (note, notes, denial_reason)
        # These are operational context - collect all values, don't reconcile
        if field_name in COLLECTED_CONTEXT_FIELDS:
            if field_values.values:
                # Collect ALL values (both are useful context)
                collected_values = [
                    {"value": v.value, "source_id": v.source_id, "source_date": str(v.source_date)}
                    for v in field_values.values
                ]
                result.payer_context[field_name] = collected_values
            continue

        # Check output filter
        if not should_output_field(field_values):
            continue

        # Get family (create empty one if standalone field)
        family = families.get(field_name, FieldFamily(base_field=field_name))

        # Reconcile (with raw text cross-validation)
        reconciled, validation = reconcile_field(
            field_name, field_values, family, schema, raw_evidence
        )
        if reconciled:
            result.fields[field_name] = reconciled
            if reconciled.has_conflicts:
                result.conflicts_detected += 1

            # Track validation results
            if validation:
                result.raw_text_validations[field_name] = validation
                result.fields_validated_against_raw += 1
                if validation.get("confidence_adjustment", 0) < 0:
                    result.json_raw_conflicts += 1

    result.total_fields_output = len(result.fields)

    # Reconcile ALL drugs (not just focus drug)
    all_drug_names = _get_all_drug_names(schema)
    for drug_name in all_drug_names:
        result.all_drugs[drug_name] = reconcile_drug(
            drug_name, schema, payer_name=schema.payer, all_known_drugs=all_drug_names
        )

    # Derive the best_route - the PRIMARY OUTPUT for ops/frontend
    result.best_route = derive_best_route(result, schema)

    # Generate LLM executive summary (TL;DR)
    if is_llm_available():
        result.executive_summary = generate_executive_summary(
            payer_name=schema.payer,
            best_route=_best_route_to_dict(result.best_route),
            focus_drug=focus_drug,
            conflicts_detected=result.conflicts_detected,
            payer_warnings=result.payer_warnings,
        )

    return result


def run_reconciliation(
    data_path: Path,
    payer_keys: list[str] | None = None,
    drug_override: str | None = None,
) -> dict[str, PayerReconciliation]:
    """
    Run reconciliation for specified payers (or all if not specified).
    """
    # Discover schemas
    schemas = discover_schema(data_path)

    # Filter to specified payers
    if payer_keys:
        schemas = {k: v for k, v in schemas.items() if k in payer_keys}

    # Reconcile each payer
    results = {}
    for payer_key, schema in schemas.items():
        results[payer_key] = reconcile_payer(schema, drug_override)

    return results
