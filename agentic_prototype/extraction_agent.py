"""
Agentic Extraction Agent (v3 - with cross-payer isolation and corrective validation)

Takes raw source files (provider manuals, phone transcripts, etc.) and extracts
structured PA route data using an LLM.

Key improvements over v2:
1. Payer isolation - explicit prompt instructions to prevent cross-payer contamination
2. Field disambiguation - clear distinction between turnaround, chart_note_window, auth_period
3. Drug field extraction - explicit instructions to extract auth_period_months, step_therapy
4. URL validation - portal_url must be valid URL format (not bare name)
5. Corrective validation - bad values are corrected/removed, not just logged
6. Cross-payer drug detection - removes drugs not found in source text

v2 features (retained):
- Source phrase grounding - every field must cite its source phrase
- Pattern validation - form codes, phone numbers must match regex
- Enum fields - biosimilar_requirement instead of two booleans
- Post-extraction validation - verify source phrases exist in raw text
"""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic

# =============================================================================
# PATTERN VALIDATORS
# =============================================================================

# PA form codes like AET-PA-2025, CG-PA-002, UHC-PA-200, ANT-MED-PA-25
PA_FORM_PATTERN = re.compile(r'^[A-Z]{2,5}(-[A-Z]{2,5})*-\d{2,4}$')

# Phone/fax numbers like (800) 267-3300, 800-267-3300, (844) 405-0296
PHONE_PATTERN = re.compile(r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')

# Phone hours like M-F 8am-5pm EST, M-F 8am-6pm local time
PHONE_HOURS_PATTERN = re.compile(r'M-F\s+\d{1,2}(am|pm)-\d{1,2}(am|pm)\s*(EST|CST|PST|local|local time)?', re.IGNORECASE)

# URL pattern - must start with www. or http(s):// OR be a domain like "anthem.com/providers"
URL_PATTERN = re.compile(r'^(https?://|www\.)?[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(/.*)?$', re.IGNORECASE)

# Turnaround value sanity check - turnaround should be < 30 days typically
# Values >= 60 are likely chart_note_window_days being confused
TURNAROUND_MAX_DAYS = 30


def validate_pattern(field_name: str, value: str, raw_text: str) -> tuple[bool, str]:
    """
    Validate a field value against its expected pattern and presence in raw text.
    Returns (is_valid, reason).
    """
    if value is None:
        return True, "null is valid"

    value_str = str(value)

    # Check pattern based on field type
    if field_name == 'pa_form':
        if not PA_FORM_PATTERN.match(value_str):
            return False, f"'{value_str}' doesn't match PA form pattern (e.g., AET-PA-2025)"

    elif field_name in ['fax_number', 'phone', 'appeal_fax', 'appeal_phone']:
        # Extract just the phone number part (before commas for options)
        phone_part = value_str.split(',')[0].strip()
        if not PHONE_PATTERN.match(phone_part):
            return False, f"'{phone_part}' doesn't match phone number pattern"

    elif field_name == 'phone_hours':
        if not PHONE_HOURS_PATTERN.search(value_str):
            return False, f"'{value_str}' doesn't match phone hours pattern"
        # Also verify it appears in raw text (critical for hallucination detection)
        if value_str not in raw_text:
            # Try normalized comparison
            normalized_value = value_str.lower().replace(" ", "")
            normalized_raw = raw_text.lower().replace(" ", "")
            if normalized_value not in normalized_raw:
                return False, f"'{value_str}' not found in raw text (hallucinated)"

    return True, "valid"


# =============================================================================
# SCHEMA WITH SOURCE PHRASE REQUIREMENT
# =============================================================================

PA_ROUTE_SCHEMA = """
{
  "fax_number": {"value": "string (phone format)", "source_phrase": "exact substring from source"},
  "fax_number_old": {"value": "string or null", "source_phrase": "exact substring or null"},
  "phone": {"value": "string (phone format)", "source_phrase": "exact substring from source"},
  "phone_hours": {"value": "string like 'M-F 8am-5pm EST' or null", "source_phrase": "exact substring or null"},
  "portal_url": {"value": "string (URL or domain like anthem.com/providers)", "source_phrase": "exact substring from source"},
  "turnaround_standard_days": {"value": "number or string", "source_phrase": "exact substring from source"},
  "turnaround_urgent_hours": {"value": "number", "source_phrase": "exact substring from source"},
  "turnaround_portal_days": {"value": "number or string or null", "source_phrase": "turnaround specific to portal submissions"},
  "turnaround_fax_days": {"value": "number or string or null", "source_phrase": "turnaround specific to fax submissions"},
  "chart_note_window_days": {"value": "number", "source_phrase": "exact substring from source"},
  "pa_form": {"value": "string matching pattern like AET-PA-2025 or CG-PA-002", "source_phrase": "exact substring"},
  "pa_form_old": {"value": "string or null", "source_phrase": "exact substring or null"},
  "appeal_fax": {"value": "string (phone format)", "source_phrase": "exact substring from source"},
  "appeal_phone": {"value": "string INCLUDING Option number if present", "source_phrase": "exact substring from source"},
  "appeal_mail": {"value": "string (mailing address) or null", "source_phrase": "exact substring from source"},
  "appeal_deadline_days": {"value": "number", "source_phrase": "exact substring from source"},
  "drugs": {
    "DrugName": {
      "auth_period_months": {"value": "number - USE INITIAL PERIOD if both initial and renewal given", "source_phrase": "substring"},
      "auth_period_initial_months": {"value": "number or null", "source_phrase": "substring or null"},
      "auth_period_renewal_months": {"value": "number or null", "source_phrase": "substring or null"},
      "step_therapy_required": {"value": "boolean", "source_phrase": "substring that justifies this"},
      "prior_treatment_failure_required": {"value": "boolean", "source_phrase": "substring"},
      "biosimilar_requirement": {"value": "one of: 'required', 'preferred', 'none', 'not_stated'", "source_phrase": "substring"},
      "specialist_required": {"value": "boolean", "source_phrase": "substring"},
      "specific_testing": [{"value": "string", "source_phrase": "substring"}],
      "diagnosis_restrictions": [{"value": "string", "source_phrase": "substring"}],
      "notes": "string with other requirements verbatim from source"
    }
  },
  "system_migration_in_progress": {"value": "boolean", "source_phrase": "substring mentioning migration"},
  "phone_experience_note": {"value": "string or null", "source_phrase": "exact substring or null"}
}

IMPORTANT:
- Use Title Case for drug names: Remicade, Entyvio, Keytruda, Tysabri, Rituxan, Herceptin, Ocrevus
- pa_form must match pattern like AET-PA-2025, CG-PA-002, UHC-PA-200 (NOT portal names like 'Availity')
- phone_hours MUST be copied exactly from source text, not inferred
- appeal_phone: INCLUDE the full string with "Option X" if present (e.g., "(800) 274-7767, Option 5")
"""

EXTRACTION_PROMPT = """You are a PA route data extraction agent. Extract structured data from the following source document.

SOURCE TYPE: {source_type}
SOURCE DATE: {source_date}
PAYER: {payer}

=== RAW SOURCE TEXT ===
{raw_text}
=== END SOURCE TEXT ===

Extract all PA route information into this JSON schema:
{schema}

CRITICAL RULES - FOLLOW EXACTLY:

1. SOURCE PHRASE GROUNDING (MOST IMPORTANT):
   - For EVERY field you extract, you MUST provide the exact source_phrase from the text
   - The source_phrase must be a VERBATIM substring that appears in the source text
   - If you cannot find a verbatim substring to justify a value, output null for that field
   - DO NOT infer values from general knowledge about how PA departments typically operate

2. PAYER ISOLATION (CRITICAL - PREVENT CROSS-CONTAMINATION):
   - You are extracting data for {payer} ONLY
   - DO NOT include ANY information from your training data about other payers
   - DO NOT include drug requirements, form codes, or policies from other payers
   - If a drug is not explicitly mentioned in THIS source document, DO NOT include it
   - If you're unsure whether information is from THIS payer, output null

3. FIELD DISAMBIGUATION (CRITICAL - PREVENT VALUE CONFUSION):
   - turnaround_standard_days: How long until the payer RESPONDS to a PA request (e.g., 7 days, 10-12 days)
   - turnaround_urgent_hours: Urgent request response time (e.g., 24 hours, 48 hours)
   - chart_note_window_days: How OLD chart notes can be when submitted (e.g., 90 days, 60 days)
   - auth_period_months: How long an APPROVAL lasts once granted (e.g., 6 months, 12 months)
   - THESE ARE COMPLETELY DIFFERENT CONCEPTS - DO NOT CONFUSE THEM:
     * "90-day chart notes" → chart_note_window_days: 90 (NOT turnaround)
     * "7 business days turnaround" → turnaround_standard_days: 7 (NOT chart_note_window)
     * "6 month authorization" → auth_period_months: 6 (this is approval duration)

4. DRUG FIELD EXTRACTION (CRITICAL - EXTRACT ALL STRUCTURED FIELDS):
   For EACH drug mentioned, you MUST extract ALL of these fields if present:
   - auth_period_months: The number from "X month authorization" or "auth period: X months"
   - auth_period_initial_months: Initial auth period if specified separately
   - auth_period_renewal_months: Renewal auth period if specified separately
   - step_therapy_required: true if text says "step therapy", "must try X first", "fail X first"
   - prior_treatment_failure_required: true if text says "failure required", "must fail"
   - biosimilar_requirement: "required"/"preferred"/"none"/"not_stated"
   - specialist_required: true if text says "specialist must submit", "oncologist required"
   - specific_testing: List tests like "CD20+", "HER2", "PD-L1", "JCV antibody"
   - diagnosis_restrictions: List diagnoses like "RA only", "Crohn's disease", "MS"

   IMPORTANT: Look for these values in BOTH the notes field AND structured fields.
   Example: If source says "Rituxan: auth_period_months: 6, step_therapy_required: true"
   Extract BOTH values - do not drop structured fields.

5. PA FORM CODE VALIDATION:
   - pa_form must match the pattern: 2-5 uppercase letters, hyphen, more letters/numbers
   - Valid examples: AET-PA-2025, CG-PA-002, UHC-PA-200, ANT-MED-PA-25, HUM-AUTH-2026
   - INVALID: "Availity", "online form", "standard form", portal names
   - If the source doesn't contain a valid form code pattern, return null

6. URL EXTRACTION (CRITICAL):
   - portal_url MUST be a valid URL starting with "www." or "http"
   - Examples: "www.availity.com", "www.cignaforhcp.com", "https://portal.example.com"
   - INVALID: Just the name like "Availity", "CignaforHCP", "Humana portal"
   - If source only mentions the portal NAME without full URL, return null for portal_url

7. PHONE HOURS - NO HALLUCINATION:
   - ONLY extract phone_hours if the EXACT hours string appears in the source text
   - Copy the hours EXACTLY as written (including timezone)
   - If no hours are explicitly stated, return null - DO NOT guess typical business hours

8. DRUG NAME NORMALIZATION:
   - Always use Title Case: "Remicade" not "REMICADE" or "remicade"
   - Remove generic names in parentheses: "Remicade" not "REMICADE (infliximab)"
   - Standard names: Remicade, Entyvio, Keytruda, Tysabri, Rituxan, Herceptin, Ocrevus, Humira

9. BIOSIMILAR REQUIREMENT (CRITICAL - READ CAREFULLY):
   - Use biosimilar_requirement with ONE of these values:
     - "required": ONLY if text says "biosimilar required", "must try biosimilar first", "biosimilar trial required", "biosimilar attestation required"
     - "preferred": if text says "biosimilar preferred", "biosimilar recommended", "prefer biosimilar"
     - "none": text explicitly says biosimilar NOT required
     - "not_stated": text doesn't mention biosimilar requirements
   - IMPORTANT: "preferred" is NOT the same as "required"!
     "biosimilar preferred for new starts" → "preferred" (NOT "required")
     "must trial biosimilar" → "required"

10. SYSTEM MIGRATION (STRICT DETECTION):
    - ONLY set to true if text contains the word "migration" or "migrating"
    - DO NOT set to true for "transition" alone - a fax number transition is NOT a system migration
    - source_phrase must contain "migration" or "migrating"
    - If no explicit migration keyword in this source, set to false

11. AUTH PERIOD (INITIAL vs RENEWAL):
    - If text has BOTH initial and renewal periods (e.g., "Initial: 6 months. Renewal: 12 months"):
      - auth_period_months = the INITIAL period (6 in this example)
      - auth_period_initial_months = the initial period
      - auth_period_renewal_months = the renewal period
    - This is critical: new PAs need the initial period, not renewal

12. PORTAL URL (FLEXIBLE FORMAT):
    - Accept URLs with or without "www." prefix
    - Valid formats: "www.availity.com", "anthem.com/providers", "https://portal.example.com"
    - If source says "Availity" without URL, check if full URL appears elsewhere in source
    - Only return null if NO URL or domain reference exists

13. APPEAL PHONE (PRESERVE OPTIONS):
    - Include the FULL string including "Option X" suffixes
    - Example: "(800) 274-7767, Option 5" - include the ", Option 5" part
    - This is critical for routing to the correct department

14. TURNAROUND BY SUBMISSION METHOD:
    - If source lists DIFFERENT turnarounds for portal vs fax, capture BOTH:
      - turnaround_portal_days: turnaround for portal submissions
      - turnaround_fax_days: turnaround for fax submissions
      - turnaround_standard_days: the general/stated policy turnaround

11. POLICY VS PATIENT-SPECIFIC INFO:
    - Drug requirements are POLICIES that apply to ALL patients
    - EXCLUDE: specific dosages for specific patients, patient dates, individual denial reasons
    - INCLUDE: authorization periods, step therapy, testing requirements, specialist requirements

Respond with valid JSON only. No markdown, no explanation.
"""


# =============================================================================
# NORMALIZATION AND VALIDATION FUNCTIONS
# =============================================================================

def _extract_drug_section_for_validation(drug_name: str, raw_text: str) -> str:
    """Extract the section of raw text that pertains to a specific drug."""
    lines = raw_text.split('\n')
    drug_upper = drug_name.upper()
    drug_section = []
    in_section = False

    for line in lines:
        # Check if this line starts a drug section
        if drug_upper in line.upper():
            in_section = True
            drug_section = [line]
        elif in_section:
            # Continue collecting until we hit another major section or drug
            stripped = line.strip()
            if stripped.startswith('-') or stripped == '' or not stripped[0:1].isupper():
                drug_section.append(line)
            elif len(drug_section) > 1:
                # We have content, stop at next major header
                break
            else:
                drug_section.append(line)

    return '\n'.join(drug_section)


def _extract_auth_period_from_text(text: str) -> int | None:
    """Extract auth_period_months from text using regex patterns."""
    text_lower = text.lower()

    # Pattern: "X month authorization" or "authorization period: X months"
    patterns = [
        r'(\d+)\s*month\s*auth',
        r'auth[^\d]*(\d+)\s*month',
        r'authorization\s*period[:\s]*(\d+)',
        r'auth_period_months[:\s]*(\d+)',
        r'(\d+)\s*months?\s*\(?auth',
    ]

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return int(match.group(1))

    return None


def _detect_step_therapy(text: str) -> bool:
    """Detect if step therapy is required from text."""
    text_lower = text.lower()
    step_therapy_phrases = [
        'step therapy',
        'step_therapy_required: true',
        'step_therapy_required":true',
        'step_therapy_required": true',
        'must try',
        'must fail',
        'try first',
        'fail first',
        'prior treatment failure',
        'failed previous',
    ]
    return any(phrase in text_lower for phrase in step_therapy_phrases)


def _detect_biosimilar_requirement(text: str) -> str | None:
    """Detect biosimilar requirement from text."""
    text_lower = text.lower()

    # Check for required
    required_phrases = [
        'biosimilar required',
        'biosimilar trial required',
        'must try biosimilar',
        'biosimilar attestation required',
        'biosimilar step therapy required',
    ]
    if any(phrase in text_lower for phrase in required_phrases):
        return 'required'

    # Check for preferred
    preferred_phrases = [
        'biosimilar preferred',
        'biosimilar recommended',
        'prefer biosimilar',
    ]
    if any(phrase in text_lower for phrase in preferred_phrases):
        return 'preferred'

    return None


def normalize_drug_name(name: str) -> str:
    """Normalize drug name to Title Case and remove generic names."""
    if '(' in name:
        name = name.split('(')[0].strip()

    for suffix in [' IV', ' SC', ' mg', ' mcg', ' 440', ' 100', ' 200']:
        if suffix in name:
            name = name.split(suffix)[0].strip()

    name_map = {
        'REMICADE': 'Remicade',
        'ENTYVIO': 'Entyvio',
        'KEYTRUDA': 'Keytruda',
        'TYSABRI': 'Tysabri',
        'RITUXAN': 'Rituxan',
        'HERCEPTIN': 'Herceptin',
        'OCREVUS': 'Ocrevus',
        'HUMIRA': 'Humira',
        'ENBREL': 'Enbrel',
        'AVASTIN': 'Avastin',
        'OPDIVO': 'Opdivo',
    }

    upper = name.upper().strip()
    if upper in name_map:
        return name_map[upper]

    return name.strip().title()


def extract_value_and_phrase(field_data):
    """Extract value and source_phrase from field data (handles both formats)."""
    if isinstance(field_data, dict) and 'value' in field_data:
        return field_data.get('value'), field_data.get('source_phrase')
    else:
        # Old format without source_phrase
        return field_data, None


def get_val(v):
    """Get the value from a nested dict or return as-is."""
    if isinstance(v, dict) and 'value' in v:
        return v['value']
    return v


def validate_source_phrase(source_phrase: str, raw_text: str) -> bool:
    """Check if source_phrase appears in raw_text (with some normalization)."""
    if not source_phrase:
        return False

    # Direct match
    if source_phrase in raw_text:
        return True

    # Normalized match (lowercase, reduced whitespace)
    normalized_phrase = ' '.join(source_phrase.lower().split())
    normalized_raw = ' '.join(raw_text.lower().split())

    if normalized_phrase in normalized_raw:
        return True

    # Try with just key parts (for phone numbers, numbers, etc.)
    # Extract numbers and check if they appear
    numbers = re.findall(r'\d+', source_phrase)
    if numbers and all(num in raw_text for num in numbers):
        return True

    return False


def post_process_extraction(extracted: dict, raw_text: str, payer: str = "") -> dict:
    """Post-process extraction to fix common issues and validate.

    CORRECTIVE VALIDATION: This function actively corrects bad values, not just logs them.
    """

    # Track validation failures
    validation_notes = []

    # ==========================================================================
    # 1. Normalize drug names
    # ==========================================================================
    if 'drugs' in extracted and isinstance(extracted['drugs'], dict):
        normalized_drugs = {}
        for drug_name, drug_data in extracted['drugs'].items():
            clean_name = normalize_drug_name(drug_name)

            if clean_name in normalized_drugs:
                existing = normalized_drugs[clean_name]
                for key, value in drug_data.items():
                    if value is not None and (key not in existing or existing[key] is None):
                        existing[key] = value
            else:
                normalized_drugs[clean_name] = drug_data

        extracted['drugs'] = normalized_drugs

    # ==========================================================================
    # 2. Validate pa_form pattern AND presence in raw text
    # ==========================================================================
    pa_form_data = extracted.get('pa_form')
    pa_form_value, pa_form_phrase = extract_value_and_phrase(pa_form_data)

    if pa_form_value:
        pa_form_str = str(pa_form_value)
        # Check pattern
        if not PA_FORM_PATTERN.match(pa_form_str):
            validation_notes.append(f"pa_form '{pa_form_str}' CORRECTED to null (doesn't match pattern)")
            extracted['pa_form'] = None
        # Also check presence in raw text
        elif pa_form_str not in raw_text:
            validation_notes.append(f"pa_form '{pa_form_str}' CORRECTED to null (not in raw text)")
            extracted['pa_form'] = None

    # ==========================================================================
    # 3. Validate portal_url - accept URLs and domain references
    # ==========================================================================
    portal_url_data = extracted.get('portal_url')
    portal_url_value, portal_url_phrase = extract_value_and_phrase(portal_url_data)

    if portal_url_value:
        portal_url_str = str(portal_url_value)
        # Check if it's a valid URL pattern (including domain-only like "anthem.com/providers")
        if URL_PATTERN.match(portal_url_str):
            # Valid URL format, keep it
            pass
        elif '.' in portal_url_str and '/' in portal_url_str:
            # Looks like a domain with path (e.g., "anthem.com/providers") - keep it
            validation_notes.append(f"portal_url '{portal_url_str}' kept (domain with path)")
        else:
            # Bare name like "Availity" or "CignaforHCP" - try to find full URL
            url_matches = re.findall(r'((?:www\.)?[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:/[^\s]*)?)', raw_text)
            if url_matches:
                portal_name_lower = portal_url_str.lower().replace(" ", "")
                found_url = None
                for url in url_matches:
                    if portal_name_lower in url.lower().replace(".", "").replace("/", ""):
                        found_url = url
                        break
                if found_url:
                    validation_notes.append(f"portal_url '{portal_url_str}' CORRECTED to '{found_url}'")
                    extracted['portal_url'] = found_url
                elif url_matches:
                    # Use first URL as fallback
                    validation_notes.append(f"portal_url '{portal_url_str}' CORRECTED to '{url_matches[0]}'")
                    extracted['portal_url'] = url_matches[0]
            else:
                # No URL found but we have a name - keep the name rather than nulling
                # An ops person can at least search for "Availity"
                validation_notes.append(f"portal_url '{portal_url_str}' kept (no full URL found, but name is useful)")

    # ==========================================================================
    # 4. Validate turnaround_standard_days - detect chart_note confusion
    # ==========================================================================
    turnaround_data = extracted.get('turnaround_standard_days')
    turnaround_value, turnaround_phrase = extract_value_and_phrase(turnaround_data)

    if turnaround_value is not None:
        try:
            turnaround_num = int(str(turnaround_value).split('-')[0].split()[0])
            if turnaround_num >= TURNAROUND_MAX_DAYS:
                # This is likely chart_note_window_days being confused
                # Check if 90 or 60 appears with "chart" or "note" context
                if any(f"{turnaround_num}" in phrase and ('chart' in phrase.lower() or 'note' in phrase.lower())
                       for phrase in [turnaround_phrase or "", raw_text]):
                    validation_notes.append(
                        f"turnaround_standard_days '{turnaround_value}' CORRECTED to null "
                        f"(value >= {TURNAROUND_MAX_DAYS} is likely chart_note_window_days confusion)"
                    )
                    extracted['turnaround_standard_days'] = None
                else:
                    validation_notes.append(
                        f"turnaround_standard_days '{turnaround_value}' FLAGGED (unusually high - verify not chart_note_window)"
                    )
        except (ValueError, TypeError):
            pass  # Non-numeric value, let it pass

    # ==========================================================================
    # 5. Validate phone_hours against raw text
    # ==========================================================================
    phone_hours_data = extracted.get('phone_hours')
    phone_hours_value, phone_hours_phrase = extract_value_and_phrase(phone_hours_data)

    if phone_hours_value:
        # Must appear in raw text
        if str(phone_hours_value) not in raw_text:
            # Try normalized
            normalized = str(phone_hours_value).lower().replace(" ", "")
            if normalized not in raw_text.lower().replace(" ", ""):
                validation_notes.append(f"phone_hours '{phone_hours_value}' CORRECTED to null (not in raw text)")
                extracted['phone_hours'] = None

    # ==========================================================================
    # 6. Validate system_migration against raw text - STRICT (require "migration")
    # ==========================================================================
    sys_migration_data = extracted.get('system_migration_in_progress')
    sys_migration_value, sys_migration_phrase = extract_value_and_phrase(sys_migration_data)

    if sys_migration_value is True:
        # Must have actual mention of "migration" or "migrating" - NOT just "transition"
        # A fax number transition is NOT a system migration
        migration_keywords = ['migration', 'migrating']
        found = any(kw in raw_text.lower() for kw in migration_keywords)
        if not found:
            validation_notes.append("system_migration_in_progress CORRECTED to false (no 'migration'/'migrating' keyword - 'transition' alone is not sufficient)")
            extracted['system_migration_in_progress'] = False

    # ==========================================================================
    # 6b. Validate appeal_deadline_days against raw text - CORRECTIVE
    # ==========================================================================
    appeal_deadline_data = extracted.get('appeal_deadline_days')
    appeal_deadline_value, appeal_deadline_phrase = extract_value_and_phrase(appeal_deadline_data)

    if appeal_deadline_value is not None:
        deadline_str = str(appeal_deadline_value)
        # Check if the number appears in the raw text near "appeal" context
        raw_lower = raw_text.lower()
        if deadline_str not in raw_text:
            validation_notes.append(
                f"appeal_deadline_days '{deadline_str}' CORRECTED to null "
                f"(value not found in source text - possible cross-payer contamination)"
            )
            extracted['appeal_deadline_days'] = None
        elif 'appeal' not in raw_lower:
            validation_notes.append(
                f"appeal_deadline_days '{deadline_str}' CORRECTED to null "
                f"(no appeal context in source text)"
            )
            extracted['appeal_deadline_days'] = None

    # ==========================================================================
    # 7. Convert biosimilar booleans to enum if old format
    # ==========================================================================
    if 'drugs' in extracted:
        for drug_name, drug_data in extracted['drugs'].items():
            if isinstance(drug_data, dict):
                # Handle old format with two booleans
                biosimilar_req = drug_data.get('biosimilar_required')
                biosimilar_pref = drug_data.get('biosimilar_preferred')

                if biosimilar_req is not None or biosimilar_pref is not None:
                    if biosimilar_req is True:
                        drug_data['biosimilar_requirement'] = 'required'
                    elif biosimilar_pref is True:
                        drug_data['biosimilar_requirement'] = 'preferred'
                    elif biosimilar_req is False and biosimilar_pref is False:
                        drug_data['biosimilar_requirement'] = 'none'
                    else:
                        drug_data['biosimilar_requirement'] = 'not_stated'

                    # Remove old fields
                    drug_data.pop('biosimilar_required', None)
                    drug_data.pop('biosimilar_preferred', None)

    # ==========================================================================
    # 8. CROSS-PAYER CONTAMINATION DETECTION - Remove drugs not in source
    # ==========================================================================
    if 'drugs' in extracted:
        raw_text_lower = raw_text.lower()
        drugs_to_remove = []

        for drug_name in extracted['drugs'].keys():
            # Check if drug name appears in raw text
            drug_lower = drug_name.lower()
            if drug_lower not in raw_text_lower:
                # Also check common variations
                variations = [
                    drug_lower,
                    drug_lower.replace(' ', ''),
                    drug_lower + ' ',
                    ' ' + drug_lower,
                ]
                found = any(var in raw_text_lower for var in variations)
                if not found:
                    validation_notes.append(
                        f"drugs.{drug_name} REMOVED (cross-payer contamination: "
                        f"drug name not found in {payer} source text)"
                    )
                    drugs_to_remove.append(drug_name)

        for drug_name in drugs_to_remove:
            del extracted['drugs'][drug_name]

    # ==========================================================================
    # 9. Extract missing drug fields from raw text (auth_period, step_therapy)
    # ==========================================================================
    if 'drugs' in extracted:
        for drug_name, drug_data in extracted['drugs'].items():
            if not isinstance(drug_data, dict):
                continue

            # Find drug section in raw text
            drug_section = _extract_drug_section_for_validation(drug_name, raw_text)

            # Check for auth_period_months if missing
            if drug_data.get('auth_period_months') is None:
                auth_period = _extract_auth_period_from_text(drug_section)
                if auth_period:
                    drug_data['auth_period_months'] = auth_period
                    validation_notes.append(f"drugs.{drug_name}.auth_period_months RECOVERED: {auth_period}")

            # Check for step_therapy_required if missing or False
            if not drug_data.get('step_therapy_required'):
                step_therapy = _detect_step_therapy(drug_section)
                if step_therapy:
                    drug_data['step_therapy_required'] = True
                    validation_notes.append(f"drugs.{drug_name}.step_therapy_required RECOVERED: True")

            # Check for biosimilar requirement if not_stated
            if drug_data.get('biosimilar_requirement') == 'not_stated':
                biosimilar = _detect_biosimilar_requirement(drug_section)
                if biosimilar:
                    drug_data['biosimilar_requirement'] = biosimilar
                    validation_notes.append(f"drugs.{drug_name}.biosimilar_requirement RECOVERED: {biosimilar}")

    # ==========================================================================
    # 10. Validate biosimilar "required" vs "preferred" against raw text
    # ==========================================================================
    if 'drugs' in extracted:
        for drug_name, drug_data in extracted['drugs'].items():
            if not isinstance(drug_data, dict):
                continue

            bio_req = get_val(drug_data.get('biosimilar_requirement'))
            if bio_req == 'required':
                # Verify it's actually required, not just preferred
                drug_section = _extract_drug_section_for_validation(drug_name, raw_text)
                drug_section_lower = drug_section.lower()

                # Check if "preferred" appears without "required"
                has_preferred = 'preferred' in drug_section_lower
                has_required = any(kw in drug_section_lower for kw in ['required', 'must', 'trial required', 'attestation required'])

                if has_preferred and not has_required:
                    validation_notes.append(f"drugs.{drug_name}.biosimilar_requirement CORRECTED: 'required' → 'preferred' (text says 'preferred' not 'required')")
                    drug_data['biosimilar_requirement'] = 'preferred'

    # ==========================================================================
    # 11. Validate auth_period_months uses initial period (not renewal)
    # ==========================================================================
    if 'drugs' in extracted:
        for drug_name, drug_data in extracted['drugs'].items():
            if not isinstance(drug_data, dict):
                continue

            auth = get_val(drug_data.get('auth_period_months'))
            auth_initial = get_val(drug_data.get('auth_period_initial_months'))
            auth_renewal = get_val(drug_data.get('auth_period_renewal_months'))

            # If we have both initial and renewal, and auth matches renewal, correct it
            if auth_initial and auth_renewal and auth == auth_renewal and auth != auth_initial:
                validation_notes.append(f"drugs.{drug_name}.auth_period_months CORRECTED: {auth} → {auth_initial} (use initial period, not renewal)")
                drug_data['auth_period_months'] = auth_initial

    # ==========================================================================
    # 6. Flatten value/source_phrase structures for downstream compatibility
    # ==========================================================================
    fields_to_flatten = [
        'fax_number', 'fax_number_old', 'phone', 'phone_hours', 'portal_url',
        'turnaround_standard_days', 'turnaround_urgent_hours', 'chart_note_window_days',
        'pa_form', 'pa_form_old', 'appeal_fax', 'appeal_phone', 'appeal_deadline_days',
        'system_migration_in_progress', 'phone_experience_note'
    ]

    for field in fields_to_flatten:
        if field in extracted and isinstance(extracted[field], dict) and 'value' in extracted[field]:
            extracted[field] = extracted[field]['value']

    # Store validation notes
    if validation_notes:
        extracted['_validation_notes'] = validation_notes

    return extracted


# =============================================================================
# EXTRACTION AGENT CLASS
# =============================================================================

class ExtractionAgent:
    """Agent that extracts structured PA route data from raw text."""

    def __init__(self, cache_dir: Path = Path(".agent_cache")):
        self.client = Anthropic()
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.total_cost = 0.0

    def _cache_key(self, text: str, source_type: str, payer: str) -> str:
        """Generate cache key from input."""
        # Add version to cache key to invalidate old caches
        # v6: Fixed source date to prioritize "Last updated" over "Scraped date"
        content = f"v6:{payer}:{source_type}:{text}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _get_cached(self, key: str) -> dict | None:
        """Get cached extraction result."""
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        return None

    def _save_cache(self, key: str, data: dict):
        """Save extraction result to cache."""
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps(data, indent=2))

    def _extract_source_date(self, raw_text: str, default_date: str) -> str:
        """Extract source date from raw text metadata and content."""
        # Month name to number mapping
        months = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12',
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09',
            'oct': '10', 'nov': '11', 'dec': '12'
        }

        # Priority 1: "Last updated" patterns (content date, most relevant for freshness)
        # These indicate when the CONTENT was last updated, not when we scraped it
        last_updated_patterns = [
            r'[Ll]ast\s+updated(?:\s+on\s+page)?[:\s]+(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "Last updated: January 15, 2025"
            r'[Ll]ast\s+updated(?:\s+on\s+page)?[:\s]+(\w+)\s+(\d{4})',  # "Last updated on page: October 2024"
            r'[Ll]ast\s+reviewed[:\s]+(\w+)\s+(\d{4})',  # "Last reviewed: April 2025"
        ]

        for pattern in last_updated_patterns:
            match = re.search(pattern, raw_text, re.MULTILINE)
            if match:
                groups = match.groups()
                month_str = groups[0].lower()
                if month_str in months:
                    month = months[month_str]
                    if len(groups) == 3:
                        day_num = int(groups[1])
                        if 1 <= day_num <= 31:
                            return f"{groups[2]}-{month}-{str(day_num).zfill(2)}"
                    else:
                        return f"{groups[1]}-{month}-01"

        # Priority 2: Other date patterns (call dates, document dates, etc.)
        patterns = [
            r'[Cc]all\s+date[:\s]+(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "Call date: March 19, 2026"
            r'^Date[:\s]+(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "Date: March 8, 2026" at line start
            r'[Dd]ate[:\s]+(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "Date: March 8, 2026"
        ]

        for pattern in patterns:
            match = re.search(pattern, raw_text, re.MULTILINE)
            if match:
                groups = match.groups()
                month_str = groups[0].lower()
                if month_str in months:
                    month = months[month_str]
                    if len(groups) == 3:
                        # Has day - validate it's a valid day (1-31)
                        day_num = int(groups[1])
                        if 1 <= day_num <= 31:
                            day = groups[1].zfill(2)
                            year = groups[2]
                            return f"{year}-{month}-{day}"
                    else:
                        # No day, use 01
                        day = '01'
                        year = groups[1]
                        return f"{year}-{month}-{day}"

        # Priority 2: ISO format (2025-01-15) - but not in reference numbers
        # Look for standalone ISO dates, not embedded in IDs
        match = re.search(r'(?<![A-Z0-9-])(\d{4})-(\d{2})-(\d{2})(?![0-9])', raw_text)
        if match:
            year, month, day = match.groups()
            if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                return f"{year}-{month}-{day}"

        return default_date

    def extract_from_source(
        self,
        raw_text: str,
        source_type: str,
        source_date: str,
        payer: str,
        source_id: str,
    ) -> dict:
        """
        Extract structured data from a single source document.
        """
        # Check cache first
        cache_key = self._cache_key(raw_text, source_type, payer)
        cached = self._get_cached(cache_key)
        if cached:
            print(f"  [CACHE HIT] {source_id}")
            return cached

        print(f"  [EXTRACTING] {source_id}...")

        prompt = EXTRACTION_PROMPT.format(
            source_type=source_type,
            source_date=source_date,
            payer=payer,
            raw_text=raw_text[:15000],
            schema=PA_ROUTE_SCHEMA,
        )

        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        # Track cost
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000
        self.total_cost += cost

        # Parse response
        try:
            extracted = json.loads(response.content[0].text)
        except json.JSONDecodeError as e:
            text = response.content[0].text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    extracted = json.loads(text[start:end])
                except json.JSONDecodeError as e2:
                    # Try to fix common JSON issues
                    json_text = text[start:end]
                    # Remove trailing commas before } or ]
                    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
                    try:
                        extracted = json.loads(json_text)
                    except json.JSONDecodeError:
                        print(f"  [ERROR] Failed to parse JSON from {source_id}: {e2}")
                        extracted = {}
            else:
                print(f"  [ERROR] No JSON found in response from {source_id}")
                extracted = {}

        # Post-process with validation against raw text
        extracted = post_process_extraction(extracted, raw_text, payer=payer)

        # Log validation notes
        if '_validation_notes' in extracted:
            for note in extracted['_validation_notes']:
                print(f"    [VALIDATION] {note}")

        # Add metadata
        extracted["source_id"] = source_id
        extracted["source_type"] = source_type
        extracted["source_date"] = source_date
        extracted["payer"] = payer

        # Cache result
        self._save_cache(cache_key, extracted)

        return extracted

    def extract_payer(self, payer_dir: Path, payer_name: str) -> list[dict]:
        """Extract all sources for a payer."""
        sources = []

        source_files = {
            "provider_manual.txt": ("provider_manual", "2024-01-01"),
            "phone_transcript.txt": ("phone_transcript", "2026-03-20"),
            "web_page.txt": ("web_page", "2025-06-01"),
            "denial_letter.txt": ("denial_letter", "2026-03-15"),
        }

        payer_key = payer_name.lower().replace(" ", "_")

        for i, (filename, (source_type, default_date)) in enumerate(source_files.items(), 1):
            filepath = payer_dir / filename
            if not filepath.exists():
                continue

            raw_text = filepath.read_text()

            # Try to extract date from metadata header or content
            source_date = self._extract_source_date(raw_text, default_date)

            source_id = f"{payer_key[:3].upper()}-SRC-{i:03d}"

            extracted = self.extract_from_source(
                raw_text=raw_text,
                source_type=source_type,
                source_date=source_date,
                payer=payer_name,
                source_id=source_id,
            )

            sources.append(extracted)

        return sources


def run_extraction(payers_dir: Path = Path("payer_sources")) -> dict:
    """Run extraction agent on all payers."""
    agent = ExtractionAgent()

    result = {
        "extraction_date": datetime.now().isoformat(),
        "extraction_method": "agentic_v2",
        "payers": {}
    }

    payer_dirs = [d for d in payers_dir.iterdir() if d.is_dir()]

    for payer_dir in sorted(payer_dirs):
        payer_name = payer_dir.name.replace("_", " ").title()
        if payer_name == "Blue Cross Blue Shield":
            payer_name = "Anthem Blue Cross Blue Shield"

        print(f"\n[PAYER] {payer_name}")

        sources = agent.extract_payer(payer_dir, payer_name)
        result["payers"][payer_name] = {
            "sources": sources
        }

    print(f"\n[DONE] Total API cost: ${agent.total_cost:.4f}")

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("AGENTIC EXTRACTION AGENT v3")
    print("With payer isolation + corrective validation + field disambiguation")
    print("=" * 60)

    result = run_extraction()

    output_file = Path("agentic_prototype/extracted_data.json")
    output_file.write_text(json.dumps(result, indent=2))
    print(f"\nOutput saved to: {output_file}")

    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    for payer, data in result["payers"].items():
        n_sources = len(data["sources"])
        n_drugs = sum(len(s.get("drugs", {})) for s in data["sources"])
        print(f"  {payer}: {n_sources} sources, {n_drugs} drug mentions")
