"""Markdown report generation."""

from pathlib import Path
from typing import Any

from reconciliation_v2.pipeline.reconcile import PayerReconciliation


def generate_markdown_report(reconciliation: PayerReconciliation, output_path: Path) -> None:
    """Generate human-readable Markdown report."""
    lines = []

    # Header
    lines.append(f"# Prior Authorization Route: {reconciliation.payer}")
    lines.append("")

    # TL;DR - Executive Summary (LLM-generated)
    if reconciliation.executive_summary:
        lines.append("## TL;DR")
        lines.append("")
        lines.append(f"_{reconciliation.executive_summary}_")
        lines.append("")

    # Payer warnings (top-level banner)
    if reconciliation.payer_warnings:
        lines.append("## ⚠️ Payer Warnings")
        lines.append("")
        for warning in reconciliation.payer_warnings:
            lines.append(f"> **{warning}**")
            lines.append("")
        lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Focus Drug:** {reconciliation.focus_drug}")
    lines.append(f"  - _{reconciliation.focus_drug_selection_reason}_")
    lines.append(f"- **Fields Discovered:** {reconciliation.total_fields_discovered}")
    lines.append(f"- **Fields Output:** {reconciliation.total_fields_output}")
    lines.append(f"- **Conflicts Detected:** {reconciliation.conflicts_detected}")
    lines.append("")

    # =========================================================================
    # BEST ROUTE - PRIMARY OUTPUT FOR OPS/FRONTEND
    # =========================================================================
    lines.append("## Best Route (Actionable)")
    lines.append("")
    lines.append("_This is the primary output for form submission._")
    lines.append("")

    best = reconciliation.best_route

    # Submission method
    if best.submission:
        lines.append("### Submission Method")
        lines.append("")
        if best.submission.get("preferred_method"):
            lines.append(f"**Preferred:** {best.submission['preferred_method'].upper()}")
            if best.submission.get("preferred_url"):
                lines.append(f"- URL: `{best.submission['preferred_url']}`")
            if best.submission.get("portal_notes"):
                for note in best.submission["portal_notes"]:
                    lines.append(f"  - _{note}_")
        if best.submission.get("fallback_method"):
            lines.append(f"**Fallback:** {best.submission['fallback_method'].upper()}")
            if best.submission.get("fallback_fax"):
                lines.append(f"- Fax: `{best.submission['fallback_fax']}`")
            if best.submission.get("fax_notes"):
                for note in best.submission["fax_notes"]:
                    lines.append(f"  - _{note}_")
        if best.submission.get("do_not_use"):
            lines.append("**Do NOT Use:**")
            for item in best.submission["do_not_use"]:
                lines.append(f"- ~~{item}~~")
        lines.append("")

    # Required documents
    if best.required_documents:
        lines.append("### Required Documents")
        lines.append("")
        for doc in best.required_documents:
            lines.append(f"- {doc}")
        lines.append("")

    # Turnaround
    if best.turnaround:
        lines.append("### Turnaround Times")
        lines.append("")
        for method, time in best.turnaround.items():
            method_label = method.replace("_actual", " (actual)").replace("_", " ").title()
            lines.append(f"- **{method_label}:** {time}")
        lines.append("")

    # Contact info
    if best.contact:
        lines.append("### Contact Information")
        lines.append("")
        if best.contact.get("status_phone"):
            lines.append(f"- **Status/Questions:** `{best.contact['status_phone']}`")
        if best.contact.get("general_phone"):
            lines.append(f"- **General Phone:** `{best.contact['general_phone']}`")
        if best.contact.get("urgent_phone"):
            lines.append(f"- **Urgent Line:** `{best.contact['urgent_phone']}`")
        if best.contact.get("appeal_fax"):
            lines.append(f"- **Appeal Fax:** `{best.contact['appeal_fax']}`")
        if best.contact.get("appeal_phone"):
            lines.append(f"- **Appeal Phone:** `{best.contact['appeal_phone']}`")
        if best.contact.get("appeal_mail"):
            lines.append(f"- **Appeal Mail:** `{best.contact['appeal_mail']}`")
        if best.contact.get("appeal_deadline_days"):
            lines.append(f"- **Appeal Deadline:** {best.contact['appeal_deadline_days']} days")
        lines.append("")

    # Drug requirements - ALL DRUGS
    if best.all_drug_requirements:
        lines.append("### Drug-Specific Requirements")
        lines.append("")
        # Show focus drug first if available, then others
        focus = reconciliation.focus_drug
        drug_order = sorted(best.all_drug_requirements.keys(),
                           key=lambda d: (d != focus, d))  # Focus drug first

        for drug_name in drug_order:
            drug_req = best.all_drug_requirements[drug_name]
            is_focus = drug_name == focus
            focus_marker = " ⭐" if is_focus else ""
            lines.append(f"#### {drug_name}{focus_marker}")
            lines.append("")
            for key, value in drug_req.items():
                if key == "drug_name":
                    continue
                if key == "notes" and isinstance(value, list):
                    for note in value:
                        lines.append(f"> {note}")
                else:
                    lines.append(f"- **{_format_field_name(key)}:** {_format_value(value)}")
            lines.append("")

    # Restrictions
    if best.restrictions:
        lines.append("### Restrictions & Warnings")
        lines.append("")
        for restriction in best.restrictions:
            lines.append(f"- ⚠️ {restriction}")
        lines.append("")

    # Data Coverage (transparency)
    if best.data_coverage:
        lines.append("### Data Coverage")
        lines.append("")
        lines.append(f"_{best.data_coverage.extraction_note}_")
        lines.append("")
        if best.data_coverage.potentially_missing:
            lines.append("**Verify with payer (not in extracted data):**")
            for item in best.data_coverage.potentially_missing[:5]:
                lines.append(f"- {item}")
            lines.append("")

    lines.append("---")
    lines.append("")

    # =========================================================================
    # DETAILED FIELDS (for audit)
    # =========================================================================

    # All Drug Details (audit section)
    if reconciliation.all_drugs:
        lines.append("## All Drug Details (Audit)")
        lines.append("")
        for drug_name, drug_info in sorted(reconciliation.all_drugs.items()):
            is_focus = drug_name == reconciliation.focus_drug
            focus_marker = " ⭐ (focus)" if is_focus else ""
            lines.append(f"### {drug_name}{focus_marker}")
            lines.append("")
            lines.append(f"_Sources: {', '.join(drug_info.sources)}_")
            lines.append("")
            for field_name, value in drug_info.fields.items():
                lines.append(f"- **{_format_field_name(field_name)}:** {_format_value(value)}")
            if drug_info.notes:
                lines.append("")
                lines.append("**Notes:**")
                for note in drug_info.notes:
                    lines.append(f"> {note}")
            lines.append("")

    # Reconciled Route (high-confidence fields)
    lines.append("## Reconciled Route")
    lines.append("")

    high_conf_fields = {
        name: f for name, f in reconciliation.fields.items()
        if f.confidence >= 0.5 and not f.has_conflicts
    }

    if high_conf_fields:
        for field_name, field_rec in sorted(high_conf_fields.items()):
            lines.append(f"### {_format_field_name(field_name)}")
            lines.append("")
            lines.append(f"**Value:** `{_format_value(field_rec.value)}`")
            lines.append(f"**Confidence:** {field_rec.confidence:.2f} | **Source:** {field_rec.source_id} ({field_rec.source_type})")

            if field_rec.notes:
                lines.append("")
                lines.append("**Notes:**")
                for note in field_rec.notes:
                    lines.append(f"> {note}")

            if field_rec.operational_reality:
                lines.append("")
                lines.append("**⚠️ Operational Reality:**")
                op = field_rec.operational_reality
                if op.get("min") and op.get("max"):
                    lines.append(f"> Actual: {op['min']}-{op['max']} days")
                if op.get("cause"):
                    lines.append(f"> Cause: {op['cause']}")

            lines.append("")
    else:
        lines.append("_No high-confidence fields without conflicts._")
        lines.append("")

    # Conflicts & Warnings
    conflict_fields = {
        name: f for name, f in reconciliation.fields.items()
        if f.has_conflicts or f.confidence < 0.5
    }

    if conflict_fields:
        lines.append("## Conflicts & Warnings")
        lines.append("")

        for field_name, field_rec in sorted(conflict_fields.items()):
            lines.append(f"### {_format_field_name(field_name)}")
            lines.append("")

            if field_rec.has_conflicts:
                lines.append("⚠️ **Conflict detected across sources**")
                lines.append("")

                # Show conflicting values
                if field_rec.all_values:
                    lines.append("**Conflicting values:**")
                    for source_id, value in field_rec.all_values.items():
                        marker = "✓" if source_id == field_rec.source_id else "✗"
                        superseded = " (superseded)" if source_id in field_rec.superseded_values else ""
                        lines.append(f"- {marker} `{source_id}`: `{_format_value(value)}`{superseded}")
                    lines.append("")

            if field_rec.supersession_reasons:
                lines.append("**Supersession:**")
                for reason in field_rec.supersession_reasons:
                    lines.append(f"- {reason}")
                lines.append("")

            lines.append(f"**Selected:** `{_format_value(field_rec.value)}`")
            lines.append(f"**Confidence:** {field_rec.confidence:.2f}")
            lines.append("")

    # Decision Audit Trail
    lines.append("## Decision Audit Trail")
    lines.append("")
    lines.append("Detailed decision paths for key fields.")
    lines.append("")

    # Show audit trail for fields with conflicts or special handling
    audit_fields = {
        name: f for name, f in reconciliation.fields.items()
        if f.has_conflicts or f.supersession_reasons or f.operational_reality
    }

    for field_name, field_rec in sorted(audit_fields.items()):
        lines.append(f"### {_format_field_name(field_name)}")
        lines.append("")
        lines.append("```")
        for i, step in enumerate(field_rec.decision_path, 1):
            lines.append(f"{i}. {step}")
        lines.append("```")
        lines.append("")

    output_path.write_text("\n".join(lines))


def _format_field_name(field_name: str) -> str:
    """Format field name for display."""
    return field_name.replace("_", " ").title()


def _format_value(value: Any) -> str:
    """Format value for display."""
    if value is None:
        return "None"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        # Format dict nicely
        parts = []
        for k, v in value.items():
            if isinstance(v, dict):
                v_str = ", ".join(f"{k2}: {v2}" for k2, v2 in v.items())
                parts.append(f"{k}: {{{v_str}}}")
            else:
                parts.append(f"{k}: {v}")
        return " | ".join(parts)
    return str(value)
