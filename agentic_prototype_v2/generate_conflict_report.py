"""
Conflict Report Generator for PA Route Reconciliation

Generates a human-readable conflict report from reconciled payer data.
Shows where sources disagreed, what was selected, and why.
"""

import json
from pathlib import Path
from datetime import datetime


def load_reconciled_data() -> dict:
    """Load all reconciled payer data."""
    base_path = Path(__file__).parent
    payers = {}

    payer_files = {
        "Aetna": "reconciled_aetna.json",
        "Cigna": "reconciled_cigna.json",
        "Humana": "reconciled_humana.json",
        "Anthem BCBS": "reconciled_blue_cross_blue_shield.json",
        "UnitedHealthcare": "reconciled_unitedhealthcare.json",
    }

    for name, filename in payer_files.items():
        filepath = base_path / filename
        if filepath.exists():
            payers[name] = json.loads(filepath.read_text())

    return payers


def has_conflict(field_data: dict) -> bool:
    """Check if a field has conflicting sources."""
    sources = field_data.get("sources_considered", [])
    if len(sources) < 2:
        return False

    # Check for different values or superseded sources
    values = set()
    for s in sources:
        val = s.get("value")
        if val is not None:
            values.add(str(val))

    return len(values) > 1 or any(s.get("weight") == "superseded" for s in sources)


def format_value(val) -> str:
    """Format a value for display."""
    if val is None:
        return "None"
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    if isinstance(val, bool):
        return "Yes" if val else "No"
    return str(val)


def generate_field_conflict_section(field_name: str, field_data: dict) -> str:
    """Generate markdown for a single field conflict."""
    lines = []

    selected = field_data.get("selected_value")
    confidence = field_data.get("confidence", "N/A")
    reasoning = field_data.get("reasoning", "No reasoning provided")
    sources = field_data.get("sources_considered", [])
    superseded = field_data.get("superseded_values", [])
    extraction_errors = field_data.get("extraction_errors", [])

    lines.append(f"### {field_name}")
    lines.append("")
    lines.append(f"**Selected Value:** `{format_value(selected)}`  ")
    lines.append(f"**Confidence:** {confidence}")
    lines.append("")

    # Source comparison table
    if sources:
        lines.append("| Source | Date | Value | Weight |")
        lines.append("|--------|------|-------|--------|")
        for s in sources:
            source = s.get("source", "unknown")
            date = s.get("date", "unknown")
            value = format_value(s.get("value"))
            weight = s.get("weight", "unknown")

            # Highlight superseded
            if weight == "superseded":
                value = f"~~{value}~~"
                weight = "**superseded**"

            lines.append(f"| {source} | {date} | {value} | {weight} |")
        lines.append("")

    # Supersession details
    if superseded:
        lines.append("**Superseded Values:**")
        for sv in superseded:
            lines.append(f"- ~~{sv.get('value')}~~ — {sv.get('reason')}")
        lines.append("")

    # Extraction errors
    if extraction_errors:
        lines.append("**Extraction Errors Detected:**")
        for err in extraction_errors:
            lines.append(f"- {err}")
        lines.append("")

    # Reasoning
    lines.append(f"**Reasoning:** {reasoning}")
    lines.append("")

    return "\n".join(lines)


def generate_payer_report(payer_name: str, data: dict) -> str:
    """Generate conflict report section for a single payer."""
    lines = []
    lines.append(f"## {payer_name}")
    lines.append("")

    # Top-level extraction errors
    top_errors = data.get("extraction_errors", [])
    if top_errors:
        lines.append("### Extraction Errors")
        lines.append("")
        for err in top_errors:
            if isinstance(err, dict):
                lines.append(f"- **{err.get('drug', 'Unknown')}/{err.get('field', 'Unknown')}** ({err.get('source', 'unknown')}): {err.get('issue', '')}")
            else:
                lines.append(f"- {err}")
        lines.append("")

    # Field-level conflicts
    fields = data.get("fields", {})
    conflicting_fields = {k: v for k, v in fields.items() if isinstance(v, dict) and has_conflict(v)}

    if conflicting_fields:
        lines.append("### Payer-Level Field Conflicts")
        lines.append("")
        for field_name, field_data in conflicting_fields.items():
            lines.append(generate_field_conflict_section(field_name, field_data))
    else:
        lines.append("*No payer-level field conflicts detected.*")
        lines.append("")

    # Drug-level conflicts
    drugs = data.get("drugs", {})
    if drugs:
        lines.append("### Drug-Level Conflicts")
        lines.append("")

        for drug_name, drug_data in drugs.items():
            drug_conflicts = {k: v for k, v in drug_data.items() if isinstance(v, dict) and has_conflict(v)}

            if drug_conflicts:
                lines.append(f"#### {drug_name}")
                lines.append("")
                for field_name, field_data in drug_conflicts.items():
                    lines.append(generate_field_conflict_section(field_name, field_data))

    return "\n".join(lines)


def generate_cross_payer_analysis(all_data: dict) -> str:
    """Generate cross-payer outlier analysis."""
    lines = []
    lines.append("## Cross-Payer Analysis")
    lines.append("")
    lines.append("This section identifies payers that are outliers for specific drug requirements.")
    lines.append("Outliers may indicate stale policy data or upcoming policy changes.")
    lines.append("")

    # Collect all drugs across payers
    all_drugs = set()
    for payer_data in all_data.values():
        all_drugs.update(payer_data.get("drugs", {}).keys())

    # Analyze biosimilar requirements
    lines.append("### Biosimilar Requirement Outliers")
    lines.append("")
    lines.append("| Drug | Payer | Value | Other Payers |")
    lines.append("|------|-------|-------|--------------|")

    for drug in sorted(all_drugs):
        values = {}
        for payer_name, payer_data in all_data.items():
            drug_data = payer_data.get("drugs", {}).get(drug, {})
            bio = drug_data.get("biosimilar_requirement", {}).get("selected_value")
            if bio:
                values[payer_name] = bio

        if values:
            # Find outliers (not_stated when others require/prefer)
            required_payers = [p for p, v in values.items() if v in ("required", "preferred")]
            not_stated_payers = [p for p, v in values.items() if v == "not_stated"]

            if required_payers and not_stated_payers:
                for outlier in not_stated_payers:
                    others = ", ".join(f"{p}: {values[p]}" for p in required_payers[:3])
                    lines.append(f"| {drug} | **{outlier}** | `not_stated` | {others} |")

    lines.append("")

    # Analyze step therapy requirements
    lines.append("### Step Therapy Variation")
    lines.append("")
    lines.append("| Drug | Payer | Step Therapy | Notes |")
    lines.append("|------|-------|--------------|-------|")

    for drug in sorted(all_drugs):
        values = {}
        for payer_name, payer_data in all_data.items():
            drug_data = payer_data.get("drugs", {}).get(drug, {})
            st = drug_data.get("step_therapy_required", {}).get("selected_value")
            if st is not None:
                values[payer_name] = st

        if values and len(set(str(v) for v in values.values())) > 1:
            for payer, val in values.items():
                note = ""
                if val == "indication_dependent":
                    note = "Varies by diagnosis"
                lines.append(f"| {drug} | {payer} | `{val}` | {note} |")

    lines.append("")

    return "\n".join(lines)


def generate_summary_stats(all_data: dict) -> str:
    """Generate summary statistics."""
    lines = []
    lines.append("## Summary Statistics")
    lines.append("")

    total_conflicts = 0
    total_extraction_errors = 0
    total_supersessions = 0

    for payer_name, data in all_data.items():
        payer_conflicts = 0
        payer_errors = len(data.get("extraction_errors", []))
        payer_supersessions = 0

        # Count field conflicts
        for field_data in data.get("fields", {}).values():
            if isinstance(field_data, dict) and has_conflict(field_data):
                payer_conflicts += 1
            if isinstance(field_data, dict) and field_data.get("superseded_values"):
                payer_supersessions += len(field_data.get("superseded_values", []))

        # Count drug conflicts
        for drug_data in data.get("drugs", {}).values():
            for field_data in drug_data.values():
                if isinstance(field_data, dict) and has_conflict(field_data):
                    payer_conflicts += 1
                if isinstance(field_data, dict) and field_data.get("superseded_values"):
                    payer_supersessions += len(field_data.get("superseded_values", []))

        total_conflicts += payer_conflicts
        total_extraction_errors += payer_errors
        total_supersessions += payer_supersessions

    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Payers Reconciled | {len(all_data)} |")
    lines.append(f"| Fields with Conflicts | {total_conflicts} |")
    lines.append(f"| Supersession Events | {total_supersessions} |")
    lines.append(f"| Extraction Errors Caught | {total_extraction_errors} |")
    lines.append("")

    return "\n".join(lines)


def generate_high_risk_conflicts(all_data: dict) -> str:
    """Generate high-risk conflict section (fields that cause denials)."""
    lines = []
    lines.append("## High-Risk Conflicts (Denial Impact)")
    lines.append("")
    lines.append("These conflicts involve fields that commonly cause PA denials if incorrect.")
    lines.append("")

    high_risk_fields = [
        "fax_number",
        "chart_note_window_days",
        "step_therapy_required",
        "biosimilar_requirement",
        "specific_testing",
        "appeal_deadline_days"
    ]

    for payer_name, data in all_data.items():
        payer_risks = []

        # Check payer-level fields
        for field in ["fax_number", "chart_note_window_days", "appeal_deadline_days"]:
            field_data = data.get("fields", {}).get(field, {})
            if isinstance(field_data, dict) and has_conflict(field_data):
                superseded = field_data.get("superseded_values", [])
                if superseded:
                    payer_risks.append(f"- **{field}**: Old value `{superseded[0].get('value')}` superseded → `{field_data.get('selected_value')}`")

        # Check drug-level fields
        for drug_name, drug_data in data.get("drugs", {}).items():
            for field in ["step_therapy_required", "biosimilar_requirement", "specific_testing"]:
                field_data = drug_data.get(field, {})
                if isinstance(field_data, dict):
                    # Check for extraction errors
                    if field_data.get("extraction_errors"):
                        payer_risks.append(f"- **{drug_name}/{field}**: Extraction error detected — {field_data.get('extraction_errors')[0]}")
                    # Check for indication-dependent
                    elif field_data.get("selected_value") == "indication_dependent":
                        payer_risks.append(f"- **{drug_name}/{field}**: Varies by indication — check before submitting")

        if payer_risks:
            lines.append(f"### {payer_name}")
            lines.append("")
            lines.extend(payer_risks)
            lines.append("")

    return "\n".join(lines)


def main():
    print("Generating conflict report...")

    all_data = load_reconciled_data()

    if not all_data:
        print("No reconciled data found. Run reconciliation_agent.py first.")
        return

    # Build report
    report_lines = []

    # Header
    report_lines.append("# PA Route Reconciliation — Conflict Report")
    report_lines.append("")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    report_lines.append("This report shows where source documents disagreed and how conflicts were resolved.")
    report_lines.append("Use this to understand why certain values were selected and what evidence supports them.")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Summary stats
    report_lines.append(generate_summary_stats(all_data))

    # High-risk conflicts
    report_lines.append(generate_high_risk_conflicts(all_data))

    # Cross-payer analysis
    report_lines.append(generate_cross_payer_analysis(all_data))

    # Per-payer details
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("# Per-Payer Conflict Details")
    report_lines.append("")

    for payer_name, data in all_data.items():
        report_lines.append(generate_payer_report(payer_name, data))
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

    # Write report
    report_content = "\n".join(report_lines)
    output_path = Path(__file__).parent / "conflict_report.md"
    output_path.write_text(report_content)

    print(f"Conflict report saved to: {output_path}")
    print(f"Payers included: {', '.join(all_data.keys())}")


if __name__ == "__main__":
    main()
