"""
Agentic Pipeline Demo

Shows the full flow:
1. Extraction Agent: Raw text → Structured JSON
2. Reconciliation: Conflicting sources → Single trusted route
3. Output: Confidence-scored, auditable result

This demonstrates how agentic extraction feeds into deterministic reconciliation.
"""

import json
from pathlib import Path

from extraction_agent import run_extraction, ExtractionAgent


def transform_to_reconciliation_format(agentic_data: dict) -> dict:
    """
    Transform agentic extraction output to the format expected by reconciliation_v2.

    The reconciliation pipeline expects extracted_route_data.json format.
    """
    result = {}

    for payer_name, payer_data in agentic_data["payers"].items():
        payer_key = payer_name.lower().replace(" ", "_")
        if "anthem" in payer_key:
            payer_key = "blue_cross_blue_shield"

        result[payer_key] = {
            "payer": payer_name,
            "sources": payer_data["sources"]
        }

    return result


def compare_with_provided(agentic_data: dict, provided_path: Path) -> dict:
    """
    Compare agentic extraction with provided extracted_route_data.json.

    Returns comparison statistics.
    """
    provided = json.loads(provided_path.read_text())

    comparison = {}

    for payer_key, agentic_payer in agentic_data.items():
        if payer_key not in provided:
            continue

        provided_payer = provided[payer_key]

        # Count fields extracted
        agentic_fields = set()
        provided_fields = set()

        for source in agentic_payer.get("sources", []):
            for key in source.keys():
                if key not in ["source_id", "source_type", "source_date", "payer"]:
                    agentic_fields.add(key)

        for source in provided_payer.get("sources", []):
            for key in source.keys():
                if key not in ["source_id", "source_type", "source_date", "payer"]:
                    provided_fields.add(key)

        comparison[payer_key] = {
            "agentic_fields": len(agentic_fields),
            "provided_fields": len(provided_fields),
            "overlap": len(agentic_fields & provided_fields),
            "agentic_only": list(agentic_fields - provided_fields),
            "provided_only": list(provided_fields - agentic_fields),
        }

    return comparison


def run_full_pipeline():
    """Run the full agentic pipeline."""
    print("=" * 70)
    print("AGENTIC PA ROUTE PIPELINE")
    print("=" * 70)

    # Step 1: Extract from raw sources
    print("\n[STEP 1] AGENTIC EXTRACTION")
    print("-" * 70)
    agentic_data = run_extraction()

    # Step 2: Transform to reconciliation format
    print("\n[STEP 2] TRANSFORM TO RECONCILIATION FORMAT")
    print("-" * 70)
    reconciliation_input = transform_to_reconciliation_format(agentic_data)

    # Save intermediate output
    output_path = Path("agentic_prototype/reconciliation_input.json")
    output_path.write_text(json.dumps(reconciliation_input, indent=2))
    print(f"Saved reconciliation input to: {output_path}")

    # Step 3: Compare with provided data
    print("\n[STEP 3] COMPARE WITH PROVIDED EXTRACTION")
    print("-" * 70)
    provided_path = Path("payer_sources/extracted_route_data.json")
    if provided_path.exists():
        comparison = compare_with_provided(reconciliation_input, provided_path)
        for payer, stats in comparison.items():
            print(f"\n  {payer}:")
            print(f"    Agentic extracted: {stats['agentic_fields']} fields")
            print(f"    Provided had: {stats['provided_fields']} fields")
            print(f"    Overlap: {stats['overlap']} fields")
            if stats['agentic_only']:
                print(f"    Agentic found extra: {stats['agentic_only'][:5]}...")
            if stats['provided_only']:
                print(f"    Missing from agentic: {stats['provided_only'][:5]}...")

    # Step 4: Show how this would feed into reconciliation
    print("\n[STEP 4] RECONCILIATION (using reconciliation_v2)")
    print("-" * 70)
    print("""
To run reconciliation on agentic-extracted data:

    # Copy agentic extraction to expected location
    cp agentic_prototype/reconciliation_input.json payer_sources/extracted_route_data.json

    # Run reconciliation pipeline
    python -m reconciliation_v2.main --all

The reconciliation layer is DETERMINISTIC - same input always produces
same output. The agentic part handles the messy extraction; reconciliation
handles the trustworthy output.
    """)

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_full_pipeline()
