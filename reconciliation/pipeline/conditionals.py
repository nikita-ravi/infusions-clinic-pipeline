"""Phase 4: Conditional logic for field-specific rules."""

from typing import Any

from reconciliation.models.decision import DecisionPath
from reconciliation.models.source import SourceRecord


def apply_field_conditionals(
    field_name: str,
    sources: list[SourceRecord],
    decision_path: DecisionPath,
) -> tuple[Any | None, str | None]:
    """
    Apply field-specific conditional rules.

    Returns:
        (preferred_value, source_id) if a conditional rule applies
        (None, None) if no conditional applies
    """
    # Fax number: prefer specialty/dedicated lines over general
    if field_name == "fax_number":
        result = _prefer_specialty_fax(sources, decision_path)
        if result:
            return result

    # PA form: prefer highest version number
    if field_name == "pa_form":
        result = _prefer_latest_form_version(sources, decision_path)
        if result:
            return result

    # Chart note window: take max if policy update exists
    if field_name == "chart_note_window_days":
        result = _apply_chart_note_policy(sources, decision_path)
        if result:
            return result

    # Submission methods: prefer portal if mentioned as preferred
    if field_name == "submission_methods":
        result = _order_by_preference(sources, decision_path)
        if result:
            return result

    return None, None


def _prefer_specialty_fax(
    sources: list[SourceRecord],
    decision_path: DecisionPath,
) -> tuple[Any | None, str | None]:
    """Prefer specialty/dedicated fax numbers over general."""
    specialty_sources = []

    for source in sources:
        data = source.data

        # Look for specialty/dedicated indicators
        if "fax_number_specialty" in data:
            specialty_sources.append((source, data["fax_number_specialty"], "specialty"))
        elif "fax_number_infusion" in data:
            specialty_sources.append((source, data["fax_number_infusion"], "infusion"))

        # Check for notes indicating specialty routing
        if "fax_note" in data:
            note = data["fax_note"].lower()
            if any(kw in note for kw in ["specialty", "dedicated", "faster", "infusion"]):
                if "fax_number" in data:
                    specialty_sources.append((source, data["fax_number"], "specialty_note"))

    if specialty_sources:
        # Prefer most recent specialty fax
        source, value, reason = max(specialty_sources, key=lambda x: x[0].source_date)

        decision_path.add(
            rule_name="prefer_specialty_fax",
            description=f"Specialty fax preferred over general ({reason})",
            outcome=f"Selected: {value}",
            source_id=source.source_id,
            reason=reason,
        )

        return value, source.source_id

    return None, None


def _prefer_latest_form_version(
    sources: list[SourceRecord],
    decision_path: DecisionPath,
) -> tuple[Any | None, str | None]:
    """Prefer highest version number in form names."""
    import re

    forms_with_versions = []

    for source in sources:
        if "pa_form" in source.data:
            form = source.data["pa_form"]
            if form:
                # Try to extract version number (e.g., "UHC-PA-200" -> 200)
                match = re.search(r"-(\d+)$", str(form))
                if match:
                    version = int(match.group(1))
                    forms_with_versions.append((source, form, version))
                # Also try year-based versions (e.g., "HUM-AUTH-2026" -> 2026)
                else:
                    match = re.search(r"-(\d{4})$", str(form))
                    if match:
                        version = int(match.group(1))
                        forms_with_versions.append((source, form, version))

    if forms_with_versions:
        # Get highest version
        source, form, version = max(forms_with_versions, key=lambda x: x[2])

        decision_path.add(
            rule_name="prefer_latest_form_version",
            description=f"Selected form with highest version number",
            outcome=f"Selected: {form} (version {version})",
            source_id=source.source_id,
            version=version,
        )

        return form, source.source_id

    return None, None


def _apply_chart_note_policy(
    sources: list[SourceRecord],
    decision_path: DecisionPath,
) -> tuple[Any | None, str | None]:
    """For chart note window, take max if recent policy update exists."""
    from datetime import datetime, timedelta

    # Check if there's a recent policy update
    policy_updates = []
    for source in sources:
        if "chart_note_policy_update" in source.data:
            policy_updates.append(source)

    if policy_updates:
        # Get most recent policy update
        most_recent = max(policy_updates, key=lambda s: s.source_date)

        # If policy update is within 6 months, take the max value from recent sources
        if most_recent.age_days < 180:
            recent_sources = [s for s in sources if s.age_days < 180]
            values = []
            for source in recent_sources:
                if "chart_note_window_days" in source.data:
                    value = source.data["chart_note_window_days"]
                    if isinstance(value, (int, float)):
                        values.append((source, value))

            if values:
                source, max_value = max(values, key=lambda x: x[1])

                decision_path.add(
                    rule_name="chart_note_policy_update",
                    description=f"Recent policy update detected, taking maximum window",
                    outcome=f"Selected: {max_value} days",
                    source_id=source.source_id,
                    policy_source=most_recent.source_id,
                )

                return max_value, source.source_id

    return None, None


def _order_by_preference(
    sources: list[SourceRecord],
    decision_path: DecisionPath,
) -> tuple[Any | None, str | None]:
    """Order submission methods by stated preference."""
    for source in sources:
        data = source.data

        # Check for explicit preference indicators
        if "portal_note" in data:
            note = data["portal_note"].lower()
            if any(kw in note for kw in ["preferred", "recommended", "faster"]):
                if "submission_methods" in data:
                    methods = data["submission_methods"]
                    if isinstance(methods, list) and "portal" in methods:
                        # Reorder to put portal first
                        reordered = ["portal"] + [m for m in methods if m != "portal"]

                        decision_path.add(
                            rule_name="prefer_portal_submission",
                            description="Portal indicated as preferred method",
                            outcome=f"Reordered methods: {reordered}",
                            source_id=source.source_id,
                            note=data["portal_note"],
                        )

                        return reordered, source.source_id

    return None, None
