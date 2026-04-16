"""Phase 1: Schema discovery - scan all fields across all sources."""

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass
class FieldOccurrence:
    """A single occurrence of a field in a source."""

    source_id: str
    source_type: str
    source_date: date
    value: Any


@dataclass
class DiscoveredField:
    """A field discovered across sources."""

    name: str
    occurrences: list[FieldOccurrence] = field(default_factory=list)

    @property
    def source_count(self) -> int:
        return len(self.occurrences)

    @property
    def most_recent_date(self) -> date | None:
        if not self.occurrences:
            return None
        return max(o.source_date for o in self.occurrences)

    @property
    def days_since_most_recent(self) -> int | None:
        if self.most_recent_date is None:
            return None
        return (datetime.now().date() - self.most_recent_date).days


@dataclass
class PayerSchema:
    """Complete discovered schema for a payer."""

    payer: str
    payer_key: str
    fields: dict[str, DiscoveredField] = field(default_factory=dict)
    sources: list[dict] = field(default_factory=list)

    def add_field_occurrence(
        self,
        field_name: str,
        source_id: str,
        source_type: str,
        source_date: date,
        value: Any,
    ):
        """Add a field occurrence."""
        if field_name not in self.fields:
            self.fields[field_name] = DiscoveredField(name=field_name)

        self.fields[field_name].occurrences.append(
            FieldOccurrence(
                source_id=source_id,
                source_type=source_type,
                source_date=source_date,
                value=value,
            )
        )


def discover_schema(data_path: Path) -> dict[str, PayerSchema]:
    """
    Discover schema for all payers from extracted_route_data.json.

    Scans ALL fields at ALL levels (including nested drugs data).
    Returns a PayerSchema for each payer.
    """
    with open(data_path) as f:
        raw_data = json.load(f)

    schemas = {}

    for payer_key, payer_info in raw_data.items():
        schema = PayerSchema(
            payer=payer_info["payer"],
            payer_key=payer_key,
        )

        for source_dict in payer_info["sources"]:
            source_id = source_dict["source_id"]
            source_type = source_dict["source_type"]
            source_date = datetime.strptime(
                source_dict["source_date"], "%Y-%m-%d"
            ).date()

            # Store source metadata
            schema.sources.append({
                "source_id": source_id,
                "source_type": source_type,
                "source_date": source_date,
                "source_name": source_dict["source_name"],
                "retrieved_date": datetime.strptime(
                    source_dict["retrieved_date"], "%Y-%m-%d"
                ).date(),
            })

            # Extract all fields from data
            data = source_dict.get("data", {})
            _extract_fields(
                data=data,
                prefix="",
                schema=schema,
                source_id=source_id,
                source_type=source_type,
                source_date=source_date,
            )

        schemas[payer_key] = schema

    return schemas


def _extract_fields(
    data: dict,
    prefix: str,
    schema: PayerSchema,
    source_id: str,
    source_type: str,
    source_date: date,
):
    """Recursively extract fields from nested data."""
    for key, value in data.items():
        field_name = f"{prefix}{key}" if prefix else key

        if isinstance(value, dict):
            # Check if this is a nested structure (like drugs.Remicade)
            # or a simple dict value
            if key == "drugs":
                # Special handling for drugs - flatten to drugs.{drug_name}.{field}
                for drug_name, drug_data in value.items():
                    if isinstance(drug_data, dict):
                        _extract_fields(
                            data=drug_data,
                            prefix=f"drugs.{drug_name}.",
                            schema=schema,
                            source_id=source_id,
                            source_type=source_type,
                            source_date=source_date,
                        )
            else:
                # Store the dict as a value (e.g., common_denial_reasons)
                schema.add_field_occurrence(
                    field_name=field_name,
                    source_id=source_id,
                    source_type=source_type,
                    source_date=source_date,
                    value=value,
                )
        else:
            # Scalar or list value
            schema.add_field_occurrence(
                field_name=field_name,
                source_id=source_id,
                source_type=source_type,
                source_date=source_date,
                value=value,
            )
