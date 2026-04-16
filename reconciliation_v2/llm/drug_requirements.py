"""LLM-based drug requirement extraction from prose notes - STRICTLY GROUNDED."""

import re
from typing import Any

from reconciliation_v2.llm.client import get_client, is_llm_available


def extract_drug_requirements_with_llm(
    drug_name: str,
    all_notes: list[str],
    payer_name: str,
    existing_fields: dict[str, Any] | None = None,
    raw_drug_section: str = "",
) -> dict[str, Any]:
    """
    Extract structured drug requirements from prose notes using LLM.

    STRICTLY GROUNDED: Only extracts values explicitly stated in source text.
    Each extracted field must have a source phrase justification.

    Args:
        drug_name: Name of the drug (e.g., "Herceptin", "Remicade")
        all_notes: List of notes from all sources about this drug
        payer_name: Name of the payer (e.g., "Aetna", "BCBS")
        existing_fields: Already extracted fields from keyword matching
        raw_drug_section: Raw text section for this drug from provider manual

    Returns:
        Dictionary of structured requirements
    """
    if not is_llm_available():
        return existing_fields or {}

    if not all_notes and not raw_drug_section:
        return existing_fields or {}

    # Combine all source text
    notes_text = "\n".join(f"- {note}" for note in all_notes)
    source_text = f"""
NOTES:
{notes_text}

RAW MANUAL SECTION:
{raw_drug_section if raw_drug_section else "(not available)"}
"""

    existing_text = ""
    if existing_fields:
        existing_text = f"""
Already extracted (from deterministic parsing):
{_format_existing_fields(existing_fields)}

Only add fields that are EXPLICITLY stated in the source text but not captured above.
"""

    prompt = f"""Analyze the source text for {drug_name} from {payer_name} and extract structured requirements.

=== SOURCE TEXT (THIS IS YOUR ONLY ALLOWED SOURCE) ===
{source_text}
=== END SOURCE TEXT ===
{existing_text}
CRITICAL GROUNDING RULES:
1. ONLY extract values that are EXPLICITLY stated in the source text above.
2. For each field you extract, you MUST quote the exact phrase from the source that justifies it.
3. DO NOT infer requirements from medical knowledge or typical drug prescribing patterns.
4. DO NOT add specialist_required unless the source explicitly says "specialist", "neurologist must", "oncologist must/required", etc.
5. DISTINGUISH between "preferred", "recommended", and "required":
   - "preferred" or "recommended" → use the *_preferred field (e.g., biosimilar_preferred)
   - "required", "must", "mandatory" → use the *_required field (e.g., biosimilar_required)
   - If source says "preferred for new starts", that is NOT required.

Output a JSON object with these fields (only include if EXPLICITLY mentioned in source):
- specialist_required: boolean - ONLY if source says specialist/neurologist/oncologist must submit/required
- prior_treatment_failure_required: boolean - ONLY if source says failure documentation "required" or "must"
- step_therapy_required: boolean - if source says step therapy required
- biosimilar_required: boolean - ONLY if source says biosimilar "required" or "must"
- biosimilar_preferred: boolean - if source says biosimilar "preferred" or "recommended"
- specific_testing: list of strings - specific tests mentioned (e.g., "HER2", "CD20", "PD-L1", "JCV")
- documentation_requirements: list of strings - specific documents mentioned
- diagnosis_restrictions: list of strings - specific diagnoses that qualify

For EACH field you include, add a corresponding "_source" field with the exact quote.
Example: {{"specialist_required": true, "specialist_required_source": "Neurologist must submit"}}

If a field is not explicitly stated in the source text, DO NOT include it.
Respond with valid JSON only.
"""

    try:
        client = get_client()
        result = client.complete_json(prompt, max_tokens=1024)

        if result is None:
            return existing_fields or {}

        # VALIDATE: Check that *_required fields have proper source justification
        validated = dict(existing_fields or {})

        for key, value in result.items():
            # Skip source citation fields
            if key.endswith("_source"):
                continue

            # For *_required fields, validate the source phrase
            if key.endswith("_required") and value is True:
                source_key = f"{key}_source"
                source_phrase = result.get(source_key, "")

                # Check if source phrase justifies "required"
                if not _validates_required(source_phrase):
                    # Check if it's actually "preferred" language
                    if _is_preferred_language(source_phrase):
                        # Downgrade to preferred
                        preferred_key = key.replace("_required", "_preferred")
                        validated[preferred_key] = True
                        continue
                    else:
                        # No valid source, skip this field
                        continue

            # For non-required fields or validated required fields
            if key not in validated or validated[key] is None:
                # Don't add specialist_required unless source is valid
                if key == "specialist_required" and value is True:
                    source_phrase = result.get("specialist_required_source", "")
                    if not any(phrase in source_phrase.lower() for phrase in
                               ['specialist', 'neurologist', 'oncologist']):
                        continue

                validated[key] = value
            elif isinstance(value, list) and isinstance(validated.get(key), list):
                # Merge lists, deduplicate
                validated[key] = list(set(validated[key] + value))

        return validated

    except Exception:
        # Graceful degradation - return existing fields if LLM fails
        return existing_fields or {}


def _validates_required(source_phrase: str) -> bool:
    """Check if source phrase justifies a 'required' designation."""
    if not source_phrase:
        return False

    lower = source_phrase.lower()
    required_words = ['required', 'must', 'mandatory', 'need to', 'have to']
    return any(word in lower for word in required_words)


def _is_preferred_language(source_phrase: str) -> bool:
    """Check if source phrase indicates 'preferred' rather than 'required'."""
    if not source_phrase:
        return False

    lower = source_phrase.lower()
    preferred_words = ['preferred', 'recommended', 'encouraged', 'should']
    return any(word in lower for word in preferred_words)


def _format_existing_fields(fields: dict[str, Any]) -> str:
    """Format existing fields for display in prompt."""
    lines = []
    for key, value in fields.items():
        if value is not None:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "(none)"
