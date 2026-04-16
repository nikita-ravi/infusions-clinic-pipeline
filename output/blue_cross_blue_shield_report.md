# Prior Authorization Route: Anthem Blue Cross Blue Shield

**Focus Drug:** Remicade

## Summary

- **Total Sources:** 4
  - provider_manual: 1
  - phone_transcript: 1
  - web_page: 1
  - denial_letter: 1
- **Fields Reconciled:** 9
- **Conflicts Detected:** 2
- **High Confidence (≥0.8):** 8 fields
- **Low Confidence (<0.5):** 0 fields

## Reconciled Route

### Chart Note Window Days

**Value:** `90`
**Confidence:** 0.95

### Fax Number

**Value:** `8444050296`
**Confidence:** 1.00

### Pa Form

**Value:** `ANT-MED-PA-25`
**Confidence:** 0.95

### Phone Urgent

**Value:** `800274776711`
**Confidence:** 0.75

### Portal Url

**Value:** `anthem.com/providers`
**Confidence:** 1.00

### Remicade Requirements

**Value:** `biosimilar_preferred: True | step_therapy_required: True`
**Confidence:** 0.85

### Submission Methods

**Value:** `fax, phone_urgent_only, portal`
**Confidence:** 0.85

### Turnaround Standard Days

**Value:** `5`
**Confidence:** 1.00

### Turnaround Urgent Hours

**Value:** `24`
**Confidence:** 0.85

## Conflicts & Warnings

### Chart Note Window Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `BCB-SRC-001`: `60`
- ✗ `BCB-SRC-002`: `60`
- ✓ `BCB-SRC-003`: `90`
- ✗ `BCB-SRC-004`: `90`

**Selected:** `90`
**Confidence:** 0.95

### Phone Urgent

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `BCB-SRC-001`: `(800) 274-7767`
- ✓ `BCB-SRC-003`: `(800) 274-7767, Option 1, Option 1`

**Selected:** `800274776711`
**Confidence:** 0.75

## Decision Audit Trail

Detailed decision paths for all fields. Each path shows the rules applied in order.

### Chart Note Window Days

```
1. collect_values: Collected 4 values from sources → Sources: ['BCB-SRC-001', 'BCB-SRC-002', 'BCB-SRC-003', 'BCB-SRC-004']
2. recent_denial_letter_authority: Recent denial letter (2026-03-18) carries authority → Denial letter value takes precedence
3. chart_note_policy_update: Recent policy update detected, taking maximum window → Selected: 90 days
```

### Fax Number

```
1. collect_values: Collected 4 values from sources → Sources: ['BCB-SRC-001', 'BCB-SRC-002', 'BCB-SRC-003', 'BCB-SRC-004']
2. recent_denial_letter_authority: Recent denial letter (2026-03-18) carries authority → Denial letter value takes precedence
3. recency_boost: Source is 25 days old → Boost: +0.30
4. authority_boost: Source type: phone_transcript → Boost: +0.20
5. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
6. final_confidence: Final confidence calculation → Score: 1.00
```

### Pa Form

```
1. collect_values: Collected 4 values from sources → Sources: ['BCB-SRC-001', 'BCB-SRC-002', 'BCB-SRC-003', 'BCB-SRC-004']
2. recent_denial_letter_authority: Recent denial letter (2026-03-18) carries authority → Denial letter value takes precedence
3. prefer_latest_form_version: Selected form with highest version number → Selected: ANT-MED-PA-25 (version 25)
```

### Phone Urgent

```
1. collect_values: Collected 2 values from sources → Sources: ['BCB-SRC-001', 'BCB-SRC-003']
2. recency_boost: Source is 164 days old → Boost: +0.10
3. authority_boost: Source type: web_page → Boost: +0.15
4. final_confidence: Final confidence calculation → Score: 0.75
```

### Portal Url

```
1. collect_values: Collected 3 values from sources → Sources: ['BCB-SRC-001', 'BCB-SRC-003', 'BCB-SRC-004']
2. recent_denial_letter_authority: Recent denial letter (2026-03-18) carries authority → Denial letter value takes precedence
3. recency_boost: Source is 27 days old → Boost: +0.30
4. authority_boost: Source type: denial_letter → Boost: +0.25
5. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
6. final_confidence: Final confidence calculation → Score: 1.00
```

### Remicade Requirements

```
1. drug_requirements_merged: Merged Remicade requirements from 1 sources → Used most recent source: BCB-SRC-001
```

### Submission Methods

```
1. collect_values: Collected 2 values from sources → Sources: ['BCB-SRC-001', 'BCB-SRC-003']
2. recency_boost: Source is 164 days old → Boost: +0.10
3. authority_boost: Source type: web_page → Boost: +0.15
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
5. final_confidence: Final confidence calculation → Score: 0.85
```

### Turnaround Standard Days

```
1. collect_values: Collected 3 values from sources → Sources: ['BCB-SRC-001', 'BCB-SRC-002', 'BCB-SRC-003']
2. recency_boost: Source is 25 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
5. final_confidence: Final confidence calculation → Score: 1.00
```

### Turnaround Urgent Hours

```
1. collect_values: Collected 2 values from sources → Sources: ['BCB-SRC-001', 'BCB-SRC-003']
2. recency_boost: Source is 164 days old → Boost: +0.10
3. authority_boost: Source type: web_page → Boost: +0.15
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
5. final_confidence: Final confidence calculation → Score: 0.85
```
