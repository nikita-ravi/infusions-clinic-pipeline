# Prior Authorization Route: UnitedHealthcare

**Focus Drug:** Remicade

## Summary

- **Total Sources:** 4
  - provider_manual: 1
  - phone_transcript: 1
  - web_page: 1
  - denial_letter: 1
- **Fields Reconciled:** 9
- **Conflicts Detected:** 6
- **High Confidence (≥0.8):** 9 fields
- **Low Confidence (<0.5):** 0 fields

## Reconciled Route

### Chart Note Window Days

**Value:** `90`
**Confidence:** 0.95

### Fax Number

**Value:** `(800) 699-4702`
**Confidence:** 0.95

### Pa Form

**Value:** `UHC-PA-200`
**Confidence:** 0.95

### Phone Urgent

**Value:** `8003316689`
**Confidence:** 0.95

### Portal Url

**Value:** `uhcprovider.com`
**Confidence:** 1.00

### Remicade Requirements

**Value:** `biosimilar_required: True | notes: #1 denial reason is missing biosimilar trial/justification`
**Confidence:** 0.85

### Submission Methods

**Value:** `fax, portal`
**Confidence:** 1.00

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
- ✗ `UHC-SRC-001`: `60`
- ✗ `UHC-SRC-002`: `60`
- ✓ `UHC-SRC-003`: `90`
- ✗ `UHC-SRC-004`: `90`

**Selected:** `90`
**Confidence:** 0.95

### Fax Number

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `UHC-SRC-001`: `(800) 699-4711`
- ✓ `UHC-SRC-002`: `(800) 699-4702`

**Selected:** `(800) 699-4702`
**Confidence:** 0.95

### Pa Form

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `UHC-SRC-001`: `UHC-PA-100`
- ✓ `UHC-SRC-002`: `UHC-PA-200`
- ✗ `UHC-SRC-003`: `UHC-PA-200`
- ✗ `UHC-SRC-004`: `UHC-PA-200`

**Selected:** `UHC-PA-200`
**Confidence:** 0.95

### Remicade Requirements

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `UHC-SRC-001`: `step_therapy_required: True | biosimilar_preferred: True | auth_period_months: 6 | notes: Weight-based dosing docs required`
- ✓ `UHC-SRC-002`: `biosimilar_required: True | notes: #1 denial reason is missing biosimilar trial/justification`
- ✗ `UHC-SRC-003`: `biosimilar_required: True | auth_period_months: 6`

**Selected:** `biosimilar_required: True | notes: #1 denial reason is missing biosimilar trial/justification`
**Confidence:** 0.85

### Submission Methods

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `UHC-SRC-001`: `portal, fax, phone_urgent_only`
- ✓ `UHC-SRC-002`: `portal, fax`
- ✗ `UHC-SRC-003`: `portal, fax, phone_urgent_only`

**Selected:** `fax, portal`
**Confidence:** 1.00

### Turnaround Standard Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `UHC-SRC-001`: `5`
- ✓ `UHC-SRC-002`: `5`
- ✗ `UHC-SRC-003`: `3-5`

**Selected:** `5`
**Confidence:** 1.00

## Decision Audit Trail

Detailed decision paths for all fields. Each path shows the rules applied in order.

### Chart Note Window Days

```
1. collect_values: Collected 4 values from sources → Sources: ['UHC-SRC-001', 'UHC-SRC-002', 'UHC-SRC-003', 'UHC-SRC-004']
2. chart_note_policy_update: Recent policy update detected, taking maximum window → Selected: 90 days
```

### Fax Number

```
1. collect_values: Collected 2 values from sources → Sources: ['UHC-SRC-001', 'UHC-SRC-002']
2. prefer_specialty_fax: Specialty fax preferred over general (specialty_note) → Selected: (800) 699-4702
```

### Pa Form

```
1. collect_values: Collected 4 values from sources → Sources: ['UHC-SRC-001', 'UHC-SRC-002', 'UHC-SRC-003', 'UHC-SRC-004']
2. explicit_deprecation: Found pa_form_old → pa_form pair in UHC-SRC-002 → Deprecated: UHC-PA-100, Superseding: UHC-PA-200
3. prefer_latest_form_version: Selected form with highest version number → Selected: UHC-PA-200 (version 200)
```

### Phone Urgent

```
1. collect_values: Collected 2 values from sources → Sources: ['UHC-SRC-001', 'UHC-SRC-003']
2. recency_boost: Source is 44 days old → Boost: +0.20
3. authority_boost: Source type: web_page → Boost: +0.15
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
5. final_confidence: Final confidence calculation → Score: 0.95
```

### Portal Url

```
1. collect_values: Collected 4 values from sources → Sources: ['UHC-SRC-001', 'UHC-SRC-002', 'UHC-SRC-003', 'UHC-SRC-004']
2. recency_boost: Source is 27 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
5. final_confidence: Final confidence calculation → Score: 1.00
```

### Remicade Requirements

```
1. drug_requirements_merged: Merged Remicade requirements from 3 sources → Used most recent source: UHC-SRC-002
```

### Submission Methods

```
1. collect_values: Collected 3 values from sources → Sources: ['UHC-SRC-001', 'UHC-SRC-002', 'UHC-SRC-003']
2. recency_boost: Source is 27 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. final_confidence: Final confidence calculation → Score: 1.00
```

### Turnaround Standard Days

```
1. collect_values: Collected 3 values from sources → Sources: ['UHC-SRC-001', 'UHC-SRC-002', 'UHC-SRC-003']
2. recency_boost: Source is 27 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
5. final_confidence: Final confidence calculation → Score: 1.00
```

### Turnaround Urgent Hours

```
1. collect_values: Collected 3 values from sources → Sources: ['UHC-SRC-001', 'UHC-SRC-002', 'UHC-SRC-003']
2. recency_boost: Source is 27 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
5. final_confidence: Final confidence calculation → Score: 1.00
```
