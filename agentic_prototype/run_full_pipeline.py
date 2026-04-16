"""
Full Agentic Pipeline

Runs:
1. Extraction Agent → structured JSON from raw text
2. Reconciliation → same output as reconciliation_v2

Output goes to: output_agentic/
"""

import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from agentic_prototype.extraction_agent import run_extraction, ExtractionAgent
except ImportError:
    from extraction_agent import run_extraction, ExtractionAgent
from reconciliation_v2.discovery.schema import discover_schema
from reconciliation_v2.pipeline.reconcile import reconcile_payer
from reconciliation_v2.reports.json_report import generate_json_report
from reconciliation_v2.reports.markdown_report import generate_markdown_report


def transform_agentic_to_schema_format(agentic_payer_data: dict, payer_name: str) -> dict:
    """
    Transform agentic extraction format to the format expected by discover_schema.

    The schema discovery expects the format from extracted_route_data.json:
    - source_name, retrieved_date fields
    - data nested under "data" key
    """
    payer_key = payer_name.lower().replace(" ", "_")
    if "anthem" in payer_key.lower():
        payer_key = "blue_cross_blue_shield"

    source_type_names = {
        "provider_manual": "Provider Manual (Agentic Extraction)",
        "phone_transcript": "Phone Transcript (Agentic Extraction)",
        "web_page": "Web Page (Agentic Extraction)",
        "denial_letter": "Denial Letter (Agentic Extraction)",
    }

    # Transform sources to match expected format
    transformed_sources = []
    for source in agentic_payer_data.get("sources", []):
        source_type = source.get("source_type", "unknown")

        # Build data dict (nested fields)
        data = {}
        drugs = {}

        for key, value in source.items():
            if key in ["source_id", "source_type", "source_date", "payer"]:
                continue
            if value is None:
                continue

            if key == "drugs" and isinstance(value, dict):
                # Process drug data
                for drug_name, drug_data in value.items():
                    # Normalize drug name (remove generic name in parens)
                    clean_name = drug_name.split("(")[0].strip()
                    drug_entry = {}

                    for field, field_value in drug_data.items():
                        if field_value is None:
                            continue
                        # Handle nested auth periods
                        if field == "auth_period_months" and isinstance(field_value, dict):
                            if "initial" in field_value:
                                drug_entry["auth_period_initial_months"] = field_value["initial"]
                            if "renewal" in field_value:
                                drug_entry["auth_period_renewal_months"] = field_value["renewal"]
                            drug_entry["auth_period_months"] = field_value.get("initial") or field_value.get("renewal")
                        else:
                            drug_entry[field] = field_value

                    if drug_entry:
                        drugs[clean_name] = drug_entry
            else:
                data[key] = value

        if drugs:
            data["drugs"] = drugs

        transformed = {
            "source_id": source.get("source_id"),
            "source_type": source_type,
            "source_name": source_type_names.get(source_type, source_type),
            "source_date": source.get("source_date"),
            "retrieved_date": source.get("source_date"),  # Same as source_date for agentic
            "data": data
        }

        transformed_sources.append(transformed)

    return {
        "payer": payer_name,
        "payer_key": payer_key,
        "sources": transformed_sources
    }


def run_agentic_pipeline(output_dir: Path = Path("output_agentic")):
    """Run full agentic pipeline with reconciliation."""

    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("FULL AGENTIC PIPELINE")
    print("Extraction → Reconciliation → Output")
    print("=" * 70)

    # Step 1: Run extraction
    print("\n[STEP 1] AGENTIC EXTRACTION")
    print("-" * 70)
    agentic_data = run_extraction()

    # Step 2: Run reconciliation for each payer
    print("\n[STEP 2] RECONCILIATION")
    print("-" * 70)

    results = {}

    for payer_name, payer_data in agentic_data["payers"].items():
        print(f"\n  Processing {payer_name}...")

        # Transform to schema format
        transformed = transform_agentic_to_schema_format(payer_data, payer_name)

        # Create a temporary JSON file for schema discovery
        temp_file = output_dir / f"_temp_{transformed['payer_key']}.json"

        # Write in the format expected by discover_schema
        temp_data = {transformed['payer_key']: transformed}
        temp_file.write_text(json.dumps(temp_data, indent=2))

        try:
            # Discover schema (returns dict of all payers)
            all_schemas = discover_schema(temp_file)
            schema = all_schemas.get(transformed['payer_key'])

            if not schema:
                print(f"    [ERROR] No schema found for {transformed['payer_key']}")
                continue

            # Run reconciliation
            result = reconcile_payer(schema)
            results[transformed['payer_key']] = result

            # Generate reports
            json_path = output_dir / f"{transformed['payer_key']}_reconciled.json"
            md_path = output_dir / f"{transformed['payer_key']}_report.md"

            generate_json_report(result, json_path)
            generate_markdown_report(result, md_path)

            print(f"    ✓ {json_path.name}")
            print(f"    ✓ {md_path.name}")

        finally:
            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()

    # Summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir.absolute()}")
    print("\nResults:")
    for payer_key, result in results.items():
        n_drugs = len(result.all_drugs)
        n_conflicts = result.conflicts_detected
        focus = result.focus_drug or "N/A"
        print(f"  {payer_key}: {n_drugs} drugs, {n_conflicts} conflicts, focus: {focus}")

    return results


if __name__ == "__main__":
    run_agentic_pipeline()
