"""Verify schema discovery and field family detection."""

from pathlib import Path

from reconciliation_v2.discovery.schema import discover_schema
from reconciliation_v2.discovery.field_family import (
    detect_field_families,
    print_schema_summary,
    RelationType,
)


def main():
    data_path = Path("payer_sources/extracted_route_data.json")

    print("=" * 60)
    print("SCHEMA DISCOVERY & FIELD FAMILY DETECTION")
    print("=" * 60)

    # Discover schema
    schemas = discover_schema(data_path)

    # Print summary
    print_schema_summary(schemas)

    # Verification checks
    print("\n" + "=" * 60)
    print("VERIFICATION CHECKS")
    print("=" * 60)

    checks = [
        ("blue_cross_blue_shield", "chart_note_window_days", RelationType.POLICY_UPDATE,
         "BCBS chart_note_window_days has policy_update trigger"),

        ("aetna", "fax_number", RelationType.SUPERSESSION_OLD,
         "Aetna fax_number has supersession_old trigger (fax_number_old)"),

        ("aetna", "fax_number", RelationType.SUPERSESSION_STATUS,
         "Aetna fax_number has supersession_status trigger (fax_old_status)"),

        ("unitedhealthcare", "fax_number", RelationType.QUALIFIER,
         "UHC fax_number has qualifier split (specialty/general)"),

        ("humana", "pa_form", RelationType.SUPERSESSION_OLD,
         "Humana pa_form has supersession_old trigger"),

        ("cigna", "fax_number", RelationType.SUPERSESSION_OLD,
         "Cigna fax_number has supersession_old trigger"),

        ("cigna", "fax_number", RelationType.NOTE,
         "Cigna fax_number has note (fax_note)"),
    ]

    all_passed = True

    for payer_key, base_field, expected_type, description in checks:
        schema = schemas[payer_key]
        families, _ = detect_field_families(schema)

        passed = False
        if base_field in families:
            family = families[base_field]
            if any(r.relation_type == expected_type for r in family.relations):
                passed = True

        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {description}")

        if not passed:
            all_passed = False
            # Debug info
            if base_field in families:
                family = families[base_field]
                print(f"       Found relations: {[r.relation_type.value for r in family.relations]}")
            else:
                print(f"       Base field '{base_field}' not found in families")
                # Check if it exists as a related field
                for bf, fam in families.items():
                    for rel in fam.relations:
                        if base_field in rel.related_field:
                            print(f"       Found as relation of '{bf}'")

    print()
    if all_passed:
        print("All verification checks PASSED")
    else:
        print("Some verification checks FAILED - pattern regexes need fixing")

    return all_passed


if __name__ == "__main__":
    main()
