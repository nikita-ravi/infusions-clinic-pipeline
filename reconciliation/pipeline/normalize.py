"""Phase 2: Value normalization."""

import re
from typing import Any


def normalize_value(field_name: str, value: Any) -> Any:
    """
    Normalize a value based on field type.

    Normalization rules:
    - Phone numbers: strip all non-digits
    - URLs: lowercase, strip www., strip trailing /
    - Date ranges: extract numeric value
    - Lists: sort and dedupe
    - Strings: strip whitespace
    """
    if value is None:
        return None

    # Phone number fields
    if "phone" in field_name or "fax" in field_name:
        if isinstance(value, str):
            # Strip all non-digits
            digits = re.sub(r"\D", "", value)
            return digits if digits else None
        return value

    # URL fields
    if "url" in field_name or "portal" in field_name:
        if isinstance(value, str):
            normalized = value.lower()
            normalized = normalized.replace("www.", "")
            normalized = normalized.rstrip("/")
            # Remove http/https if present
            normalized = re.sub(r"^https?://", "", normalized)
            return normalized
        return value

    # Date range fields (days, months, hours)
    if any(x in field_name for x in ["_days", "_months", "_hours", "_window"]):
        if isinstance(value, str):
            # Extract first number
            match = re.search(r"\d+", value)
            if match:
                return int(match.group())
        return value

    # List fields: sort and dedupe
    if isinstance(value, list):
        # Only sort if all elements are strings
        if all(isinstance(x, str) for x in value):
            return sorted(set(value))
        return value

    # String fields: strip whitespace
    if isinstance(value, str):
        return value.strip()

    # Pass through everything else
    return value


def are_values_equivalent(field_name: str, value1: Any, value2: Any) -> bool:
    """
    Check if two values are semantically equivalent after normalization.
    """
    norm1 = normalize_value(field_name, value1)
    norm2 = normalize_value(field_name, value2)

    if norm1 == norm2:
        return True

    # Handle list comparison (order-independent)
    if isinstance(norm1, list) and isinstance(norm2, list):
        return set(norm1) == set(norm2)

    return False
