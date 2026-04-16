"""Phase 3: Supersession detection."""

from datetime import datetime, timedelta
from typing import Any

from reconciliation.models.decision import DecisionPath
from reconciliation.models.source import SourceRecord


class SupersessionInfo:
    """Information about superseded values."""

    def __init__(self):
        self.deprecated_values: dict[Any, str] = {}  # value -> reason
        self.superseding_value: Any | None = None
        self.effective_date: str | None = None
        self.policy_update_date: str | None = None


def detect_supersession(
    field_name: str,
    sources: list[SourceRecord],
    decision_path: DecisionPath,
) -> SupersessionInfo:
    """
    Detect supersession by scanning for:
    1. {field}_old / {field} pairs
    2. {field}_old_status descriptions
    3. {field}_policy_update dates
    4. Temporal authority (denial letters, recent phone transcripts)

    Returns SupersessionInfo with deprecated values and superseding value.
    """
    info = SupersessionInfo()

    # Rule 1: Scan for {field}_old pairs
    for source in sources:
        data = source.data

        # Check for explicit old/new pairs
        old_key = f"{field_name}_old"
        if old_key in data and field_name in data:
            old_value = data[old_key]
            new_value = data[field_name]
            info.deprecated_values[old_value] = f"superseded by {new_value} in {source.source_id}"
            info.superseding_value = new_value

            decision_path.add(
                rule_name="explicit_deprecation",
                description=f"Found {old_key} → {field_name} pair in {source.source_id}",
                outcome=f"Deprecated: {old_value}, Superseding: {new_value}",
                source_id=source.source_id,
            )

        # Check for {field}_old_status
        old_status_key = f"{field_name.replace('_number', '')}_old_status"
        if old_status_key in data:
            status = data[old_status_key]
            if old_key in data:
                old_value = data[old_key]
                info.deprecated_values[old_value] = status

                decision_path.add(
                    rule_name="deprecation_status",
                    description=f"Found deprecation status: {status}",
                    outcome=f"Deprecated: {old_value}",
                    source_id=source.source_id,
                    status=status,
                )

    # Rule 2: Check for policy update dates
    policy_key = f"{field_name}_policy_update"
    for source in sources:
        if policy_key in source.data:
            policy_date = source.data[policy_key]
            info.policy_update_date = policy_date

            decision_path.add(
                rule_name="policy_update_detected",
                description=f"Policy update found: {policy_date}",
                outcome=f"Field {field_name} updated as of {policy_date}",
                source_id=source.source_id,
                policy_date=policy_date,
            )

    # Rule 3: Temporal authority - denial letters override if recent
    denial_letters = [s for s in sources if s.source_type.value == "denial_letter"]
    if denial_letters:
        most_recent_denial = max(denial_letters, key=lambda s: s.source_date)
        if most_recent_denial.age_days < 30:
            if field_name in most_recent_denial.data:
                decision_path.add(
                    rule_name="recent_denial_letter_authority",
                    description=f"Recent denial letter ({most_recent_denial.source_date}) carries authority",
                    outcome=f"Denial letter value takes precedence",
                    source_id=most_recent_denial.source_id,
                    age_days=most_recent_denial.age_days,
                )

    # Rule 4: Phone transcript temporal override (within 7 days)
    phone_transcripts = [s for s in sources if s.source_type.value == "phone_transcript"]
    if phone_transcripts:
        most_recent_phone = max(phone_transcripts, key=lambda s: s.source_date)
        if most_recent_phone.age_days < 7:
            if field_name in most_recent_phone.data:
                decision_path.add(
                    rule_name="very_recent_phone_transcript",
                    description=f"Phone transcript from {most_recent_phone.source_date} is very recent",
                    outcome="Phone transcript value prioritized",
                    source_id=most_recent_phone.source_id,
                    age_days=most_recent_phone.age_days,
                )

    return info


def is_value_deprecated(value: Any, supersession_info: SupersessionInfo) -> bool:
    """Check if a value is deprecated based on supersession info."""
    # Handle unhashable types (lists, dicts) by checking equality
    if isinstance(value, (list, dict)):
        for deprecated_value in supersession_info.deprecated_values:
            if value == deprecated_value:
                return True
        return False

    try:
        return value in supersession_info.deprecated_values
    except TypeError:
        # Fallback for other unhashable types
        for deprecated_value in supersession_info.deprecated_values:
            if value == deprecated_value:
                return True
        return False


def get_deprecation_reason(value: Any, supersession_info: SupersessionInfo) -> str | None:
    """Get the reason why a value was deprecated."""
    return supersession_info.deprecated_values.get(value)
