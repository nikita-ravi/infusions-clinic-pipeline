"""Phase 5: Confidence scoring."""

from typing import Any

from reconciliation.models.decision import DecisionPath
from reconciliation.models.source import SourceRecord
from reconciliation.pipeline.supersession import SupersessionInfo, is_value_deprecated


def calculate_confidence(
    field_name: str,
    value: Any,
    source: SourceRecord,
    all_sources: list[SourceRecord],
    supersession_info: SupersessionInfo,
    decision_path: DecisionPath,
) -> float:
    """
    Calculate confidence score for a field value from a source.

    Scoring factors:
    1. Recency (0-0.3): How old is the source?
    2. Authority (0-0.25): Source type authority weight
    3. Deprecation penalty (-0.5): Is this value deprecated?
    4. Agreement bonus (0-0.2): Do other sources agree?
    5. Warning penalty (0-0.3): Are there operational warnings?

    Returns: confidence score in [0, 1]
    """
    score = 0.5  # base score

    # Factor 1: Recency boost
    recency_boost = _calculate_recency_boost(source.age_days)
    score += recency_boost

    decision_path.add(
        rule_name="recency_boost",
        description=f"Source is {source.age_days} days old",
        outcome=f"Boost: +{recency_boost:.2f}",
        age_days=source.age_days,
    )

    # Factor 2: Authority boost
    authority_boost = _calculate_authority_boost(source)
    score += authority_boost

    decision_path.add(
        rule_name="authority_boost",
        description=f"Source type: {source.source_type.value}",
        outcome=f"Boost: +{authority_boost:.2f}",
        source_type=source.source_type.value,
        authority_weight=source.authority_weight,
    )

    # Factor 3: Deprecation penalty
    if is_value_deprecated(value, supersession_info):
        score -= 0.5
        reason = supersession_info.deprecated_values.get(value, "unknown")

        decision_path.add(
            rule_name="deprecation_penalty",
            description=f"Value is deprecated: {reason}",
            outcome=f"Penalty: -0.50",
            deprecated_value=value,
            reason=reason,
        )

    # Factor 4: Agreement bonus
    agreement_bonus = _calculate_agreement_bonus(field_name, value, all_sources)
    score += agreement_bonus

    if agreement_bonus > 0:
        decision_path.add(
            rule_name="agreement_bonus",
            description=f"Multiple sources agree on this value",
            outcome=f"Bonus: +{agreement_bonus:.2f}",
        )

    # Factor 5: Warning penalty
    warning_penalty = _calculate_warning_penalty(field_name, source)
    score -= warning_penalty

    if warning_penalty > 0:
        decision_path.add(
            rule_name="warning_penalty",
            description=f"Operational warnings detected",
            outcome=f"Penalty: -{warning_penalty:.2f}",
        )

    # Clamp to [0, 1]
    final_score = max(0.0, min(1.0, score))

    decision_path.add(
        rule_name="final_confidence",
        description=f"Final confidence calculation",
        outcome=f"Score: {final_score:.2f}",
        raw_score=score,
        clamped_score=final_score,
    )

    return final_score


def _calculate_recency_boost(age_days: int) -> float:
    """
    Calculate recency boost based on source age.

    - Last 30 days: +0.3
    - 31-90 days: +0.2
    - 91-180 days: +0.1
    - 181-365 days: +0.05
    - 365+ days: +0.0
    """
    if age_days <= 30:
        return 0.3
    elif age_days <= 90:
        return 0.2
    elif age_days <= 180:
        return 0.1
    elif age_days <= 365:
        return 0.05
    else:
        return 0.0


def _calculate_authority_boost(source: SourceRecord) -> float:
    """
    Calculate authority boost based on source type.

    Authority weights:
    - Denial letter: 1.5 → boost of 0.25
    - Phone transcript: 1.3 → boost of 0.20
    - Web page: 1.0 → boost of 0.15
    - Provider manual: 0.7 → boost of 0.10
    """
    weight = source.authority_weight
    if weight >= 1.5:
        return 0.25
    elif weight >= 1.3:
        return 0.20
    elif weight >= 1.0:
        return 0.15
    else:
        return 0.10


def _calculate_agreement_bonus(
    field_name: str,
    value: Any,
    all_sources: list[SourceRecord],
) -> float:
    """
    Calculate bonus for multiple sources agreeing on the same value.

    For each additional source that agrees: +0.1 (max +0.2)
    """
    from reconciliation.pipeline.normalize import are_values_equivalent

    # Count sources with this value
    agreeing_sources = 0
    for source in all_sources:
        if field_name in source.data:
            source_value = source.data[field_name]
            if are_values_equivalent(field_name, value, source_value):
                agreeing_sources += 1

    # +0.1 for each source beyond the first, max +0.2
    if agreeing_sources > 1:
        return min(0.2, (agreeing_sources - 1) * 0.1)

    return 0.0


def _calculate_warning_penalty(field_name: str, source: SourceRecord) -> float:
    """
    Calculate penalty for operational warnings.

    Check for *_note fields that contain warning signals:
    - "glitchy", "issues", "problems": -0.3 (high severity)
    - "slow", "delayed", "migration": -0.15 (medium severity)
    - "recommend", "prefer": -0.05 (low severity, just a preference)
    """
    penalty = 0.0

    # Look for note fields related to this field
    note_fields = [
        f"{field_name}_note",
        "portal_note",
        "fax_note",
        "system_migration_in_progress",
    ]

    for note_field in note_fields:
        if note_field in source.data:
            note = str(source.data[note_field]).lower()

            # High severity warnings
            if any(kw in note for kw in ["glitchy", "issues", "problems", "not working"]):
                penalty = max(penalty, 0.3)

            # Medium severity warnings
            elif any(kw in note for kw in ["slow", "delayed", "migration", "transition"]):
                penalty = max(penalty, 0.15)

            # Low severity (preference, not warning)
            elif any(kw in note for kw in ["recommend", "prefer", "better"]):
                penalty = max(penalty, 0.05)

    return penalty
