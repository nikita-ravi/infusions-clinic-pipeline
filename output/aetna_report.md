# Prior Authorization Route: Aetna

**Focus Drug:** Remicade

## Summary

- **Total Sources:** 4
  - provider_manual: 1
  - phone_transcript: 1
  - web_page: 1
  - denial_letter: 1
- **Fields Reconciled:** 9
- **Conflicts Detected:** 4
- **High Confidence (≥0.8):** 8 fields
- **Low Confidence (<0.5):** 1 fields

## Reconciled Route

### Chart Note Window Days

**Value:** `90`
**Confidence:** 0.95

### Fax Number

**Value:** `8882673300`
**Confidence:** 1.00

### Pa Form

**Value:** `AET-PA-2025`
**Confidence:** 0.95

### Portal Url

**Value:** `availity.com`
**Confidence:** 1.00

### Remicade Requirements

**Value:** `step_therapy_required: True | notes: Step therapy docs required`
**Confidence:** 0.85

### Submission Methods

**Value:** `portal, fax`
**Confidence:** 0.95

### Turnaround Standard Days

**Value:** `5`
**Confidence:** 1.00

### Turnaround Urgent Hours

**Value:** `24`
**Confidence:** 1.00

## Conflicts & Warnings

### Chart Note Window Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `AET-SRC-001`: `60`
- ✓ `AET-SRC-002`: `90`
- ✗ `AET-SRC-003`: `60`
- ✗ `AET-SRC-004`: `90`

**Selected:** `90`
**Confidence:** 0.95

### Fax Number

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `AET-SRC-001`: `(888) 267-3277`
- ✓ `AET-SRC-002`: `(888) 267-3300`
- ✗ `AET-SRC-003`: `(888) 267-3277`
- ✗ `AET-SRC-004`: `(888) 267-3300`

**Selected:** `8882673300`
**Confidence:** 1.00

### Pa Form

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✓ `AET-SRC-001`: `AET-PA-2025`
- ✗ `AET-SRC-002`: `None`
- ✗ `AET-SRC-003`: `AET-PA-2024`

**Selected:** `AET-PA-2025`
**Confidence:** 0.95

### Phone Urgent

**Selected:** `None`
**Confidence:** 0.00

### Remicade Requirements

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `AET-SRC-001`: `step_therapy_required: True | auth_period_months: 6 | notes: Specialist diagnosis, conventional therapy failure`
- ✓ `AET-SRC-002`: `step_therapy_required: True | notes: Step therapy docs required`
- ✗ `AET-SRC-003`: `step_therapy_required: True | auth_period_months: 6`

**Selected:** `step_therapy_required: True | notes: Step therapy docs required`
**Confidence:** 0.85

## Decision Audit Trail

Detailed decision paths for all fields. Each path shows the rules applied in order.

### Chart Note Window Days

```
1. collect_values: Collected 4 values from sources → Sources: ['AET-SRC-001', 'AET-SRC-002', 'AET-SRC-003', 'AET-SRC-004']
2. chart_note_policy_update: Recent policy update detected, taking maximum window → Selected: 90 days
```

### Fax Number

```
1. collect_values: Collected 4 values from sources → Sources: ['AET-SRC-001', 'AET-SRC-002', 'AET-SRC-003', 'AET-SRC-004']
2. explicit_deprecation: Found fax_number_old → fax_number pair in AET-SRC-002 → Deprecated: (888) 267-3277, Superseding: (888) 267-3300
3. deprecation_status: Found deprecation status: Decommissioned February 1, 2026 → Deprecated: (888) 267-3277
4. explicit_deprecation: Found fax_number_old → fax_number pair in AET-SRC-004 → Deprecated: (888) 267-3277, Superseding: (888) 267-3300
5. deprecation_status: Found deprecation status: No longer active for infusion medication PAs as of Feb 2026 → Deprecated: (888) 267-3277
6. recency_boost: Source is 23 days old → Boost: +0.30
7. authority_boost: Source type: phone_transcript → Boost: +0.20
8. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
9. warning_penalty: Operational warnings detected → Penalty: -0.05
10. final_confidence: Final confidence calculation → Score: 1.00
```

### Pa Form

```
1. collect_values: Collected 3 values from sources → Sources: ['AET-SRC-001', 'AET-SRC-002', 'AET-SRC-003']
2. prefer_latest_form_version: Selected form with highest version number → Selected: AET-PA-2025 (version 2025)
```

### Portal Url

```
1. collect_values: Collected 4 values from sources → Sources: ['AET-SRC-001', 'AET-SRC-002', 'AET-SRC-003', 'AET-SRC-004']
2. recency_boost: Source is 23 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
5. warning_penalty: Operational warnings detected → Penalty: -0.05
6. final_confidence: Final confidence calculation → Score: 1.00
```

### Remicade Requirements

```
1. drug_requirements_merged: Merged Remicade requirements from 3 sources → Used most recent source: AET-SRC-002
```

### Submission Methods

```
1. collect_values: Collected 3 values from sources → Sources: ['AET-SRC-001', 'AET-SRC-002', 'AET-SRC-003']
2. prefer_portal_submission: Portal indicated as preferred method → Reordered methods: ['portal', 'fax']
```

### Turnaround Standard Days

```
1. collect_values: Collected 2 values from sources → Sources: ['AET-SRC-001', 'AET-SRC-002']
2. recency_boost: Source is 23 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
5. warning_penalty: Operational warnings detected → Penalty: -0.05
6. final_confidence: Final confidence calculation → Score: 1.00
```

### Turnaround Urgent Hours

```
1. collect_values: Collected 2 values from sources → Sources: ['AET-SRC-001', 'AET-SRC-002']
2. recency_boost: Source is 23 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
5. warning_penalty: Operational warnings detected → Penalty: -0.05
6. final_confidence: Final confidence calculation → Score: 1.00
```
