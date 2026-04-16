"""Phase 4: Supersession application with 3 triggers."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from reconciliation_v2.pipeline.value_collection import FieldValues, CollectedValue
from reconciliation_v2.pipeline.canonicalize import values_are_equivalent


@dataclass
class SupersessionResult:
    """Result of supersession analysis."""

    # Values that passed supersession checks (not zeroed out)
    active_values: list[CollectedValue] = field(default_factory=list)

    # Values that were superseded (zeroed out)
    superseded_values: list[CollectedValue] = field(default_factory=list)

    # Reasons for supersession
    supersession_reasons: list[str] = field(default_factory=list)

    # Policy update date if detected
    policy_update_date: date | None = None


def parse_policy_date(value: Any) -> date | None:
    """
    Parse a policy update date from various formats.

    Examples:
    - "January 2026" -> date(2026, 1, 1)
    - "November 2025" -> date(2025, 11, 1)
    - "2026-01-15" -> date(2026, 1, 15)
    """
    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        return None

    # Try ISO format first
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Try "Month Year" format
    month_year_match = re.match(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
        value,
        re.IGNORECASE,
    )
    if month_year_match:
        month_name = month_year_match.group(1)
        year = int(month_year_match.group(2))
        month_map = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
        }
        month = month_map.get(month_name.lower(), 1)
        return date(year, month, 1)

    # Try "Month YYYY" with short month names
    short_month_match = re.match(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})",
        value,
        re.IGNORECASE,
    )
    if short_month_match:
        month_name = short_month_match.group(1).lower()
        year = int(short_month_match.group(2))
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4,
            "may": 5, "jun": 6, "jul": 7, "aug": 8,
            "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        month = month_map.get(month_name, 1)
        return date(year, month, 1)

    return None


def extract_version_info(value: str) -> tuple[str, int | None]:
    """
    Extract base value and version year from versioned strings.

    Only matches explicit version patterns to avoid false positives:
    - 4-digit year (2020-2029): "AET-PA-2025" -> ("AET-PA", 2025)
    - 2-digit year (20-29 only): "AET-PA-25" -> ("AET-PA", 2025)

    Does NOT match:
    - Random numbers: "PA-1847" (not a version)
    - Old years: "FORM-2001" (unlikely to be current version)

    Returns: (base_value, version_year) tuple
    """
    if not isinstance(value, str):
        return (str(value), None)

    # Pattern 1: 4-digit year in 2020-2029 range (current versions)
    match = re.match(r'^(.+?)[-_](202\d)$', value)
    if match:
        return (match.group(1), int(match.group(2)))

    # Pattern 2: 2-digit year 20-29 only (shorthand for 2020s)
    # Must have a separator before it to avoid matching random numbers
    match = re.match(r'^(.+?)[-_](2[0-9])$', value)
    if match:
        year_suffix = int(match.group(2))
        full_year = 2000 + year_suffix
        return (match.group(1), full_year)

    return (value, None)


def apply_supersession(field_values: FieldValues) -> SupersessionResult:
    """
    Apply all four supersession triggers:

    1. {X, X_old} pair: X_old value is deprecated
    2. X_old_status: Explains why X_old is deprecated
    3. X_policy_update: Zero out ANY source dated BEFORE the policy date
    4. Version supersession: When values differ only by version suffix (e.g., -2024 vs -2025),
       the newer version supersedes the older

    The third trigger handles cases where a phone rep postdates the policy update but
    contradicts it. For example:
    - Field X has X_policy_update = "November 2025"
    - Provider manual (pre-policy) says value A
    - Web page (policy date) says value B + has X_policy_update
    - Phone rep (post-policy) says value A (wrong - rep has stale information)
    - Denial letter (post-policy) says value B

    The policy_update trigger zeroes out sources dated BEFORE the policy date.
    Sources AFTER are kept but must compete on scoring. The web page that HAS
    the X_policy_update field gets a scoring boost. Authority weights handle
    denial_letter > phone_transcript, so the correct value wins.

    Implementation:
    1. Zero out sources dated BEFORE X_policy_update date
    2. Sources that HAVE the X_policy_update field get a scoring boost (handled in scoring)
    3. Authority weights handle remaining conflicts
    4. For versioned values, older versions are superseded by newer versions
    """
    result = SupersessionResult()

    # Start with all values as active
    active_values = list(field_values.values)

    # Trigger 1 & 2: {X, X_old} pair and X_old_status
    # Mark values matching X_old as superseded
    deprecated_canonicals = set()

    for old_val in field_values.old_values:
        deprecated_canonicals.add(old_val.canonical)
        result.supersession_reasons.append(
            f"Value '{old_val.value}' deprecated by *_old field in {old_val.source_id}"
        )

    # X_old_status provides explanation
    for status_val in field_values.old_status:
        result.supersession_reasons.append(
            f"Deprecation reason: {status_val.value}"
        )

    # Trigger 3: X_policy_update - zero out sources before policy date
    policy_date = None
    policy_source_id = None

    for pu_val in field_values.policy_updates:
        parsed_date = parse_policy_date(pu_val.value)
        if parsed_date:
            if policy_date is None or parsed_date > policy_date:
                policy_date = parsed_date
                policy_source_id = pu_val.source_id
                result.policy_update_date = policy_date

    # Trigger 4: Version supersession
    # Group values by their base (non-version part) and find which versions exist
    version_groups: dict[str, list[tuple[CollectedValue, int]]] = {}
    for val in active_values:
        base, version_year = extract_version_info(str(val.value))
        if version_year is not None:
            if base not in version_groups:
                version_groups[base] = []
            version_groups[base].append((val, version_year))

    # For each version group, mark older versions as superseded
    version_superseded: set[str] = set()  # source_id + value combos to supersede
    for base, versioned_vals in version_groups.items():
        if len(versioned_vals) > 1:
            # Find the newest version year
            max_year = max(v[1] for v in versioned_vals)
            newest_vals = [(v, y) for v, y in versioned_vals if y == max_year]

            # Mark older versions as superseded
            for val, year in versioned_vals:
                if year < max_year:
                    version_superseded.add(f"{val.source_id}:{val.value}")
                    result.supersession_reasons.append(
                        f"Version {val.value} ({year}) superseded by newer version ({max_year})"
                    )

    # Apply supersession
    still_active = []

    for val in active_values:
        superseded = False
        reason = None

        # Check if value matches a deprecated canonical
        if val.canonical in deprecated_canonicals:
            superseded = True
            reason = f"Value matches deprecated *_old value"

        # Check if source predates policy update
        elif policy_date and val.source_date < policy_date:
            superseded = True
            reason = f"Source {val.source_id} ({val.source_date}) predates policy update ({policy_date})"

        # Check if this is an older version (version supersession)
        elif f"{val.source_id}:{val.value}" in version_superseded:
            superseded = True
            # Reason already added in version detection loop

        if superseded:
            result.superseded_values.append(val)
            if reason:
                result.supersession_reasons.append(reason)
        else:
            still_active.append(val)

    result.active_values = still_active

    # If policy_update exists, note which source has it (for scoring boost)
    if policy_source_id:
        result.supersession_reasons.append(
            f"Policy update ({policy_date}) found in source {policy_source_id}"
        )

    return result
