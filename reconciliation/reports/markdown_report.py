"""Markdown report generation."""

from pathlib import Path

from reconciliation.models.decision import PayerReconciliation


def generate_markdown_report(
    reconciliation: PayerReconciliation,
    output_path: Path,
) -> None:
    """
    Generate human-readable Markdown report.

    Sections:
    1. Summary
    2. Reconciled Route (high-confidence fields)
    3. Conflicts & Warnings (fields with conflicts or low confidence)
    4. Decision Audit Trail (detailed decision paths)
    """
    lines = []

    # Header
    lines.append(f"# Prior Authorization Route: {reconciliation.payer}")
    lines.append("")
    lines.append(f"**Focus Drug:** {reconciliation.summary.get('focus_drug', 'N/A')}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    summary = reconciliation.summary
    lines.append(f"- **Total Sources:** {summary.get('total_sources', 0)}")

    sources_by_type = summary.get('sources_by_type', {})
    for source_type, count in sources_by_type.items():
        lines.append(f"  - {source_type}: {count}")

    lines.append(f"- **Fields Reconciled:** {summary.get('fields_reconciled', 0)}")
    lines.append(f"- **Conflicts Detected:** {summary.get('conflicts_detected', 0)}")
    lines.append(
        f"- **High Confidence (≥0.8):** {summary.get('high_confidence_fields', 0)} fields"
    )
    lines.append(
        f"- **Low Confidence (<0.5):** {summary.get('low_confidence_fields', 0)} fields"
    )
    lines.append("")

    # Reconciled Route
    lines.append("## Reconciled Route")
    lines.append("")

    high_confidence_fields = {
        name: field
        for name, field in reconciliation.fields.items()
        if field.confidence >= 0.7 and field.value is not None
    }

    if high_confidence_fields:
        for field_name, field in sorted(high_confidence_fields.items()):
            lines.append(f"### {_format_field_name(field_name)}")
            lines.append("")
            lines.append(f"**Value:** `{_format_value(field.value)}`")
            lines.append(f"**Confidence:** {field.confidence:.2f}")

            if field.reasoning:
                lines.append("")
                lines.append(f"_{field.reasoning}_")

            lines.append("")
    else:
        lines.append("_No high-confidence fields found._")
        lines.append("")

    # Conflicts & Warnings
    lines.append("## Conflicts & Warnings")
    lines.append("")

    conflict_fields = {
        name: field
        for name, field in reconciliation.fields.items()
        if field.conflicts_detected or field.confidence < 0.7
    }

    if conflict_fields:
        for field_name, field in sorted(conflict_fields.items()):
            lines.append(f"### {_format_field_name(field_name)}")
            lines.append("")

            if field.conflicts_detected:
                lines.append("⚠️ **Conflict detected across sources**")
                lines.append("")

                # Show conflicting values
                if field.raw_values:
                    lines.append("**Conflicting values:**")
                    for source_id, value in field.raw_values.items():
                        marker = "✓" if source_id in field.contributing_sources else "✗"
                        lines.append(f"- {marker} `{source_id}`: `{_format_value(value)}`")
                    lines.append("")

            lines.append(f"**Selected:** `{_format_value(field.value)}`")
            lines.append(f"**Confidence:** {field.confidence:.2f}")

            if field.reasoning:
                lines.append("")
                lines.append(f"_{field.reasoning}_")

            lines.append("")
    else:
        lines.append("_No conflicts or warnings._")
        lines.append("")

    # Decision Audit Trail
    lines.append("## Decision Audit Trail")
    lines.append("")
    lines.append(
        "Detailed decision paths for all fields. Each path shows the rules applied in order."
    )
    lines.append("")

    for field_name, field in sorted(reconciliation.fields.items()):
        if field.value is not None:
            lines.append(f"### {_format_field_name(field_name)}")
            lines.append("")
            lines.append("```")
            for i, rule in enumerate(field.decision_path, 1):
                lines.append(f"{i}. {rule}")
            lines.append("```")
            lines.append("")

    output_path.write_text("\n".join(lines))


def _format_field_name(field_name: str) -> str:
    """Format field name for display."""
    return field_name.replace("_", " ").title()


def _format_value(value) -> str:
    """Format value for display."""
    if value is None:
        return "None"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        # Format dict as key: value pairs
        return " | ".join(f"{k}: {v}" for k, v in value.items())
    return str(value)
