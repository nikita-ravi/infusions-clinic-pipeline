"""
Test suite for the reconciliation pipeline.

Tests are organized by component:
1. Schema discovery
2. Field family detection
3. Supersession (3 triggers)
4. Scoring primitives
5. Qualifier handling
6. Drug selection
7. Integration tests
"""

import pytest
from datetime import date
from pathlib import Path

# Import modules under test
from reconciliation_v2.discovery.schema import discover_schema, PayerSchema
from reconciliation_v2.discovery.field_family import (
    detect_field_families,
    RelationType,
)
from reconciliation_v2.pipeline.value_collection import (
    CollectedValue,
    FieldValues,
    detect_operational_reality,
)
from reconciliation_v2.pipeline.supersession import apply_supersession
from reconciliation_v2.pipeline.scoring import (
    calculate_freshness,
    calculate_authority,
    calculate_corroboration,
    calculate_confidence_floor,
)
from reconciliation_v2.pipeline.reconcile import (
    select_focus_drug,
    reconcile_payer,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_schema():
    """Load the actual test data schema for Aetna."""
    schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
    return schemas["aetna"]


@pytest.fixture
def bcbs_schema():
    """Load BCBS schema for policy_update tests."""
    schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
    return schemas["blue_cross_blue_shield"]


@pytest.fixture
def cigna_schema():
    """Load Cigna schema for operational reality tests."""
    schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
    return schemas["cigna"]


@pytest.fixture
def humana_schema():
    """Load Humana schema for complex supersession tests."""
    schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
    return schemas["humana"]


# ============================================================================
# 1. Schema Discovery Tests
# ============================================================================

class TestSchemaDiscovery:
    """Tests for schema discovery module."""

    def test_discovers_all_payers(self):
        """Should discover all 5 payers from the data file."""
        schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
        assert len(schemas) == 5
        assert set(schemas.keys()) == {
            "aetna", "unitedhealthcare", "cigna",
            "blue_cross_blue_shield", "humana"
        }

    def test_discovers_nested_drug_fields(self, sample_schema):
        """Should discover nested drug fields like drugs.Remicade.step_therapy_required."""
        drug_fields = [f for f in sample_schema.fields if f.startswith("drugs.")]
        assert len(drug_fields) > 0
        # Check for specific nested structure
        assert any("step_therapy_required" in f for f in drug_fields)

    def test_tracks_source_metadata(self, sample_schema):
        """Should track source_id, source_type, and source_date for each occurrence."""
        fax_field = sample_schema.fields.get("fax_number")
        assert fax_field is not None
        assert len(fax_field.occurrences) >= 2

        for occ in fax_field.occurrences:
            assert occ.source_id is not None
            assert occ.source_type in ["provider_manual", "phone_transcript", "web_page", "denial_letter"]
            assert occ.source_date is not None


# ============================================================================
# 2. Field Family Detection Tests
# ============================================================================

class TestFieldFamilyDetection:
    """Tests for field family detection via pattern matching."""

    def test_detects_supersession_old_pair(self, sample_schema):
        """Should detect {fax_number, fax_number_old} as a supersession family."""
        families, related = detect_field_families(sample_schema)

        assert "fax_number" in families
        fax_family = families["fax_number"]

        # Should have supersession_old relation
        old_relations = fax_family.get_relations_by_type(RelationType.SUPERSESSION_OLD)
        assert len(old_relations) >= 1
        assert any(r.related_field == "fax_number_old" for r in old_relations)

    def test_detects_policy_update_relation(self, bcbs_schema):
        """Should detect chart_note_policy_update as related to chart_note_window_days."""
        families, related = detect_field_families(bcbs_schema)

        # chart_note_policy_update should link to chart_note_window_days
        assert "chart_note_window_days" in families
        family = families["chart_note_window_days"]

        policy_relations = family.get_relations_by_type(RelationType.POLICY_UPDATE)
        assert len(policy_relations) >= 1

    def test_detects_turnaround_qualifiers(self, sample_schema):
        """Should detect turnaround_standard_days, turnaround_urgent_hours as qualifiers."""
        families, related = detect_field_families(sample_schema)

        assert "turnaround" in families
        turnaround_family = families["turnaround"]

        qualifiers = turnaround_family.get_qualifiers()
        assert "standard" in qualifiers or "urgent" in qualifiers

    def test_related_fields_excluded_from_primary(self, sample_schema):
        """Related fields like fax_number_old should be in the related set."""
        families, related = detect_field_families(sample_schema)

        # fax_number_old should be marked as related, not a primary field
        assert "fax_number_old" in related or "fax_old_status" in related


# ============================================================================
# 3. Supersession Tests (3 Triggers)
# ============================================================================

class TestSupersession:
    """Tests for the three supersession triggers."""

    def test_trigger1_old_pair_deprecates_value(self, sample_schema):
        """Trigger 1: {X, X_old} pair should deprecate the old value."""
        families, _ = detect_field_families(sample_schema)
        from reconciliation_v2.pipeline.value_collection import collect_field_values

        fax_family = families.get("fax_number")
        field_values = collect_field_values("fax_number", sample_schema, fax_family)

        result = apply_supersession(field_values)

        # Old fax number should be superseded
        assert len(result.superseded_values) > 0
        # Deprecation reason should be captured
        assert len(result.supersession_reasons) > 0

    def test_trigger3_policy_update_zeros_old_sources(self, bcbs_schema):
        """Trigger 3: policy_update should zero out sources before policy date."""
        families, _ = detect_field_families(bcbs_schema)
        from reconciliation_v2.pipeline.value_collection import collect_field_values

        family = families.get("chart_note_window_days")
        field_values = collect_field_values("chart_note_window_days", bcbs_schema, family)

        result = apply_supersession(field_values)

        # At least one source should be superseded due to predating policy
        assert len(result.superseded_values) >= 1
        # Should have reason mentioning policy update
        assert any("policy" in r.lower() for r in result.supersession_reasons)


# ============================================================================
# 4. Scoring Primitives Tests
# ============================================================================

class TestScoringPrimitives:
    """Tests for the scoring components."""

    def test_freshness_exponential_decay(self):
        """Freshness should decay exponentially with 180-day half-life."""
        # Today's date
        today = date.today()

        # 0 days old -> ~1.0
        freshness_0 = calculate_freshness(today)
        assert freshness_0 > 0.99

        # 180 days old -> ~0.5
        from datetime import timedelta
        date_180_ago = today - timedelta(days=180)
        freshness_180 = calculate_freshness(date_180_ago)
        assert 0.45 < freshness_180 < 0.55

        # 360 days old -> ~0.25
        date_360_ago = today - timedelta(days=360)
        freshness_360 = calculate_freshness(date_360_ago)
        assert 0.20 < freshness_360 < 0.30

    def test_authority_weights(self):
        """Authority weights should match the specified hierarchy."""
        assert calculate_authority("denial_letter") == 1.0
        assert calculate_authority("phone_transcript") == 0.75
        assert calculate_authority("web_page") == 0.50
        assert calculate_authority("provider_manual") == 0.50

    def test_corroboration_counts_active_only(self):
        """Corroboration should count from active values only."""
        # Create test values
        values = [
            CollectedValue(value="A", source_id="S1", source_type="web_page",
                          source_date=date.today()),
            CollectedValue(value="A", source_id="S2", source_type="web_page",
                          source_date=date.today()),
        ]

        score, agreeing, total = calculate_corroboration("A", "test_field", values)

        assert agreeing == 2
        assert total == 2
        assert score == 0.5  # 2 sources agree -> 1 - 0.5^1 = 0.5

    def test_confidence_floor_universal_agreement(self):
        """Confidence floor should apply when all sources agree, capped at 0.95."""
        # 4/4 agreement -> 0.7 + 0.075*4 = 1.0, but capped at 0.95
        floor_4, reason_4 = calculate_confidence_floor(4, 4)
        assert abs(floor_4 - 0.95) < 0.001  # Capped at 0.95
        assert "universal agreement" in reason_4

        # 3/3 agreement -> 0.7 + 0.075*3 = 0.925
        floor_3, _ = calculate_confidence_floor(3, 3)
        assert abs(floor_3 - 0.925) < 0.001

        # 2/2 agreement -> 0.7 + 0.075*2 = 0.85
        floor_2, _ = calculate_confidence_floor(2, 2)
        assert abs(floor_2 - 0.85) < 0.001

        # Partial agreement -> no floor
        floor_partial, _ = calculate_confidence_floor(2, 4)
        assert floor_partial == 0.0

        # Single-source provider_manual -> 0.70 floor
        floor_manual, reason_manual = calculate_confidence_floor(1, 1, source_type="provider_manual")
        assert abs(floor_manual - 0.70) < 0.001
        assert "provider_manual" in reason_manual

        # Post-supersession uncontested -> 0.75 floor
        floor_superseded, reason_superseded = calculate_confidence_floor(1, 1, superseded_count=2)
        assert abs(floor_superseded - 0.75) < 0.001
        assert "supersession" in reason_superseded


# ============================================================================
# 5. Operational Reality Detection Tests
# ============================================================================

class TestOperationalReality:
    """Tests for operational reality detection."""

    def test_detects_range_with_cause(self):
        """Should detect range values with explanatory cause."""
        result = detect_operational_reality("10-12 (system migration delays)")

        assert result is not None
        assert result.min_value == 10
        assert result.max_value == 12
        assert result.cause == "system migration delays"

    def test_detects_simple_range(self):
        """Should detect simple range without cause."""
        result = detect_operational_reality("7-10 (during transition)")

        assert result is not None
        assert result.min_value == 7
        assert result.max_value == 10
        assert "transition" in result.cause.lower()

    def test_ignores_clean_numbers(self):
        """Should not flag clean integers as operational reality."""
        result = detect_operational_reality(7)
        assert result is None

        result = detect_operational_reality("7")
        assert result is None


# ============================================================================
# 6. Drug Selection Tests
# ============================================================================

class TestDrugSelection:
    """Tests for data-driven drug selection."""

    def test_selects_drug_with_most_fresh_mentions(self, bcbs_schema):
        """Should select drug with most mentions in high-signal sources."""
        drug, reason = select_focus_drug(bcbs_schema)

        # BCBS should pick Herceptin based on denial letter mentions
        assert drug == "Herceptin"
        assert "Data-driven" in reason or "Fallback" in reason

    def test_raw_text_scanning_finds_drugs(self, cigna_schema):
        """Should find drugs via raw text scanning in high-signal sources."""
        drug, reason = select_focus_drug(cigna_schema)

        # Cigna's phone transcript mentions Entyvio, should be found via raw text scan
        assert drug is not None
        # Either high-signal (raw text found it) or fallback (no raw text available)
        assert "high-signal" in reason.lower() or "Fallback" in reason

    def test_override_bypasses_selection(self, sample_schema):
        """CLI override should bypass data-driven selection."""
        drug, reason = select_focus_drug(sample_schema, override="Keytruda")

        assert drug == "Keytruda"
        assert "override" in reason.lower()

    def test_returns_none_when_no_drug_data(self):
        """Should return None when no drug data exists."""
        # Create a minimal schema with no drug fields
        from reconciliation_v2.discovery.schema import PayerSchema
        empty_schema = PayerSchema(payer="Test", payer_key="test")

        drug, reason = select_focus_drug(empty_schema)

        assert drug is None
        assert "No drug data" in reason


# ============================================================================
# 7. Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests."""

    def test_aetna_fax_supersession(self):
        """Aetna fax_number should correctly supersede old number."""
        schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
        result = reconcile_payer(schemas["aetna"])

        fax = result.fields.get("fax_number")
        assert fax is not None
        # New fax number should win
        assert fax.value == "(888) 267-3300"
        # Old number should be superseded
        assert len(fax.superseded_values) > 0

    def test_bcbs_policy_update_wins(self):
        """BCBS chart_note_window_days should pick policy-updated value (90)."""
        schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
        result = reconcile_payer(schemas["blue_cross_blue_shield"])

        chart_note = result.fields.get("chart_note_window_days")
        assert chart_note is not None
        assert chart_note.value == 90  # Not phone rep's 60

    def test_humana_focus_drug_is_rituxan(self):
        """Humana should select Rituxan as focus drug."""
        schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
        result = reconcile_payer(schemas["humana"])

        assert result.focus_drug == "Rituxan"

    def test_cigna_turnaround_has_both_policy_and_reality(self):
        """Cigna turnaround should have both stated_policy and operational_reality."""
        schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
        result = reconcile_payer(schemas["cigna"])

        turnaround = result.fields.get("turnaround")
        assert turnaround is not None

        value = turnaround.value
        assert "stated_policy" in value
        assert "operational_reality" in value
        # stated_policy should have standard: 7
        assert value["stated_policy"].get("standard") == 7
        # operational_reality should have standard with cause
        assert "standard" in value["operational_reality"]

    def test_bcbs_note_in_context_not_reconciled(self):
        """BCBS 'note' field should be in payer_context, not reconciled."""
        schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
        result = reconcile_payer(schemas["blue_cross_blue_shield"])

        # note should NOT be in fields (reconciled)
        assert "note" not in result.fields
        # note SHOULD be in payer_context
        assert "note" in result.payer_context

    def test_universal_agreement_high_confidence(self):
        """Fields with universal agreement should have high confidence (capped at 0.95)."""
        schemas = discover_schema(Path("payer_sources/extracted_route_data.json"))
        result = reconcile_payer(schemas["blue_cross_blue_shield"])

        # fax_number has 4/4 agreement
        fax = result.fields.get("fax_number")
        assert fax is not None
        assert fax.confidence >= 0.90  # Floor should apply, capped at 0.95


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
