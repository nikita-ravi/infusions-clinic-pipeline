# Prior Authorization Route: UnitedHealthcare

## TL;DR

_Here is a 5-7 sentence executive summary for the UnitedHealthcare prior authorization process:

The preferred submission method for UnitedHealthcare prior authorizations is through the online portal at www.uhcprovider.com. However, fax submissions can be used as a fallback option to the dedicated fax number of (800) 699-4702. Standard turnaround time is 5 business days for portal submissions and 5-7 business days for fax. For urgent requests, a 24-hour turnaround is available by calling (800) 331-6689. Key required documents include the PA request form (UHC-PA-200), chart notes within 90 days, step therapy/prior treatment failure documentation, and biosimilar trial info. Drug-specific requirements vary, with Remicade needing step therapy, biosimilar preference, and weight-based dosing documentation. The data had 5 conflicting fields, so some information may not be fully reliable._

## Summary

- **Focus Drug:** Remicade
  - _Data-driven (high-signal): Remicade (2 mentions in phone/denial) [Remicade: 2]_
- **Fields Discovered:** 35
- **Fields Output:** 12
- **Conflicts Detected:** 5

## Best Route (Actionable)

_This is the primary output for form submission._

### Submission Method

**Preferred:** PORTAL
- URL: `www.uhcprovider.com`
**Fallback:** FAX
- Fax: `(800) 699-4702`
  - _4702 is specialty team, faster for infusion drugs. 4711 is general medical PA._

### Required Documents

- PA request form (retrieve from www.uhcprovider.com; best-known version: UHC-PA-200)
- Chart notes within 90 days
- Step therapy / prior treatment failure documentation
- Biosimilar trial documentation or medical justification for brand

### Turnaround Times

- **Standard:** 5 business days
- **Fax:** 5-7 business days
- **Urgent:** 24 hours

### Contact Information

- **Urgent Line:** `(800) 331-6689`
- **Appeal Fax:** `(800) 699-4800`
- **Appeal Phone:** `(800) 331-6689`
- **Appeal Deadline:** 60 days

### Drug-Specific Requirements

#### Remicade ⭐

- **Step Therapy Required:** True
- **Biosimilar Preferred:** True
- **Auth Period Months:** 6
- **Biosimilar Required:** True
- **Auth Period Renewal Months:** 12
- **Auth Period Initial Months:** 6
- **Prior Treatment Failure Required:** True
- **Documentation Requirements:** Weight-based dosing documentation required
> #1 denial reason is missing biosimilar trial/justification
> Weight-based dosing docs required

#### Herceptin

- **Biosimilar Required:** True
- **Auth Period Months:** 6

#### Keytruda

- **Auth Period Months:** 3
- **Biomarker Testing Required:** True
- **Documentation Requirements:** Staging documentation
> Biomarker testing
> Biomarker testing required

#### Ocrevus

- **Auth Period Months:** 12
- **Specialist Required:** True
- **Documentation Requirements:** MRI within 12 months
> Neurologist must submit, MRI within 12 months

#### Rituxan

- **Biosimilar Required:** True
- **Auth Period Months:** 6

### Restrictions & Warnings

- ⚠️ Herceptin: Biosimilar trial required before brand drug approval
- ⚠️ Keytruda: Biomarker testing required
- ⚠️ Ocrevus: Specialist diagnosis confirmation required
- ⚠️ Ocrevus: Neurologist must submit, MRI within 12 months
- ⚠️ Remicade: Step therapy / prior treatment failure required
- ⚠️ Remicade: Weight-based dosing docs required

### Data Coverage

_Based on 4 sources. Cross-validated 11 fields against raw text (1 discrepancies found). Verify with payer if additional documentation needed: Letter Of Medical Necessity, Prescription Order, Diagnosis Codes..._

**Verify with payer (not in extracted data):**
- Letter Of Medical Necessity
- Prescription Order
- Diagnosis Codes
- Prior Treatment History
- Specialist Attestation

---

## All Drug Details (Audit)

### Herceptin

_Sources: UHC-SRC-003_

- **Biosimilar Required:** True
- **Auth Period Months:** 6

### Keytruda

_Sources: UHC-SRC-003, UHC-SRC-001_

- **Auth Period Months:** 3
- **Biomarker Testing Required:** True
- **Documentation Requirements:** Staging documentation

**Notes:**
> Biomarker testing
> Biomarker testing required

### Ocrevus

_Sources: UHC-SRC-003, UHC-SRC-001_

- **Auth Period Months:** 12
- **Specialist Required:** True
- **Documentation Requirements:** MRI within 12 months

**Notes:**
> Neurologist must submit, MRI within 12 months

### Remicade ⭐ (focus)

_Sources: UHC-SRC-003, UHC-SRC-002, UHC-SRC-001_

- **Step Therapy Required:** True
- **Biosimilar Preferred:** True
- **Auth Period Months:** 6
- **Biosimilar Required:** True
- **Auth Period Renewal Months:** 12
- **Auth Period Initial Months:** 6
- **Prior Treatment Failure Required:** True
- **Documentation Requirements:** Weight-based dosing documentation required

**Notes:**
> #1 denial reason is missing biosimilar trial/justification
> Weight-based dosing docs required

### Rituxan

_Sources: UHC-SRC-003_

- **Biosimilar Required:** True
- **Auth Period Months:** 6

## Reconciled Route

### Appeal Deadline Days

**Value:** `60`
**Confidence:** 0.75 | **Source:** UHC-SRC-004 (denial_letter)

### Appeal Fax

**Value:** `(800) 699-4800`
**Confidence:** 0.75 | **Source:** UHC-SRC-004 (denial_letter)

### Appeal Phone

**Value:** `(800) 331-6689`
**Confidence:** 0.75 | **Source:** UHC-SRC-004 (denial_letter)

### Pend Period Days

**Value:** `14`
**Confidence:** 0.75 | **Source:** UHC-SRC-001 (provider_manual)

### Phone Hours

**Value:** `M-F 8am-6pm EST`
**Confidence:** 0.65 | **Source:** UHC-SRC-001 (provider_manual)

### Phone Urgent

**Value:** `(800) 331-6689`
**Confidence:** 0.90 | **Source:** UHC-SRC-001 (provider_manual)

### Portal Url

**Value:** `www.uhcprovider.com`
**Confidence:** 0.95 | **Source:** UHC-SRC-001 (provider_manual)

## Conflicts & Warnings

### Chart Note Window Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `UHC-SRC-001`: `60` (superseded)
- ✗ `UHC-SRC-002`: `60`
- ✗ `UHC-SRC-003`: `90`
- ✓ `UHC-SRC-004`: `90`

**Supersession:**
- Source UHC-SRC-001 (2024-12-01) predates policy update (2026-03-01)
- Policy update (2026-03-01) found in source UHC-SRC-003

**Selected:** `90`
**Confidence:** 0.80

### Fax Number

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `UHC-SRC-001`: `(800) 699-4711`
- ✓ `UHC-SRC-002`: `(800) 699-4702`

**Selected:** `default: (800) 699-4702 | recommended: (800) 699-4702 | specialty: (800) 699-4702 | general: (800) 699-4711`
**Confidence:** 0.63

### Pa Form

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `UHC-SRC-001`: `UHC-PA-100` (superseded)
- ✓ `UHC-SRC-002`: `UHC-PA-200`
- ✗ `UHC-SRC-003`: `UHC-PA-200`
- ✗ `UHC-SRC-004`: `UHC-PA-200`

**Supersession:**
- Value 'UHC-PA-100' deprecated by *_old field in UHC-SRC-002
- Value matches deprecated *_old value

**Selected:** `UHC-PA-200`
**Confidence:** 0.95

### Submission Methods

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `UHC-SRC-001`: `portal, fax, phone_urgent_only`
- ✓ `UHC-SRC-002`: `portal, fax`
- ✗ `UHC-SRC-003`: `portal, fax, phone_urgent_only`

**Selected:** `portal, fax`
**Confidence:** 0.58

### Turnaround

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `turnaround_urgent`: `24`
- ✗ `turnaround_standard`: `5`
- ✗ `turnaround_fax`: `5-7`

**Selected:** `urgent: 24 | standard: 5 | fax: {min: 5, max: 7}`
**Confidence:** 0.71

## Decision Audit Trail

Detailed decision paths for key fields.

### Chart Note Window Days

```
1. field: chart_note_window_days
2. sources: 4
3. Source UHC-SRC-001 (2024-12-01) predates policy update (2026-03-01)
4. Policy update (2026-03-01) found in source UHC-SRC-003
5. freshness: 2026-03-05 (41d old) -> 0.854
6. authority: denial_letter -> 1.000
7. corroboration: 2/3 agree -> 0.500
8. total: 0.749
9. selected: 90 from UHC-SRC-004
10. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Fax Number

```
1. field: fax_number
2. sources: 2
3. freshness: 2026-03-18 (28d old) -> 0.898
4. authority: phone_transcript -> 0.750
5. corroboration: 1/2 agree -> 0.000
6. total: 0.577
7. selected: (800) 699-4702 from UHC-SRC-002
8. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Pa Form

```
1. field: pa_form
2. sources: 4
3. Value 'UHC-PA-100' deprecated by *_old field in UHC-SRC-002
4. Value matches deprecated *_old value
5. freshness: 2026-03-18 (28d old) -> 0.898
6. authority: phone_transcript -> 0.750
7. corroboration: 3/3 agree -> 0.750
8. confidence_floor: 3/3 universal agreement -> 0.925
9. total: 0.925
10. selected: UHC-PA-200 from UHC-SRC-002
11. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Submission Methods

```
1. field: submission_methods
2. sources: 3
3. freshness: 2026-03-18 (28d old) -> 0.898
4. authority: phone_transcript -> 0.750
5. corroboration: 1/3 agree -> 0.000
6. total: 0.577
7. selected: ['portal', 'fax'] from UHC-SRC-002
```

### Turnaround

```
1. field: turnaround
2. qualifier_only_family: no base field, 3 qualifiers
3. urgent stated_policy: 24 (conf: 0.92)
4. standard stated_policy: 5 (conf: 0.73)
5. fax stated_policy: 5-7 (conf: 0.47)
6. overall_confidence: avg of 3 components -> 0.707 (range: 0.47-0.92)
7. output: {'urgent': 24, 'standard': 5, 'fax': {'min': 5, 'max': 7}}
```
