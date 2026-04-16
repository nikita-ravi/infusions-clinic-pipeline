# Prior Authorization Route: Cigna

**Focus Drug:** Remicade

## Summary

- **Total Sources:** 4
  - provider_manual: 1
  - phone_transcript: 1
  - web_page: 1
  - denial_letter: 1
- **Fields Reconciled:** 9
- **Conflicts Detected:** 5
- **High Confidence (≥0.8):** 6 fields
- **Low Confidence (<0.5):** 1 fields

## Reconciled Route

### Chart Note Window Days

**Value:** `90`
**Confidence:** 0.95

### Fax Number

**Value:** `(800) 768-4700`
**Confidence:** 0.95

### Pa Form

**Value:** `CG-PA-002`
**Confidence:** 0.95

### Portal Url

**Value:** `cignaforhcp.com`
**Confidence:** 0.90

### Remicade Requirements

**Value:** `step_therapy_required: True | auth_period_months: 6 | notes: Biosimilar preferred for new starts (2025)`
**Confidence:** 0.85

### Submission Methods

**Value:** `fax, portal`
**Confidence:** 0.70

### Turnaround Standard Days

**Value:** `7`
**Confidence:** 0.70

### Turnaround Urgent Hours

**Value:** `24`
**Confidence:** 0.90

## Conflicts & Warnings

### Chart Note Window Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `CGN-SRC-001`: `60`
- ✓ `CGN-SRC-002`: `90`
- ✗ `CGN-SRC-003`: `60`
- ✗ `CGN-SRC-004`: `90`

**Selected:** `90`
**Confidence:** 0.95

### Fax Number

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `CGN-SRC-001`: `(800) 768-4695`
- ✓ `CGN-SRC-002`: `(800) 768-4700`
- ✗ `CGN-SRC-003`: `(800) 768-4695`
- ✗ `CGN-SRC-004`: `(800) 768-4700`

**Selected:** `(800) 768-4700`
**Confidence:** 0.95

### Pa Form

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `CGN-SRC-001`: `CG-PA-001`
- ✓ `CGN-SRC-002`: `CG-PA-002`
- ✗ `CGN-SRC-003`: `CG-PA-001`
- ✗ `CGN-SRC-004`: `CG-PA-002`

**Selected:** `CG-PA-002`
**Confidence:** 0.95

### Phone Urgent

**Selected:** `None`
**Confidence:** 0.00

### Submission Methods

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `CGN-SRC-001`: `portal, fax, phone_urgent_only`
- ✓ `CGN-SRC-002`: `portal, fax`
- ✗ `CGN-SRC-003`: `portal, fax, phone`

**Selected:** `fax, portal`
**Confidence:** 0.70

### Turnaround Standard Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✓ `CGN-SRC-001`: `7`
- ✗ `CGN-SRC-002`: `10-12 (system migration delays)`
- ✗ `CGN-SRC-003`: `7`

**Selected:** `7`
**Confidence:** 0.70

## Decision Audit Trail

Detailed decision paths for all fields. Each path shows the rules applied in order.

### Chart Note Window Days

```
1. collect_values: Collected 4 values from sources → Sources: ['CGN-SRC-001', 'CGN-SRC-002', 'CGN-SRC-003', 'CGN-SRC-004']
2. chart_note_policy_update: Recent policy update detected, taking maximum window → Selected: 90 days
```

### Fax Number

```
1. collect_values: Collected 4 values from sources → Sources: ['CGN-SRC-001', 'CGN-SRC-002', 'CGN-SRC-003', 'CGN-SRC-004']
2. explicit_deprecation: Found fax_number_old → fax_number pair in CGN-SRC-002 → Deprecated: (800) 768-4695, Superseding: (800) 768-4700
3. explicit_deprecation: Found fax_number_old → fax_number pair in CGN-SRC-004 → Deprecated: (800) 768-4695, Superseding: (800) 768-4700
4. prefer_specialty_fax: Specialty fax preferred over general (specialty_note) → Selected: (800) 768-4700
```

### Pa Form

```
1. collect_values: Collected 4 values from sources → Sources: ['CGN-SRC-001', 'CGN-SRC-002', 'CGN-SRC-003', 'CGN-SRC-004']
2. explicit_deprecation: Found pa_form_old → pa_form pair in CGN-SRC-002 → Deprecated: CG-PA-001, Superseding: CG-PA-002
3. prefer_latest_form_version: Selected form with highest version number → Selected: CG-PA-002 (version 2)
```

### Portal Url

```
1. collect_values: Collected 3 values from sources → Sources: ['CGN-SRC-001', 'CGN-SRC-002', 'CGN-SRC-003']
2. recency_boost: Source is 21 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
5. warning_penalty: Operational warnings detected → Penalty: -0.30
6. final_confidence: Final confidence calculation → Score: 0.90
```

### Remicade Requirements

```
1. drug_requirements_merged: Merged Remicade requirements from 1 sources → Used most recent source: CGN-SRC-001
```

### Submission Methods

```
1. collect_values: Collected 3 values from sources → Sources: ['CGN-SRC-001', 'CGN-SRC-002', 'CGN-SRC-003']
2. recency_boost: Source is 21 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. warning_penalty: Operational warnings detected → Penalty: -0.30
5. final_confidence: Final confidence calculation → Score: 0.70
```

### Turnaround Standard Days

```
1. collect_values: Collected 3 values from sources → Sources: ['CGN-SRC-001', 'CGN-SRC-002', 'CGN-SRC-003']
2. recency_boost: Source is 682 days old → Boost: +0.00
3. authority_boost: Source type: provider_manual → Boost: +0.10
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.10
5. final_confidence: Final confidence calculation → Score: 0.70
```

### Turnaround Urgent Hours

```
1. collect_values: Collected 3 values from sources → Sources: ['CGN-SRC-001', 'CGN-SRC-002', 'CGN-SRC-003']
2. recency_boost: Source is 21 days old → Boost: +0.30
3. authority_boost: Source type: phone_transcript → Boost: +0.20
4. agreement_bonus: Multiple sources agree on this value → Bonus: +0.20
5. warning_penalty: Operational warnings detected → Penalty: -0.30
6. final_confidence: Final confidence calculation → Score: 0.90
```
