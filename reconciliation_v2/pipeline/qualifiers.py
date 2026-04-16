"""Phase 5: Qualifier handling with structured dict output."""

from dataclasses import dataclass, field
from typing import Any

from reconciliation_v2.pipeline.value_collection import FieldValues, CollectedValue
from reconciliation_v2.pipeline.supersession import SupersessionResult


@dataclass
class QualifiedValue:
    """
    A value with qualifier variants.

    Output shapes:
    - Simple qualifier: {"default": X, "specialty": Y, "general": Z}
    - Method-based: {"by_method": {"portal": 5, "fax": {"min": 7, "max": 10}}}
    - Turnaround with operational reality:
      {
        "stated_policy": {"standard": 7, "urgent_hours": 48},
        "operational_reality": {"standard": {"min": 10, "max": 14}, "cause": "system migration"},
        "emergency_override": "can sometimes get same-day"
      }
    """

    # Primary/default value
    default_value: Any = None
    default_source_id: str | None = None

    # Qualifier variants: qualifier_name -> (value, source_id)
    variants: dict[str, tuple[Any, str]] = field(default_factory=dict)

    # Operational reality (separate from stated policy)
    operational_reality: dict | None = None

    # Notes/context
    notes: list[str] = field(default_factory=list)

    def to_output_dict(self) -> dict:
        """Convert to the committed output shape."""
        # Detect the type of qualifier structure
        has_method_qualifiers = any(
            q in ["portal", "fax", "phone"]
            for q in self.variants.keys()
        )

        has_urgency_qualifiers = any(
            q in ["standard", "urgent", "emergency"]
            for q in self.variants.keys()
        )

        # Build output based on qualifier type
        if has_method_qualifiers and has_urgency_qualifiers:
            # Mixed turnaround - combine into by_method structure
            return self._build_turnaround_output()

        elif has_method_qualifiers:
            # Method-based qualifiers
            return self._build_method_output()

        elif has_urgency_qualifiers:
            # Urgency-based qualifiers (turnaround times)
            return self._build_turnaround_output()

        elif self.variants:
            # Simple qualifiers (specialty, general, recommended)
            output = {}
            if self.default_value is not None:
                output["default"] = self.default_value
            for qual_name, (val, _) in self.variants.items():
                output[qual_name] = val
            return output

        else:
            # No qualifiers, just the default value
            return self.default_value

    def _build_method_output(self) -> dict:
        """Build by_method output shape."""
        by_method = {}

        for qual_name, (val, _) in self.variants.items():
            if qual_name in ["portal", "fax", "phone"]:
                # Check if value has min/max
                if isinstance(val, str) and "-" in val:
                    import re
                    match = re.search(r"(\d+)\s*-\s*(\d+)", val)
                    if match:
                        by_method[qual_name] = {
                            "min": int(match.group(1)),
                            "max": int(match.group(2)),
                        }
                    else:
                        by_method[qual_name] = val
                else:
                    by_method[qual_name] = val

        return {"by_method": by_method}

    def _build_turnaround_output(self) -> dict:
        """Build turnaround output with stated_policy and operational_reality."""
        stated_policy = {}
        operational = {}

        # Process default value
        if self.default_value is not None:
            stated_policy["default"] = self.default_value

        # Process variants
        for qual_name, (val, _) in self.variants.items():
            # Normalize qualifier name
            key = qual_name
            if qual_name == "urgent":
                key = "urgent_hours"

            # Check for operational reality in the value itself
            if isinstance(val, str):
                import re
                # Check for range with explanation
                match = re.search(r"(\d+)\s*-\s*(\d+)\s*(?:\(([^)]+)\))?", val)
                if match:
                    min_val = int(match.group(1))
                    max_val = int(match.group(2))
                    cause = match.group(3) if match.group(3) else None

                    operational[key] = {"min": min_val, "max": max_val}
                    if cause:
                        operational[f"{key}_cause"] = cause
                else:
                    # Try to extract just a number
                    num_match = re.search(r"(\d+)", val)
                    if num_match:
                        stated_policy[key] = int(num_match.group(1))
                    else:
                        stated_policy[key] = val
            else:
                stated_policy[key] = val

        # Add separate operational reality if detected
        if self.operational_reality:
            for k, v in self.operational_reality.items():
                if k not in operational:
                    operational[k] = v

        # Build final output
        output = {}
        if stated_policy:
            output["stated_policy"] = stated_policy
        if operational:
            output["operational_reality"] = operational
        if self.notes:
            # Look for emergency override
            for note in self.notes:
                if "emergency" in note.lower() or "same-day" in note.lower():
                    output["emergency_override"] = note
                    break

        # If only stated_policy and it's simple, flatten
        if list(output.keys()) == ["stated_policy"] and len(stated_policy) == 1:
            return list(stated_policy.values())[0]

        return output if output else self.default_value


def process_qualifiers(
    field_values: FieldValues,
    supersession_result: SupersessionResult,
) -> QualifiedValue:
    """
    Process qualifier variants for a field.

    Handles:
    - Simple qualifiers: *_specialty, *_general, *_recommended
    - Method qualifiers: *_portal, *_fax, *_phone
    - Urgency qualifiers: *_standard, *_urgent, *_emergency

    Detects operational reality vs stated policy in values.
    """
    qualified = QualifiedValue()

    # Set default value from active values (will be refined by scoring later)
    if supersession_result.active_values:
        # Pick most recent for now (scoring will override)
        most_recent = max(
            supersession_result.active_values,
            key=lambda v: v.source_date
        )
        qualified.default_value = most_recent.value
        qualified.default_source_id = most_recent.source_id

        # Check if default value has operational reality
        if most_recent.operational_reality:
            qualified.operational_reality = {
                "standard": {
                    "min": most_recent.operational_reality.min_value,
                    "max": most_recent.operational_reality.max_value,
                },
            }
            if most_recent.operational_reality.cause:
                qualified.operational_reality["cause"] = most_recent.operational_reality.cause

    # Process qualifier variants
    for qual_name, qual_values in field_values.qualifiers.items():
        if qual_values:
            # Pick most recent qualifier value
            most_recent = max(qual_values, key=lambda v: v.source_date)
            qualified.variants[qual_name] = (most_recent.value, most_recent.source_id)

            # Check for operational reality in qualifier
            if most_recent.operational_reality:
                if qualified.operational_reality is None:
                    qualified.operational_reality = {}
                qualified.operational_reality[qual_name] = {
                    "min": most_recent.operational_reality.min_value,
                    "max": most_recent.operational_reality.max_value,
                }
                if most_recent.operational_reality.cause:
                    qualified.operational_reality[f"{qual_name}_cause"] = (
                        most_recent.operational_reality.cause
                    )

    # Collect notes
    for note_val in field_values.notes:
        qualified.notes.append(note_val.value)

    return qualified
