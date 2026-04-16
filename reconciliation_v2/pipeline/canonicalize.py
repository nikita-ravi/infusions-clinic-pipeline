"""Per-value-type canonicalization for equality comparison (not storage)."""

import re
from datetime import date, datetime
from typing import Any


def get_value_type(field_name: str, value: Any) -> str:
    """Infer the value type from field name and value."""
    if value is None:
        return "null"

    # Phone/fax fields
    if any(kw in field_name for kw in ["phone", "fax"]):
        if isinstance(value, str):
            return "phone"

    # URL fields
    if any(kw in field_name for kw in ["url", "portal"]):
        if isinstance(value, str) and not field_name.endswith("_note"):
            return "url"

    # Date fields
    if "date" in field_name:
        return "date"

    # Numeric fields (days, hours, months)
    if any(kw in field_name for kw in ["_days", "_hours", "_months"]):
        if isinstance(value, (int, float)):
            return "int"
        if isinstance(value, str):
            # Could be "7-10" or "7-10 (during transition)"
            return "string"  # Don't try to extract, preserve as-is

    # Lists
    if isinstance(value, list):
        return "list"

    # Dicts
    if isinstance(value, dict):
        return "dict"

    # Integers
    if isinstance(value, int):
        return "int"

    # Floats
    if isinstance(value, float):
        return "float"

    # Default to string
    return "string"


def canonicalize_for_equality(field_name: str, value: Any) -> Any:
    """
    Canonicalize a value for equality comparison only.

    This is used to detect conflicts - same logical value expressed differently.
    The original value is always preserved for storage/output.

    Rules:
    - phone: digits only (ignores formatting, options)
    - url: lowercase + strip protocol/www
    - string: exact match
    - int: exact
    - date: parsed to date object
    - list: sorted tuple for hashability
    - dict: sorted tuple of items
    """
    if value is None:
        return None

    value_type = get_value_type(field_name, value)

    if value_type == "phone":
        # Extract just the base phone number, ignoring IVR options
        # First, try to extract the phone number pattern before any "Option" or comma
        phone_str = str(value)
        # Match phone pattern: (XXX) XXX-XXXX or XXX-XXX-XXXX
        phone_match = re.match(r'^[\(\s]*(\d{3})[\)\s\-\.]*(\d{3})[\s\-\.]*(\d{4})', phone_str)
        if phone_match:
            return phone_match.group(1) + phone_match.group(2) + phone_match.group(3)
        # Fallback: extract first 10 digits
        digits = re.sub(r"\D", "", phone_str)
        return digits[:10] if len(digits) >= 10 else digits

    if value_type == "url":
        url = str(value).lower()
        # Strip protocol
        url = re.sub(r"^https?://", "", url)
        # Strip www.
        url = re.sub(r"^www\.", "", url)
        # Strip trailing slash
        url = url.rstrip("/")
        return url

    if value_type == "date":
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            # Try to parse common date formats
            for fmt in ["%Y-%m-%d", "%B %Y", "%B %d, %Y", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
            # Return as string if can't parse
            return value.lower().strip()
        return value

    if value_type == "int":
        return int(value)

    if value_type == "float":
        return float(value)

    if value_type == "list":
        # Sort for comparison, convert to tuple for hashability
        try:
            return tuple(sorted(str(x) for x in value))
        except TypeError:
            return tuple(str(x) for x in value)

    if value_type == "dict":
        # Convert to sorted tuple of items for hashability
        try:
            return tuple(sorted((str(k), str(v)) for k, v in value.items()))
        except TypeError:
            return tuple((str(k), str(v)) for k, v in value.items())

    # String: exact match (stripped)
    if isinstance(value, str):
        return value.strip()

    return value


def values_are_equivalent(field_name: str, value1: Any, value2: Any) -> bool:
    """Check if two values are equivalent after canonicalization."""
    canon1 = canonicalize_for_equality(field_name, value1)
    canon2 = canonicalize_for_equality(field_name, value2)
    return canon1 == canon2
