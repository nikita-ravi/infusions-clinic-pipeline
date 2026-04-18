"""
PA Route Reconciliation Agent (v2 - Skill-based)

This agent uses a skill (methodology) + Claude API (reasoning) to reconcile
conflicting PA route information from multiple sources.

The key insight:
- Skill: Provides consistent methodology (how to weigh sources, detect supersession)
- API: Claude's reasoning to apply methodology to specific conflicts
- Python: Orchestration and structure

Without the skill: Claude reasons ad hoc, might weigh sources differently each run.
Without the API: stuck with hardcoded weights that can't handle nuance.
Together: deterministic framework + flexible reasoning.
"""

import json
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic


# =============================================================================
# CONFIGURATION
# =============================================================================

SKILL_PATH = Path(__file__).parent.parent / "pa-reconciliation" / "SKILL.md"
PAYER_SOURCES_DIR = Path(__file__).parent.parent / "payer_sources"
EXTRACTED_DATA_PATH = Path(__file__).parent / "data" / "extracted_data.json"

# Source file mapping
SOURCE_FILES = {
    "provider_manual": "provider_manual.txt",
    "phone_transcript": "phone_transcript.txt",
    "web_page": "web_page.txt",
    "denial_letter": "denial_letter.txt",
}

# Fields to SKIP (metadata, not reconciliation targets)
SKIP_FIELDS = {
    "source_id",
    "source_type",
    "source_date",
    "payer",
    "_validation_notes",
}


# =============================================================================
# SKILL LOADER
# =============================================================================

def load_skill() -> str:
    """Load the reconciliation skill (methodology)."""
    if not SKILL_PATH.exists():
        raise FileNotFoundError(f"Skill not found at {SKILL_PATH}")

    skill_content = SKILL_PATH.read_text()

    # Extract body (skip YAML frontmatter)
    if skill_content.startswith("---"):
        parts = skill_content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()

    return skill_content


# =============================================================================
# SOURCE LOADER
# =============================================================================

def load_raw_sources(payer_key: str) -> dict[str, str]:
    """Load raw source text files for a payer."""
    payer_dir = PAYER_SOURCES_DIR / payer_key

    if not payer_dir.exists():
        raise FileNotFoundError(f"Payer directory not found: {payer_dir}")

    sources = {}
    for source_type, filename in SOURCE_FILES.items():
        filepath = payer_dir / filename
        if filepath.exists():
            sources[source_type] = filepath.read_text()

    return sources


def load_extracted_data(payer_name: str) -> dict:
    """Load previously extracted data for a payer."""
    if not EXTRACTED_DATA_PATH.exists():
        raise FileNotFoundError(f"Extracted data not found at {EXTRACTED_DATA_PATH}")

    data = json.loads(EXTRACTED_DATA_PATH.read_text())

    if payer_name not in data.get("payers", {}):
        raise ValueError(f"Payer '{payer_name}' not found in extracted data")

    return data["payers"][payer_name]


# =============================================================================
# DATA GATHERING (ALL fields, not just conflicts)
# =============================================================================

def gather_all_field_data(extracted_sources: list[dict]) -> tuple[dict, dict]:
    """
    Gather ALL field data from all sources, plus ALL drug data.
    Returns (field_data, drug_data).

    We pass EVERYTHING to Claude - the skill tells it what to reconcile.
    """
    field_values = {}
    all_drugs = {}

    for source in extracted_sources:
        source_id = source.get("source_id", "unknown")
        source_type = source.get("source_type", "unknown")
        source_date = source.get("source_date", "unknown")

        # Gather all top-level fields (except metadata and drugs)
        for field, value in source.items():
            if field in SKIP_FIELDS:
                continue
            if field == "drugs":
                continue  # Handle separately
            if value is None:
                continue

            if field not in field_values:
                field_values[field] = []

            field_values[field].append({
                "source_id": source_id,
                "source_type": source_type,
                "source_date": source_date,
                "value": value,
            })

        # Gather drug data
        if "drugs" in source and isinstance(source["drugs"], dict):
            for drug_name, drug_data in source["drugs"].items():
                if drug_name not in all_drugs:
                    all_drugs[drug_name] = []

                all_drugs[drug_name].append({
                    "source_id": source_id,
                    "source_type": source_type,
                    "source_date": source_date,
                    "fields": drug_data,
                })

    return field_values, all_drugs


def identify_conflicts(field_values: dict) -> dict:
    """Identify which fields have conflicting values across sources."""
    conflicts = {}
    agreements = {}

    for field, values in field_values.items():
        unique_values = set(str(v["value"]) for v in values)
        if len(unique_values) > 1:
            conflicts[field] = values
        else:
            agreements[field] = values

    return conflicts, agreements


# =============================================================================
# RECONCILIATION PROMPT
# =============================================================================

def build_reconciliation_prompt(
    skill: str,
    payer: str,
    raw_sources: dict[str, str],
    all_field_data: dict[str, list],
    all_drug_data: dict[str, list],
    conflicts: dict[str, list],
    agreements: dict[str, list],
) -> str:
    """Build the prompt for Claude to reconcile ALL fields, not just conflicts."""

    # Format raw sources
    sources_text = ""
    for source_type, content in raw_sources.items():
        sources_text += f"\n\n=== {source_type.upper()} ===\n{content}\n=== END {source_type.upper()} ==="

    # Format ALL extracted field data (not just conflicts)
    all_fields_text = ""
    for field, values in all_field_data.items():
        all_fields_text += f"\n\n### {field}\n"
        for v in values:
            all_fields_text += f"- {v['source_type']} ({v['source_date']}): {v['value']}\n"

    # Format ALL drug data
    drugs_text = ""
    if all_drug_data:
        drugs_text = "\n\n## Drug-Specific Data (from extracted sources)\n"
        for drug_name, drug_sources in all_drug_data.items():
            drugs_text += f"\n### {drug_name}\n"
            for ds in drug_sources:
                drugs_text += f"\n**{ds['source_type']}** ({ds['source_date']}):\n"
                for field_name, field_value in ds.get('fields', {}).items():
                    if field_value is not None:
                        drugs_text += f"- {field_name}: {field_value}\n"

    # Summary of conflicts vs agreements
    conflict_summary = f"\n\n**Fields with conflicts ({len(conflicts)}):** {', '.join(conflicts.keys()) if conflicts else 'None'}"
    agreement_summary = f"\n**Fields in agreement ({len(agreements)}):** {', '.join(agreements.keys()) if agreements else 'None'}"

    prompt = f"""You are a PA route reconciliation agent. Your job is to reconcile PA route information from multiple source documents.

## Your Methodology (FOLLOW THIS EXACTLY)

{skill}

---

## Current Task

Reconcile ALL PA route information for **{payer}**.

IMPORTANT: Use the Required Field Inventory in your methodology. You must reconcile EVERY field listed there, not just the ones with obvious conflicts. If a field is missing from all sources, note it as missing.

## Raw Source Documents

{sources_text}

## Extracted Field Data (from all sources)

The following field values were extracted from each source:
{all_fields_text}
{drugs_text}
{conflict_summary}
{agreement_summary}

## Your Task

1. **Review the Required Field Inventory** in your methodology
2. **For EACH field in the inventory:**
   - If present in sources: reconcile using the methodology (even if all sources agree - confirm the value)
   - If missing from all sources: report as missing
3. **For ALL drugs mentioned in ANY source:**
   - Reconcile every per-drug field listed in the inventory
4. **Apply supersession detection** to identify outdated values
5. **Assign confidence scores** based on evidence strength

## Output Format

Respond with a JSON object:

```json
{{
  "payer": "{payer}",
  "reconciliation_date": "{datetime.now().strftime('%Y-%m-%d')}",
  "fields": {{
    "field_name": {{
      "selected_value": "the correct value",
      "confidence": 0.95,
      "reasoning": "Why this value was selected, citing raw source evidence",
      "superseded_values": [
        {{"value": "old value", "reason": "Why superseded"}}
      ],
      "sources_considered": [
        {{"source": "source_type", "date": "date", "value": "value", "weight": "high/medium/low/superseded"}}
      ]
    }}
  }},
  "drugs": {{
    "DrugName": {{
      "step_therapy_required": {{
        "selected_value": true,
        "confidence": 0.9,
        "reasoning": "...",
        "sources_considered": [...]
      }},
      "biosimilar_requirement": {{...}},
      "auth_period_months": {{...}}
    }}
  }},
  "missing_fields": ["field1", "field2"]
}}
```

IMPORTANT:
- Reconcile ALL fields from the Required Field Inventory
- Reconcile ALL drugs from ANY source
- Your reasoning must cite specific quotes from raw source text
- Explain WHY one source is more reliable for each field
- Quote exact phrases for supersession detection
- Assign confidence based on evidence strength

Respond with valid JSON only. No markdown code fences, no explanation outside the JSON.
"""

    return prompt


# =============================================================================
# RECONCILIATION AGENT
# =============================================================================

class ReconciliationAgent:
    """Agent that reconciles PA route conflicts using skill + API."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.client = Anthropic()
        self.model = model
        self.skill = load_skill()
        self.total_cost = 0.0

    def reconcile_payer(self, payer_key: str, payer_name: str) -> dict:
        """
        Reconcile ALL fields for a single payer (not just conflicts).

        Args:
            payer_key: Directory name (e.g., "aetna")
            payer_name: Display name (e.g., "Aetna")

        Returns:
            Reconciliation result with reasoned decisions for ALL fields
        """
        print(f"\n[RECONCILING] {payer_name}")

        # Load raw sources
        print(f"  Loading raw sources from {payer_key}/...")
        raw_sources = load_raw_sources(payer_key)
        print(f"  Loaded {len(raw_sources)} source files")

        # Load extracted data
        print(f"  Loading extracted data...")
        extracted = load_extracted_data(payer_name)
        extracted_sources = extracted.get("sources", [])
        print(f"  Loaded {len(extracted_sources)} extracted sources")

        # Gather ALL field data (not just conflicts)
        print(f"  Gathering all field data...")
        all_field_data, all_drug_data = gather_all_field_data(extracted_sources)
        print(f"  Found {len(all_field_data)} fields, {len(all_drug_data)} drugs")

        # Identify conflicts vs agreements (for Claude's reference)
        conflicts, agreements = identify_conflicts(all_field_data)
        print(f"  {len(conflicts)} fields with conflicts, {len(agreements)} in agreement")

        # Build prompt with ALL data (Claude decides what to reconcile based on skill)
        prompt = build_reconciliation_prompt(
            skill=self.skill,
            payer=payer_name,
            raw_sources=raw_sources,
            all_field_data=all_field_data,
            all_drug_data=all_drug_data,
            conflicts=conflicts,
            agreements=agreements,
        )

        # Call Claude API
        print(f"  Calling Claude API for reconciliation...")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=16384,  # Large for full field inventory + all drugs
            messages=[{"role": "user", "content": prompt}]
        )

        # Track cost (Sonnet pricing)
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
        self.total_cost += cost
        print(f"  API call: {input_tokens} in, {output_tokens} out (${cost:.4f})")

        # Parse response
        text = response.content[0].text

        # Strip markdown code fences if present
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        elif text.startswith("```"):
            text = text[3:]  # Remove ```
        if text.endswith("```"):
            text = text[:-3]  # Remove trailing ```
        text = text.strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError as e:
            # Try to extract JSON from response
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    result = json.loads(text[start:end])
                except json.JSONDecodeError:
                    print(f"  [ERROR] Failed to parse JSON: {e}")
                    result = {"error": str(e), "raw_response": response.content[0].text}
            else:
                print(f"  [ERROR] Response may be truncated (max_tokens reached)")
                result = {"error": str(e), "raw_response": response.content[0].text, "truncated": True}

        return result

    def reconcile_all(self) -> dict:
        """Reconcile all payers."""
        payers = {
            "aetna": "Aetna",
            "cigna": "Cigna",
            "humana": "Humana",
            "blue_cross_blue_shield": "Anthem Blue Cross Blue Shield",
            "unitedhealthcare": "Unitedhealthcare",
        }

        results = {
            "reconciliation_date": datetime.now().isoformat(),
            "method": "skill_based_agent_v2",
            "skill_used": "pa-reconciliation",
            "payers": {}
        }

        for payer_key, payer_name in payers.items():
            payer_dir = PAYER_SOURCES_DIR / payer_key
            if payer_dir.exists():
                try:
                    result = self.reconcile_payer(payer_key, payer_name)
                    results["payers"][payer_name] = result
                except Exception as e:
                    print(f"  [ERROR] {payer_name}: {e}")
                    results["payers"][payer_name] = {"error": str(e)}

        print(f"\n[DONE] Total API cost: ${self.total_cost:.4f}")

        return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("PA ROUTE RECONCILIATION AGENT v2")
    print("Skill-based methodology + Claude API reasoning")
    print("=" * 60)

    agent = ReconciliationAgent()

    # Reconcile ALL payers
    results = agent.reconcile_all()

    # Save combined results
    output_path = Path(__file__).parent / "reconciled_all_payers.json"
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\nCombined output saved to: {output_path}")

    # Save individual payer files
    for payer_name, payer_result in results.get("payers", {}).items():
        payer_key = payer_name.lower().replace(" ", "_").replace("anthem_", "")
        individual_path = Path(__file__).parent / f"reconciled_{payer_key}.json"
        individual_path.write_text(json.dumps(payer_result, indent=2))
        print(f"Individual output saved to: {individual_path}")

    # Print summary for each payer
    for payer_name, payer_result in results.get("payers", {}).items():
        if "fields" in payer_result:
            print(f"\n{'=' * 60}")
            print(f"RECONCILIATION SUMMARY: {payer_name}")
            print("=" * 60)

            # Key fields only
            key_fields = ["fax_number", "chart_note_window_days", "turnaround_standard_days", "appeal_deadline_days"]
            for field in key_fields:
                data = payer_result.get("fields", {}).get(field, {})
                if isinstance(data, dict):
                    value = data.get("selected_value", "N/A")
                    conf = data.get("confidence", "N/A")
                    print(f"  {field}: {value} (conf: {conf})")

            # Drug summary
            drugs = payer_result.get("drugs", {})
            if drugs:
                print(f"\n  Drugs reconciled: {', '.join(drugs.keys())}")

            # Extraction errors
            errors = payer_result.get("extraction_errors", [])
            if errors:
                print(f"\n  EXTRACTION ERRORS FOUND: {len(errors)}")
                for err in errors[:3]:  # Show first 3
                    print(f"    - {err}")


if __name__ == "__main__":
    main()
