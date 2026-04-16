"""
Agentic Extraction Agent

Takes raw source files (provider manuals, phone transcripts, etc.) and extracts
structured PA route data using an LLM.

This demonstrates: "Agentic extraction → Deterministic reconciliation"
"""

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic

# Schema that the agent extracts into
PA_ROUTE_SCHEMA = """
{
  "source_id": "string (e.g., AET-SRC-001)",
  "source_type": "provider_manual | phone_transcript | web_page | denial_letter",
  "source_date": "YYYY-MM-DD",
  "payer": "string",

  // Contact fields
  "fax_number": "string (phone format)",
  "fax_number_old": "string (if deprecated number mentioned)",
  "phone": "string",
  "phone_hours": "string (e.g., M-F 8am-5pm EST)",
  "portal_url": "string",

  // Turnaround
  "turnaround_standard_days": "number or string like '10-12 (system migration)'",
  "turnaround_urgent_hours": "number",

  // Documentation requirements
  "chart_note_window_days": "number",
  "pa_form": "string (form code)",
  "pa_form_old": "string (if old form mentioned)",

  // Appeals
  "appeal_fax": "string",
  "appeal_phone": "string",
  "appeal_deadline_days": "number",

  // Drug-specific (nested)
  "drugs": {
    "DrugName": {
      "auth_period_months": "number",
      "step_therapy_required": "boolean",
      "biosimilar_required": "boolean",
      "biosimilar_preferred": "boolean",
      "specialist_required": "boolean",
      "specific_testing": ["list of tests"],
      "notes": "string with requirements"
    }
  },

  // Warnings/context
  "system_migration_in_progress": "boolean",
  "phone_experience_note": "string"
}
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

RULES:
1. Only extract information EXPLICITLY stated in the source text
2. Use null for fields not mentioned
3. For phone/fax numbers, preserve the exact format from the source
4. For drugs, extract ALL drugs mentioned with their specific requirements
5. If a field has an old/deprecated value mentioned, include both (e.g., fax_number and fax_number_old)
6. For turnaround times with ranges or explanations, include the full context (e.g., "10-12 days (system migration)")
7. Include any warnings about system issues, phone experience, etc.

Respond with valid JSON only. No markdown, no explanation.
"""


class ExtractionAgent:
    """Agent that extracts structured PA route data from raw text."""

    def __init__(self, cache_dir: Path = Path(".agent_cache")):
        self.client = Anthropic()
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.total_cost = 0.0

    def _cache_key(self, text: str, source_type: str, payer: str) -> str:
        """Generate cache key from input."""
        content = f"{payer}:{source_type}:{text}"
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

        Args:
            raw_text: The raw text content of the source
            source_type: One of: provider_manual, phone_transcript, web_page, denial_letter
            source_date: Date of the source (YYYY-MM-DD)
            payer: Payer name
            source_id: Unique identifier for this source

        Returns:
            Extracted structured data
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
            raw_text=raw_text[:15000],  # Truncate if too long
            schema=PA_ROUTE_SCHEMA,
        )

        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        # Track cost (Haiku: $0.25/1M input, $1.25/1M output)
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000
        self.total_cost += cost

        # Parse response
        try:
            extracted = json.loads(response.content[0].text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            text = response.content[0].text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                extracted = json.loads(text[start:end])
            else:
                print(f"  [ERROR] Failed to parse JSON from {source_id}")
                extracted = {}

        # Add metadata
        extracted["source_id"] = source_id
        extracted["source_type"] = source_type
        extracted["source_date"] = source_date
        extracted["payer"] = payer

        # Cache result
        self._save_cache(cache_key, extracted)

        return extracted

    def extract_payer(self, payer_dir: Path, payer_name: str) -> list[dict]:
        """
        Extract all sources for a payer.

        Args:
            payer_dir: Path to payer's source directory
            payer_name: Name of the payer

        Returns:
            List of extracted source records
        """
        sources = []

        # Map file names to source types and approximate dates
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

            # Try to extract date from metadata header
            source_date = default_date
            for line in raw_text.split('\n')[:10]:
                if 'date' in line.lower() or '202' in line:
                    # Simple date extraction
                    import re
                    match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                    if match:
                        source_date = match.group(1)
                        break

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
    """
    Run extraction agent on all payers.

    Returns:
        Dict in same format as extracted_route_data.json
    """
    agent = ExtractionAgent()

    result = {
        "extraction_date": datetime.now().isoformat(),
        "extraction_method": "agentic",
        "payers": {}
    }

    # Find all payer directories
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
    import sys

    print("=" * 60)
    print("AGENTIC EXTRACTION AGENT")
    print("Extracting PA route data from raw source files")
    print("=" * 60)

    result = run_extraction()

    # Save output
    output_file = Path("agentic_prototype/extracted_data.json")
    output_file.write_text(json.dumps(result, indent=2))
    print(f"\nOutput saved to: {output_file}")

    # Summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    for payer, data in result["payers"].items():
        n_sources = len(data["sources"])
        n_drugs = sum(
            len(s.get("drugs", {}))
            for s in data["sources"]
        )
        print(f"  {payer}: {n_sources} sources, {n_drugs} drug mentions")
