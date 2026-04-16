"""JSON report generation."""

import json
from pathlib import Path

from reconciliation.models.decision import PayerReconciliation


def generate_json_report(
    reconciliation: PayerReconciliation,
    output_path: Path,
) -> None:
    """
    Generate JSON report with full reconciliation details.

    Output structure:
    {
      "payer": "...",
      "summary": {...},
      "fields": {
        "field_name": {
          "value": ...,
          "confidence": 0.95,
          "decision_path": [...],
          "contributing_sources": [...],
          "superseded_sources": [...],
          "reasoning": "...",
          "conflicts_detected": true/false
        }
      }
    }
    """
    output_data = {
        "payer": reconciliation.payer,
        "summary": reconciliation.summary,
        "fields": {},
    }

    for field_name, field_rec in reconciliation.fields.items():
        output_data["fields"][field_name] = {
            "value": field_rec.value,
            "confidence": round(field_rec.confidence, 2),
            "decision_path": field_rec.decision_path,
            "contributing_sources": field_rec.contributing_sources,
            "superseded_sources": field_rec.superseded_sources,
            "conflicts_detected": field_rec.conflicts_detected,
            "reasoning": field_rec.reasoning,
        }

        # Include raw values if conflicts detected
        if field_rec.conflicts_detected:
            output_data["fields"][field_name]["raw_values"] = field_rec.raw_values

    output_path.write_text(json.dumps(output_data, indent=2))
