"""JSON report generation."""

import json
from pathlib import Path
from typing import Any

from reconciliation_v2.pipeline.reconcile import PayerReconciliation


def generate_json_report(reconciliation: PayerReconciliation, output_path: Path) -> None:
    """Generate JSON report with full reconciliation details."""

    def serialize_value(v: Any) -> Any:
        """Serialize values for JSON."""
        from datetime import date
        if isinstance(v, date):
            return str(v)
        if hasattr(v, "__dict__"):
            return {k: serialize_value(val) for k, val in v.__dict__.items()}
        if isinstance(v, dict):
            return {k: serialize_value(val) for k, val in v.items()}
        if isinstance(v, list):
            return [serialize_value(x) for x in v]
        return v

    output = {
        "payer": reconciliation.payer,
        "payer_key": reconciliation.payer_key,
        "executive_summary": reconciliation.executive_summary,
        "summary": {
            "total_fields_discovered": reconciliation.total_fields_discovered,
            "total_fields_output": reconciliation.total_fields_output,
            "conflicts_detected": reconciliation.conflicts_detected,
            "focus_drug": reconciliation.focus_drug,
            "focus_drug_selection": reconciliation.focus_drug_selection_reason,
            "fields_validated_against_raw": reconciliation.fields_validated_against_raw,
            "json_raw_conflicts": reconciliation.json_raw_conflicts,
        },
        "payer_warnings": reconciliation.payer_warnings,
        # PRIMARY OUTPUT - actionable route for ops/frontend
        "best_route": serialize_value(reconciliation.best_route),
        "payer_context": serialize_value(reconciliation.payer_context),
        "fields": {},
        "all_drugs": {},  # All drugs with their requirements
        "raw_text_validations": serialize_value(reconciliation.raw_text_validations),
        "raw_fields": {},  # Debug section
    }

    # Serialize fields
    for field_name, field_rec in reconciliation.fields.items():
        output["fields"][field_name] = {
            "value": serialize_value(field_rec.value),
            "confidence": round(field_rec.confidence, 3),
            "source_id": field_rec.source_id,
            "source_type": field_rec.source_type,
            "source_date": str(field_rec.source_date),
            "decision_path": field_rec.decision_path,
            "has_conflicts": field_rec.has_conflicts,
            "all_values": serialize_value(field_rec.all_values),
            "superseded_values": field_rec.superseded_values,
            "supersession_reasons": field_rec.supersession_reasons,
            "notes": field_rec.notes,
            "operational_reality": serialize_value(field_rec.operational_reality),
        }

    # Serialize ALL drugs
    output["all_drugs"] = {}
    for drug_name, drug_info in reconciliation.all_drugs.items():
        output["all_drugs"][drug_name] = {
            "drug_name": drug_info.drug_name,
            "fields": serialize_value(drug_info.fields),
            "sources": drug_info.sources,
            "notes": drug_info.notes,
        }

    # Serialize raw fields (debug section)
    for field_name, field_values in reconciliation.raw_fields.items():
        output["raw_fields"][field_name] = {
            "source_count": field_values.source_count,
            "values": [
                {
                    "value": serialize_value(v.value),
                    "source_id": v.source_id,
                    "source_type": v.source_type,
                    "source_date": str(v.source_date),
                }
                for v in field_values.values
            ],
        }

    output_path.write_text(json.dumps(output, indent=2))
