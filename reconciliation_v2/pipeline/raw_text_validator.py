"""Cross-validate JSON extracted data against raw .txt source files."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RawTextEvidence:
    """Evidence extracted directly from raw .txt file."""
    source_type: str
    file_path: str
    phone_numbers: list[str] = field(default_factory=list)
    fax_numbers: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    form_codes: list[str] = field(default_factory=list)
    day_values: dict[str, list[int]] = field(default_factory=dict)  # context -> values
    raw_text: str = ""


@dataclass
class ValidationResult:
    """Result of cross-validating JSON against raw text."""
    field_name: str
    json_value: str
    found_in_raw: bool
    raw_matches: list[str] = field(default_factory=list)
    confidence_adjustment: float = 0.0  # negative if conflict
    note: str = ""


def load_raw_text(payer_dir: Path, source_type: str) -> RawTextEvidence | None:
    """Load and parse a raw .txt file for a payer."""
    file_map = {
        "provider_manual": "provider_manual.txt",
        "phone_transcript": "phone_transcript.txt",
        "web_page": "web_page.txt",
        "denial_letter": "denial_letter.txt",
    }

    filename = file_map.get(source_type)
    if not filename:
        return None

    file_path = payer_dir / filename
    if not file_path.exists():
        return None

    raw_text = file_path.read_text()

    evidence = RawTextEvidence(
        source_type=source_type,
        file_path=str(file_path),
        raw_text=raw_text,
    )

    # Extract phone/fax numbers (various formats)
    phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    all_numbers = re.findall(phone_pattern, raw_text)

    # Normalize numbers
    for num in all_numbers:
        normalized = re.sub(r'[^\d]', '', num)
        formatted = f"({normalized[:3]}) {normalized[3:6]}-{normalized[6:]}"

        # Check context for fax vs phone
        # Look for "fax" within 50 chars before the number
        num_pos = raw_text.find(num)
        context_start = max(0, num_pos - 50)
        context = raw_text[context_start:num_pos].lower()

        if 'fax' in context:
            if formatted not in evidence.fax_numbers:
                evidence.fax_numbers.append(formatted)
        else:
            if formatted not in evidence.phone_numbers:
                evidence.phone_numbers.append(formatted)

    # Extract URLs
    url_pattern = r'(?:https?://)?(?:www\.)?[\w.-]+\.(?:com|org|net|gov)(?:/[\w.-]*)*'
    urls = re.findall(url_pattern, raw_text, re.IGNORECASE)
    evidence.urls = list(set(urls))

    # Extract form codes (patterns like ANT-MED-PA-25, HUM-AUTH-2026, AET-PA-2025)
    # Captures: 2-5 letters, optionally followed by more letter segments, ending in 2-4 digits
    form_pattern = r'\b([A-Z]{2,5}(?:[-_][A-Z]{2,5})*[-_]\d{2,4})\b'
    forms = re.findall(form_pattern, raw_text, re.IGNORECASE)
    evidence.form_codes = list(set(f.upper() for f in forms))

    # Extract day values with context
    day_patterns = [
        (r'(\d+)\s*(?:business\s+)?days?', 'days'),
        (r'(\d+)\s*hours?', 'hours'),
        (r'within\s+(\d+)\s*days?', 'window_days'),
        (r'(\d+)[-–](\d+)\s*(?:business\s+)?days?', 'day_range'),
    ]

    for pattern, context_key in day_patterns:
        matches = re.findall(pattern, raw_text, re.IGNORECASE)
        if matches:
            if context_key == 'day_range':
                # Store as tuples for ranges
                evidence.day_values[context_key] = [(int(m[0]), int(m[1])) for m in matches]
            else:
                evidence.day_values[context_key] = [int(m) if isinstance(m, str) else int(m[0]) for m in matches]

    return evidence


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to digits only.

    Handles phone numbers with IVR menu options like:
    "(800) 624-0756, Option 3, Option 1" -> extracts just the phone number part
    """
    phone_str = str(phone)

    # First, try to extract just the phone number part (before any "Option" or comma)
    # Pattern: matches phone numbers like (800) 624-0756 or 800-624-0756
    phone_match = re.match(r'^[\(\s]*(\d{3})[\)\s\-\.]*(\d{3})[\s\-\.]*(\d{4})', phone_str)
    if phone_match:
        return phone_match.group(1) + phone_match.group(2) + phone_match.group(3)

    # Fallback: extract first 10 consecutive digits
    digits = re.sub(r'[^\d]', '', phone_str)
    if len(digits) >= 10:
        return digits[:10]

    return digits


def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    url = url.lower().strip()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    url = url.rstrip('/')
    return url


def cross_validate_field(
    field_name: str,
    json_value: any,
    raw_evidence: list[RawTextEvidence],
    source_type: str | None = None,
) -> ValidationResult:
    """Cross-validate a JSON field value against raw text evidence."""

    result = ValidationResult(
        field_name=field_name,
        json_value=str(json_value),
        found_in_raw=False,
    )

    # Skip validation for list/dict fields - these are complex structures
    # that don't map directly to raw text patterns
    if isinstance(json_value, (list, dict)):
        result.note = "Skipped validation for complex type (list/dict)"
        result.confidence_adjustment = 0.0  # No penalty, not applicable
        return result

    # Filter to specific source if provided
    evidence_list = raw_evidence
    if source_type:
        evidence_list = [e for e in raw_evidence if e.source_type == source_type]

    if not evidence_list:
        result.note = "No raw text available for validation"
        return result

    # Validate based on field type
    # Note: phone_hours is operating hours, not a phone number - exclude it
    field_lower = field_name.lower()
    is_phone_field = ('fax' in field_lower or 'phone' in field_lower) and 'hours' not in field_lower
    if is_phone_field:
        normalized_json = normalize_phone(json_value)
        for evidence in evidence_list:
            all_numbers = evidence.fax_numbers + evidence.phone_numbers
            for num in all_numbers:
                if normalize_phone(num) == normalized_json:
                    result.found_in_raw = True
                    result.raw_matches.append(num)

        if not result.found_in_raw:
            result.confidence_adjustment = -0.15
            result.note = f"Phone/fax {json_value} not found in raw text"

    elif 'url' in field_name.lower() or 'portal' in field_name.lower():
        normalized_json = normalize_url(str(json_value))
        for evidence in evidence_list:
            for url in evidence.urls:
                if normalize_url(url) == normalized_json:
                    result.found_in_raw = True
                    result.raw_matches.append(url)

        if not result.found_in_raw:
            result.confidence_adjustment = -0.10
            result.note = f"URL {json_value} not found in raw text"

    elif 'form' in field_name.lower() or field_name == 'pa_form':
        json_form = str(json_value).upper().replace('-', '').replace('_', '')
        for evidence in evidence_list:
            for form in evidence.form_codes:
                normalized_form = form.replace('-', '').replace('_', '')
                if normalized_form == json_form:
                    result.found_in_raw = True
                    result.raw_matches.append(form)

        if not result.found_in_raw:
            result.confidence_adjustment = -0.10
            result.note = f"Form code {json_value} not found in raw text"

    elif 'days' in field_name.lower() or 'window' in field_name.lower() or 'hours' in field_name.lower():
        try:
            json_val = int(json_value)
            for evidence in evidence_list:
                # First check pre-extracted day values
                all_days = evidence.day_values.get('days', []) + evidence.day_values.get('window_days', [])
                if json_val in all_days:
                    result.found_in_raw = True
                    result.raw_matches.append(str(json_val))
                    break

                # Also search raw text directly for various patterns
                # Patterns: "90 days", "90-day", "within 90", "90 business days", etc.
                day_patterns = [
                    rf'\b{json_val}\s*days?\b',           # "90 days" or "90 day"
                    rf'\b{json_val}-day\b',               # "90-day"
                    rf'within\s+{json_val}\b',            # "within 90"
                    rf'\b{json_val}\s*business\s*days?\b', # "90 business days"
                    rf'\b{json_val}\s*hours?\b',          # "24 hours" or "24 hour"
                ]
                for pattern in day_patterns:
                    if re.search(pattern, evidence.raw_text, re.IGNORECASE):
                        result.found_in_raw = True
                        result.raw_matches.append(str(json_val))
                        break
                if result.found_in_raw:
                    break
        except (ValueError, TypeError):
            pass

        if not result.found_in_raw:
            result.confidence_adjustment = -0.05
            result.note = f"Day value {json_value} not confirmed in raw text"

    else:
        # For other fields, check if value appears in raw text
        json_str = str(json_value).lower()
        for evidence in evidence_list:
            if json_str in evidence.raw_text.lower():
                result.found_in_raw = True
                result.raw_matches.append(json_str)

    if result.found_in_raw:
        result.confidence_adjustment = 0.05  # Small boost for validation
        result.note = f"Validated against raw text"

    return result


def load_all_raw_evidence(payer_key: str, base_path: Path = None) -> list[RawTextEvidence]:
    """Load raw text evidence for all source types of a payer."""
    if base_path is None:
        base_path = Path("payer_sources")

    payer_dir = base_path / payer_key
    if not payer_dir.exists():
        return []

    evidence = []
    for source_type in ["provider_manual", "phone_transcript", "web_page", "denial_letter"]:
        raw = load_raw_text(payer_dir, source_type)
        if raw:
            evidence.append(raw)

    return evidence


def validate_source_record(
    source_data: dict,
    source_type: str,
    raw_evidence: list[RawTextEvidence],
) -> dict[str, ValidationResult]:
    """Validate all fields in a source record against raw text."""
    results = {}

    # Key fields to validate
    key_fields = [
        'fax_number', 'fax_number_old', 'phone_status', 'phone_urgent',
        'portal_url', 'pa_form', 'chart_note_window_days',
        'turnaround_standard_days', 'turnaround_urgent_hours',
        'appeal_fax', 'appeal_phone',
    ]

    for field_name in key_fields:
        if field_name in source_data and source_data[field_name] is not None:
            result = cross_validate_field(
                field_name,
                source_data[field_name],
                raw_evidence,
                source_type,
            )
            results[field_name] = result

    return results
