# Prior Authorization Route: Aetna

## TL;DR

_Here is a 5-7 sentence executive summary for the Aetna prior authorization route data:

The preferred submission method for Aetna prior authorizations is through the Availity portal at www.availity.com. However, fax can be used as a fallback option to the number (888) 267-3300. Critically, the previous fax number (888) 267-3277 has been decommissioned and should not be used. Turnaround times range from 3-5 business days for portal submissions, 5 business days for standard requests, and 24 hours for urgent requests. Required documents include the AET-PA-2025 PA request form, chart notes/lab results within 90 days, a letter of medical necessity, and step therapy/prior treatment failure documentation. For the focus drug Remicade, step therapy, specialist diagnosis, and prior treatment failure are required, with an initial 6-month authorization period. The data quality report notes 4 conflicting fields, so some uncertainty exists around the accuracy of the information provided. Medical office staff should be aware of these guidelines when submitting Aetna prior authorizations._

## Summary

- **Focus Drug:** Remicade
  - _Data-driven (high-signal): Remicade (2 mentions in phone/denial) [Remicade: 2]_
- **Fields Discovered:** 28
- **Fields Output:** 10
- **Conflicts Detected:** 4

## Best Route (Actionable)

_This is the primary output for form submission._

### Submission Method

**Preferred:** PORTAL
- URL: `www.availity.com`
  - _Preferred — faster than fax_
**Fallback:** FAX
- Fax: `(888) 267-3300`
**Do NOT Use:**
- ~~(888) 267-3277 (Decommissioned February 1, 2026)~~

### Required Documents

- PA request form (retrieve from www.availity.com; best-known version: AET-PA-2025)
- Chart notes within 90 days
- Lab results within 90 days
- Letter of medical necessity
- Step therapy / prior treatment failure documentation

### Turnaround Times

- **Portal:** 3-5 business days
- **Standard:** 5 business days
- **Fax:** 7-10 days (during transition)
- **Urgent:** 24 hours

### Contact Information

- **Status/Questions:** `(800) 624-0756, Option 3, Option 1`
- **Appeal Fax:** `(888) 267-3350`
- **Appeal Deadline:** 60 days

### Drug-Specific Requirements

#### Remicade ⭐

- **Step Therapy Required:** True
- **Auth Period Months:** 6
- **Auth Period Renewal Months:** 12
- **Auth Period Initial Months:** 6
- **Specialist Required:** True
- **Prior Treatment Failure Required:** True
- **Turnaround Standard Days:** 5
- **Turnaround Urgent Hours:** 24
> Step therapy docs required
> Specialist diagnosis, conventional therapy failure

#### Entyvio

- **Step Therapy Required:** True
- **Auth Period Months:** 6
- **Prior Treatment Failure Required:** True

#### Keytruda

- **Step Therapy Required:** False
- **Auth Period Months:** 3
- **Auth Period Renewal Months:** 6
- **Auth Period Initial Months:** 3
- **Specialist Required:** True
- **Specific Testing:** PD-L1
- **Documentation Requirements:** Oncologist letter of medical necessity
- **Turnaround Standard Days:** 5
- **Turnaround Urgent Hours:** 24
> PD-L1 testing required
> PD-L1 testing required, oncologist LMN

#### Rituxan

- **Step Therapy Required:** False
- **Auth Period Months:** 6
- **Auth Period Renewal Months:** 12
- **Auth Period Initial Months:** 6
- **Specific Testing:** CD20 positive
- **Documentation Requirements:** CD20+ documentation
> CD20 positive documentation
> CD20+ documentation

### Restrictions & Warnings

- ⚠️ Entyvio: Step therapy / prior treatment failure required
- ⚠️ Keytruda: Specialist diagnosis confirmation required
- ⚠️ Keytruda: PD-L1 testing required
- ⚠️ Keytruda: PD-L1 testing required, oncologist LMN
- ⚠️ Remicade: Specialist diagnosis confirmation required

### Data Coverage

_Based on 4 sources. Cross-validated 9 fields against raw text (all matched). Verify with payer if additional documentation needed: Letter Of Medical Necessity, Prescription Order, Diagnosis Codes..._

**Verify with payer (not in extracted data):**
- Letter Of Medical Necessity
- Prescription Order
- Diagnosis Codes
- Prior Treatment History
- Specialist Attestation

---

## All Drug Details (Audit)

### Entyvio

_Sources: AET-SRC-003_

- **Step Therapy Required:** True
- **Auth Period Months:** 6
- **Prior Treatment Failure Required:** True

### Keytruda

_Sources: AET-SRC-001, AET-SRC-003_

- **Step Therapy Required:** False
- **Auth Period Months:** 3
- **Auth Period Renewal Months:** 6
- **Auth Period Initial Months:** 3
- **Specialist Required:** True
- **Specific Testing:** PD-L1
- **Documentation Requirements:** Oncologist letter of medical necessity
- **Turnaround Standard Days:** 5
- **Turnaround Urgent Hours:** 24

**Notes:**
> PD-L1 testing required
> PD-L1 testing required, oncologist LMN

### Remicade ⭐ (focus)

_Sources: AET-SRC-001, AET-SRC-002_

- **Step Therapy Required:** True
- **Auth Period Months:** 6
- **Auth Period Renewal Months:** 12
- **Auth Period Initial Months:** 6
- **Specialist Required:** True
- **Prior Treatment Failure Required:** True
- **Turnaround Standard Days:** 5
- **Turnaround Urgent Hours:** 24

**Notes:**
> Step therapy docs required
> Specialist diagnosis, conventional therapy failure

### Rituxan

_Sources: AET-SRC-001, AET-SRC-003_

- **Step Therapy Required:** False
- **Auth Period Months:** 6
- **Auth Period Renewal Months:** 12
- **Auth Period Initial Months:** 6
- **Specific Testing:** CD20 positive
- **Documentation Requirements:** CD20+ documentation

**Notes:**
> CD20 positive documentation
> CD20+ documentation

## Reconciled Route

### Appeal Deadline Days

**Value:** `60`
**Confidence:** 0.75 | **Source:** AET-SRC-004 (denial_letter)

### Appeal Fax

**Value:** `(888) 267-3350`
**Confidence:** 0.75 | **Source:** AET-SRC-004 (denial_letter)

### Lab Window Days

**Value:** `90`
**Confidence:** 0.75 | **Source:** AET-SRC-001 (provider_manual)

### Phone Status Only

**Value:** `(800) 624-0756, Option 3, Option 1`
**Confidence:** 0.90 | **Source:** AET-SRC-001 (provider_manual)

### Portal Url

**Value:** `www.availity.com`
**Confidence:** 0.95 | **Source:** AET-SRC-001 (provider_manual)

**Notes:**
> Preferred — faster than fax

### Submission Methods

**Value:** `fax, portal`
**Confidence:** 0.92 | **Source:** AET-SRC-001 (provider_manual)

## Conflicts & Warnings

### Chart Note Window Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `AET-SRC-001`: `60`
- ✗ `AET-SRC-002`: `90`
- ✗ `AET-SRC-003`: `60`
- ✓ `AET-SRC-004`: `90`

**Selected:** `90`
**Confidence:** 0.90

### Fax Number

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `AET-SRC-001`: `(888) 267-3277` (superseded)
- ✓ `AET-SRC-002`: `(888) 267-3300`
- ✗ `AET-SRC-003`: `(888) 267-3277` (superseded)
- ✗ `AET-SRC-004`: `(888) 267-3300`

**Supersession:**
- Value '(888) 267-3277' deprecated by *_old field in AET-SRC-002
- Value '(888) 267-3277' deprecated by *_old field in AET-SRC-004
- Deprecation reason: Decommissioned February 1, 2026
- Deprecation reason: No longer active for infusion medication PAs as of Feb 2026
- Value matches deprecated *_old value
- Value matches deprecated *_old value

**Selected:** `(888) 267-3300`
**Confidence:** 0.90

### Pa Form

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✓ `AET-SRC-001`: `AET-PA-2025`
- ✗ `AET-SRC-003`: `AET-PA-2024` (superseded)

**Supersession:**
- Version AET-PA-2024 (2024) superseded by newer version (2025)

**Selected:** `AET-PA-2025`
**Confidence:** 0.80

### Turnaround

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `turnaround_urgent`: `24`
- ✗ `turnaround_standard`: `5`
- ✗ `turnaround_fax`: `7-10 (during transition)`
- ✗ `turnaround_portal`: `3-5`

**Selected:** `stated_policy: {urgent: 24, standard: 5, fax: {'min': 5, 'max': 7}, portal: {'min': 3, 'max': 5}} | operational_reality: {fax: {'min': 7, 'max': 10}, fax_cause: during transition}`
**Confidence:** 0.60

## Decision Audit Trail

Detailed decision paths for key fields.

### Chart Note Window Days

```
1. field: chart_note_window_days
2. sources: 4
3. freshness: 2026-03-10 (36d old) -> 0.871
4. authority: denial_letter -> 1.000
5. corroboration: 2/4 agree -> 0.500
6. policy_boost: source has policy_update -> +1.000
7. total: 0.855
8. selected: 90 from AET-SRC-004
9. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Fax Number

```
1. field: fax_number
2. sources: 4
3. Value '(888) 267-3277' deprecated by *_old field in AET-SRC-002
4. Value '(888) 267-3277' deprecated by *_old field in AET-SRC-004
5. Deprecation reason: Decommissioned February 1, 2026
6. Deprecation reason: No longer active for infusion medication PAs as of Feb 2026
7. Value matches deprecated *_old value
8. Value matches deprecated *_old value
9. freshness: 2026-03-22 (24d old) -> 0.912
10. authority: phone_transcript -> 0.750
11. corroboration: 2/2 agree -> 0.500
12. confidence_floor: 2/2 universal agreement -> 0.850
13. total: 0.850
14. selected: (888) 267-3300 from AET-SRC-002
15. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Pa Form

```
1. field: pa_form
2. sources: 2
3. Version AET-PA-2024 (2024) superseded by newer version (2025)
4. freshness: 2025-01-15 (455d old) -> 0.173
5. authority: provider_manual -> 0.500
6. corroboration: 1/1 agree -> 0.000
7. confidence_floor: uncontested after supersession -> 0.750
8. total: 0.750
9. selected: AET-PA-2025 from AET-SRC-001
10. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Turnaround

```
1. field: turnaround
2. qualifier_only_family: no base field, 4 qualifiers
3. urgent stated_policy: 24 (conf: 0.85)
4. standard stated_policy: 5 (conf: 0.85)
5. fax stated_policy: 5-7 (conf: 0.22)
6. fax operational_reality: 7-10 (during transition) (conf: 0.88)
7. portal stated_policy: 3-5 (conf: 0.22)
8. overall_confidence: avg of 5 components -> 0.602 (range: 0.22-0.88)
9. output: {'stated_policy': {'urgent': 24, 'standard': 5, 'fax': {'min': 5, 'max': 7}, 'portal': {'min': 3, 'max': 5}}, 'operational_reality': {'fax': {'min': 7, 'max': 10}, 'fax_cause': 'during transition'}}
```
