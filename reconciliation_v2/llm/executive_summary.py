"""LLM-based executive summary generation."""

import json
from typing import Any

from reconciliation_v2.llm.client import get_client, is_llm_available


def generate_executive_summary(
    payer_name: str,
    best_route: dict[str, Any],
    focus_drug: str | None,
    conflicts_detected: int,
    payer_warnings: list[str],
) -> str | None:
    """
    Generate a comprehensive executive summary of the reconciled route.

    Uses Claude Haiku for cost efficiency. Result is cached by input hash.

    Args:
        payer_name: Name of the payer
        best_route: The best_route object from reconciliation
        focus_drug: The selected focus drug name
        conflicts_detected: Number of conflicts found
        payer_warnings: List of payer-level warnings

    Returns:
        Executive summary string, or None if LLM unavailable
    """
    if not is_llm_available():
        return None

    # Build comprehensive input - give LLM ALL the data to reason through
    route_data = _build_comprehensive_route_data(best_route, focus_drug, payer_warnings, conflicts_detected)

    prompt = f"""You are helping medical office staff submit prior authorizations. Analyze this reconciled route data for {payer_name} and write a comprehensive executive summary.

=== ROUTE DATA ===
{route_data}
=== END ROUTE DATA ===

Write a 5-7 sentence executive summary that a medical office staff member can use as a quick reference. Your summary MUST cover:

1. **Submission method**: Preferred method, URL/portal, AND the fallback option
2. **CRITICAL: Deprecated/Do-Not-Use numbers**: If there are any deprecated fax numbers or "do not use" items, EXPLICITLY WARN about them with the specific number
3. **Turnaround times**: All available turnaround times (standard, urgent, portal vs fax differences)
4. **Required documents**: Key documents needed, especially form names with version numbers (e.g., AET-PA-2025)
5. **Drug-specific requirements**: If there's a focus drug, mention step therapy, biosimilar requirements, specialist requirements, auth periods
6. **Payer warnings**: System migrations, delays, any operational issues - these are CRITICAL
7. **Conflicts**: If there were conflicts in the data, mention this affects confidence

Be specific with numbers, form versions, and phone/fax numbers. This is operational guidance - vague summaries are useless. Write in prose, not bullet points.
"""

    try:
        client = get_client()
        result = client.complete(prompt, max_tokens=512)
        return result.strip()
    except Exception:
        return None


def _build_comprehensive_route_data(
    best_route: dict[str, Any],
    focus_drug: str | None,
    payer_warnings: list[str],
    conflicts_detected: int,
) -> str:
    """Build comprehensive route data for the LLM - include EVERYTHING."""
    sections = []

    # Submission method - full details
    submission = best_route.get("submission", {})
    if submission:
        sections.append("SUBMISSION METHOD:")
        sections.append(f"  Preferred: {submission.get('preferred_method', 'unknown')}")
        if submission.get("preferred_url"):
            sections.append(f"  URL: {submission['preferred_url']}")
        if submission.get("fallback_method"):
            sections.append(f"  Fallback: {submission['fallback_method']}")
        if submission.get("fallback_fax"):
            sections.append(f"  Fallback Fax: {submission['fallback_fax']}")
        # CRITICAL: Deprecated numbers
        if submission.get("do_not_use"):
            sections.append("  *** DO NOT USE (DEPRECATED): ***")
            for item in submission["do_not_use"]:
                sections.append(f"    - {item}")

    # Turnaround times - all of them
    turnaround = best_route.get("turnaround", {})
    if turnaround:
        sections.append("\nTURNAROUND TIMES:")
        for method, time in turnaround.items():
            if isinstance(time, dict):
                time_str = f"{time.get('min', '?')}-{time.get('max', '?')} days"
            else:
                time_str = str(time)
            sections.append(f"  {method}: {time_str}")

    # Required documents - ALL of them, with form versions
    docs = best_route.get("required_documents", [])
    if docs:
        sections.append("\nREQUIRED DOCUMENTS:")
        for doc in docs:
            sections.append(f"  - {doc}")

    # Contact info
    contact = best_route.get("contact", {})
    if contact:
        sections.append("\nCONTACT INFO:")
        for key, value in contact.items():
            sections.append(f"  {key}: {value}")

    # Drug requirements - ALL DRUGS
    all_drug_req = best_route.get("all_drug_requirements", {})
    if all_drug_req:
        sections.append(f"\nDRUG-SPECIFIC REQUIREMENTS ({len(all_drug_req)} drugs):")
        for drug_name, drug_req in sorted(all_drug_req.items()):
            is_focus = drug_name == focus_drug
            focus_marker = " [FOCUS DRUG]" if is_focus else ""
            sections.append(f"\n  {drug_name}{focus_marker}:")
            for key, value in drug_req.items():
                if key == "drug_name":
                    continue
                if key == "notes" and isinstance(value, list):
                    sections.append(f"    Notes:")
                    for note in value:
                        sections.append(f"      - {note}")
                else:
                    sections.append(f"    {key}: {value}")

    # Restrictions - ALL of them
    restrictions = best_route.get("restrictions", [])
    if restrictions:
        sections.append("\nRESTRICTIONS/WARNINGS:")
        for r in restrictions:
            sections.append(f"  - {r}")

    # Payer-level warnings - CRITICAL
    if payer_warnings:
        sections.append("\n*** PAYER WARNINGS (CRITICAL): ***")
        for warning in payer_warnings:
            sections.append(f"  - {warning}")

    # Conflicts
    sections.append(f"\nDATA QUALITY:")
    sections.append(f"  Conflicts detected: {conflicts_detected}")
    if conflicts_detected > 0:
        sections.append(f"  Note: {conflicts_detected} fields had conflicting values across sources. Best values were selected based on recency and source authority.")

    return "\n".join(sections)
