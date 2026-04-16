"""Phase 6: Scoring with exponential decay and authority weights."""

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from reconciliation_v2.pipeline.constants import (
    AUTHORITY_WEIGHTS,
    DEFAULT_FRESHNESS_HALF_LIFE_DAYS,
)
from reconciliation_v2.pipeline.value_collection import CollectedValue, FieldValues
from reconciliation_v2.pipeline.supersession import SupersessionResult
from reconciliation_v2.pipeline.canonicalize import canonicalize_for_equality


@dataclass
class ScoredValue:
    """A value with its computed score and breakdown."""

    value: Any
    source_id: str
    source_type: str
    source_date: date

    # Score components
    freshness_score: float = 0.0
    authority_score: float = 0.0
    corroboration_score: float = 0.0
    policy_boost: float = 0.0

    # Final combined score
    total_score: float = 0.0

    # Operational reality if present
    operational_reality: Any = None

    # Decision path entries
    decision_path: list[str] = field(default_factory=list)


def calculate_freshness(source_date: date, half_life_days: int = DEFAULT_FRESHNESS_HALF_LIFE_DAYS) -> float:
    """
    Calculate freshness score using exponential decay.

    freshness = 0.5 ^ (age_days / half_life)

    With default half_life of 180 days:
    - 0 days old -> 1.0
    - 90 days old -> 0.71
    - 180 days old -> 0.5
    - 360 days old -> 0.25
    - 423 days old -> 0.20
    """
    from datetime import datetime

    age_days = (datetime.now().date() - source_date).days
    if age_days <= 0:
        return 1.0

    freshness = math.pow(0.5, age_days / half_life_days)
    return freshness


def calculate_authority(source_type: str) -> float:
    """Get authority weight for a source type."""
    return AUTHORITY_WEIGHTS.get(source_type, 0.3)


def calculate_corroboration(
    value: Any,
    field_name: str,
    active_values: list[CollectedValue],
) -> tuple[float, int, int]:
    """
    Calculate corroboration score based on how many active sources agree.

    IMPORTANT: Only counts non-superseded, non-null sources.
    If 2/4 sources are superseded and the remaining 2 agree,
    corroboration = 2/2 = 1.0, not 2/4 = 0.5.

    Returns tuple of (score, agreeing_count, total_active_count):
    - score: 0.0 to 1.0
    - agreeing_count: number of sources that agree on this value
    - total_active_count: total number of active sources
    """
    canonical = canonicalize_for_equality(field_name, value)

    # Count sources with same canonical value (from active values only)
    agreeing_count = 0
    total_active = len(active_values)

    for v in active_values:
        v_canonical = canonicalize_for_equality(field_name, v.value)
        if v_canonical == canonical:
            agreeing_count += 1

    if agreeing_count <= 1:
        return 0.0, agreeing_count, total_active

    # Diminishing returns: 1 - (0.5 ^ (n-1))
    # 2 sources: 0.5
    # 3 sources: 0.75
    # 4 sources: 0.875
    base_score = 1.0 - math.pow(0.5, agreeing_count - 1)

    return base_score, agreeing_count, total_active


def calculate_confidence_floor(
    agreeing_count: int,
    total_active: int,
    source_type: str = "",
    superseded_count: int = 0,
) -> tuple[float, str]:
    """
    Calculate confidence floor based on agreement patterns and source authority.

    Returns (floor_value, floor_reason) tuple.

    Floors applied:
    1. Universal agreement (>=2 sources): 0.7 + 0.075 × n (capped at 0.95)
    2. Post-supersession uncontested: When supersession leaves 1 active value, floor = 0.75
    3. Single-source high-authority: provider_manual or denial_letter alone = 0.70

    CAPPED at 0.95 - we never claim 100% certainty in noisy payer systems.
    """
    # Floor 1: Universal agreement (multiple sources all agree)
    if agreeing_count == total_active and agreeing_count >= 2:
        raw_floor = 0.7 + 0.075 * agreeing_count
        return min(raw_floor, 0.95), f"{agreeing_count}/{total_active} universal agreement"

    # Floor 2: Post-supersession uncontested
    # When supersession eliminates competing values, leaving one clear winner
    if total_active == 1 and superseded_count >= 1:
        return 0.75, "uncontested after supersession"

    # Floor 3: Single-source high-authority
    # Provider manuals and denial letters are official policy documents
    if total_active == 1 and source_type in ("provider_manual", "denial_letter"):
        return 0.70, f"single-source {source_type} (official policy)"

    return 0.0, ""  # No floor applies


def score_values(
    field_name: str,
    field_values: FieldValues,
    supersession_result: SupersessionResult,
    has_policy_update: bool = False,
    policy_source_id: str | None = None,
) -> list[ScoredValue]:
    """
    Score all active values for a field.

    Scoring formula:
    total = (freshness * 0.35) + (authority * 0.35) + (corroboration * 0.20) + (policy_boost * 0.10)

    With confidence floors:
    - Universal agreement (>=2 sources): 0.7 + 0.075 × n
    - Post-supersession uncontested: 0.75
    - Single-source high-authority: 0.70

    Policy boost: +0.10 if this source has the policy_update field
    """
    scored_values = []

    active_values = supersession_result.active_values
    if not active_values:
        return scored_values

    # Count how many values were superseded (for confidence floor calculation)
    superseded_count = len(supersession_result.superseded_values)

    for val in active_values:
        # Calculate components
        freshness = calculate_freshness(val.source_date)
        authority = calculate_authority(val.source_type)
        corroboration, agreeing_count, total_active = calculate_corroboration(
            val.value, field_name, active_values
        )

        # Policy boost if this source has the policy_update
        policy_boost = 0.0
        if has_policy_update and val.source_id == policy_source_id:
            policy_boost = 1.0  # Full boost

        # Combine scores
        # Weights: freshness 35%, authority 35%, corroboration 20%, policy 10%
        weighted_total = (
            freshness * 0.35 +
            authority * 0.35 +
            corroboration * 0.20 +
            policy_boost * 0.10
        )

        # Apply confidence floor
        confidence_floor, floor_reason = calculate_confidence_floor(
            agreeing_count=agreeing_count,
            total_active=total_active,
            source_type=val.source_type,
            superseded_count=superseded_count,
        )
        total = max(weighted_total, confidence_floor)

        # Build decision path
        decision_path = [
            f"freshness: {val.source_date} ({val.age_days}d old) -> {freshness:.3f}",
            f"authority: {val.source_type} -> {authority:.3f}",
            f"corroboration: {agreeing_count}/{total_active} agree -> {corroboration:.3f}",
        ]
        if policy_boost > 0:
            decision_path.append(f"policy_boost: source has policy_update -> +{policy_boost:.3f}")
        if confidence_floor > weighted_total:
            decision_path.append(f"confidence_floor: {floor_reason} -> {confidence_floor:.3f}")
        decision_path.append(f"total: {total:.3f}")

        scored = ScoredValue(
            value=val.value,
            source_id=val.source_id,
            source_type=val.source_type,
            source_date=val.source_date,
            freshness_score=freshness,
            authority_score=authority,
            corroboration_score=corroboration,
            policy_boost=policy_boost,
            total_score=total,
            operational_reality=val.operational_reality,
            decision_path=decision_path,
        )
        scored_values.append(scored)

    # Sort by total score descending
    scored_values.sort(key=lambda v: v.total_score, reverse=True)

    return scored_values


def select_best_value(scored_values: list[ScoredValue]) -> ScoredValue | None:
    """Select the best value (highest score)."""
    if not scored_values:
        return None
    return scored_values[0]
