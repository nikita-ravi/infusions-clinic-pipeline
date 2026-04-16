"""Schema discovery and field family detection."""

from reconciliation_v2.discovery.schema import discover_schema
from reconciliation_v2.discovery.field_family import (
    FieldFamily,
    detect_field_families,
    RelationType,
)

__all__ = [
    "discover_schema",
    "FieldFamily",
    "detect_field_families",
    "RelationType",
]
