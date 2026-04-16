# Prior Authorization Route: Humana

**Focus Drug:** Remicade

## Summary

- **Total Sources:** 4
  - provider_manual: 1
  - phone_transcript: 1
  - web_page: 1
  - denial_letter: 1
- **Fields Reconciled:** 9
- **Conflicts Detected:** 4
- **High Confidence (≥0.8):** 6 fields
- **Low Confidence (<0.5):** 0 fields

## Reconciled Route

### Chart Note Window Days

**Value:** `90`
**Confidence:** 0.95

### Fax Number

**Value:** `8005230023`
**Confidence:** 1.00

### Pa Form

**Value:** `HUM-AUTH-2026`
**Confidence:** 0.95

### Phone Urgent

**Value:** `8005552546`
**Confidence:** 0.75

### Portal Url

**Value:** `availity.com`
**Confidence:** 1.00

### Remicade Requirements

**Value:** `step_therapy_required: True | biosimilar_attestation: True | auth_period_months: 6`
**Confidence:** 0.85

### Submission Methods

**Value:** `fax, phone_urgent_only, portal`
**Confidence:** 0.75

### Turnaround Standard Days

**Value:** `7`
**Confidence:** 0.75

### Turnaround Urgent Hours

**Value:** `48`
**Confidence:** 0.90

## Conflicts & Warnings

### Chart Note Window Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `HUM-SRC-001`: `60`
- ✓ `HUM-SRC-002`: `90`
- ✗ `HUM-SRC-003`: `60`
- ✗ `HUM-SRC-004`: `90`

**Selected:** `90`
**Confidence:** 0.95

### Pa Form

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `HUM-SRC-001`: `HUM-AUTH-2024`
- ✓ `HUM-SRC-002`: `HUM-AUTH-2026`
- ✗ `HUM-SRC-003`: `HUM-AUTH-2024`
- ✗ `HUM-SRC-004`: `HUM-AUTH-2026`

**Selected:** `HUM-AUTH-2026`
**Confidence:** 0.95

### Submission Methods

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `HUM-SRC-001`: `portal, fax, phone_urgent_only`
- ✗ `HUM-SRC-002`: `fax, portal`
- ✓ `HUM-SRC-003`: `portal, fax, phone_urgent_only`

**Selected:** `fax, phone_urgent_only, portal`
**Confidence:** 0.75

### Turnaround Standard Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `HUM-SRC-001`: `7`
- ✗ `HUM-SRC-002`: `10-14 (system migration delays)`
- ✓ `HUM-SRC-003`: `7`

**Selected:** `7`
**Confidence:** 0.75

## Decision Audit Trail

Detailed decision paths for all fields. Each path shows the rules applied in order.

### Chart Note Window Days

```
1. collect_values: Collected 4 values from sources → Sources: ['HUM-SRC-001', 'HUM-SRC-002', 'HUM-SRC-003', 'HUM-SRC-004']
2. chart_note_policy_update: Recent policy update detected, taking maximum window → Selected: 90 days
```

### Fax Number

```
1. collect_values: Collected 4 values from sources → Sources: ['HUM-SRC-001', 'HUM-SRC-002', 'HUM-SRC-003', 'HUM-SRC-004']
2. recency_boost: Source is 37 days old → Boost: +0.20
3. authority_boost: Source type: denial_letter → Boost: +0.25
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
5. final_confidence: Final confidence calculation → Score: 1.00
```

### Pa Form

```
1. collect_values: Collected 4 values from sources → Sources: ['HUM-SRC-001', 'HUM-SRC-002', 'HUM-SRC-003', 'HUM-SRC-004']
2. explicit_deprecation: Found pa_form_old → pa_form pair in HUM-SRC-002 → Deprecated: HUM-AUTH-2024, Superseding: HUM-AUTH-2026
3. prefer_latest_form_version: Selected form with highest version number → Selected: HUM-AUTH-2026 (version 2026)
```

### Phone Urgent

```
1. collect_values: Collected 2 values from sources → Sources: ['HUM-SRC-001', 'HUM-SRC-003']
2. recency_boost: Source is 378 days old → Boost: +0.00
3. authority_boost: Source type: web_page → Boost: +0.15
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
5. final_confidence: Final confidence calculation → Score: 0.75
```

### Portal Url

```
1. collect_values: Collected 4 values from sources → Sources: ['HUM-SRC-001', 'HUM-SRC-002', 'HUM-SRC-003', 'HUM-SRC-004']
2. recency_boost: Source is 37 days old → Boost: +0.20
3. authority_boost: Source type: denial_letter → Boost: +0.25
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
5. final_confidence: Final confidence calculation → Score: 1.00
```

### Remicade Requirements

```
1. drug_requirements_merged: Merged Remicade requirements from 1 sources → Used most recent source: HUM-SRC-001
```

### Submission Methods

```
1. collect_values: Collected 3 values from sources → Sources: ['HUM-SRC-001', 'HUM-SRC-002', 'HUM-SRC-003']
2. recency_boost: Source is 378 days old → Boost: +0.00
3. authority_boost: Source type: web_page → Boost: +0.15
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
5. final_confidence: Final confidence calculation → Score: 0.75
```

### Turnaround Standard Days

```
1. collect_values: Collected 3 values from sources → Sources: ['HUM-SRC-001', 'HUM-SRC-002', 'HUM-SRC-003']
2. recency_boost: Source is 378 days old → Boost: +0.00
3. authority_boost: Source type: web_page → Boost: +0.15
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
5. final_confidence: Final confidence calculation → Score: 0.75
```

### Turnaround Urgent Hours

```
1. collect_values: Collected 3 values from sources → Sources: ['HUM-SRC-001', 'HUM-SRC-002', 'HUM-SRC-003']
2. recency_boost: Source is 26 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
5. warning_penalty: Operational warnings detected → Penalty: -0.30
6. final_confidence: Final confidence calculation → Score: 0.90
```
