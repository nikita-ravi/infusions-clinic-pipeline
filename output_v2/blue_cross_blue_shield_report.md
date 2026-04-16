# Prior Authorization Route: Anthem Blue Cross Blue Shield

## TL;DR

_Here is a comprehensive executive summary for the Anthem Blue Cross Blue Shield prior authorization route data:

The preferred method for submitting prior authorizations to Anthem Blue Cross Blue Shield is through their online provider portal at www.anthem.com/providers. The fallback option is to fax requests to (844) 405-0296. It's critical to avoid using any deprecated fax numbers, as those will likely result in delays or rejections. 

Standard turnaround time for prior authorization decisions is 5 business days, while urgent requests are processed within 24 hours. Key required documents include the PA request form (best known version is ANT-MED-PA-25), chart notes within 90 days, lab results, and documentation of step therapy or prior treatment failure.

For the focus drug Herceptin, HER2 testing is required, and there is a high denial rate for missing biosimilar justification. Keytruda requires biomarker documentation, while Ocrevus needs to be submitted by a neurologist and include an MRI within the past 12 months. Remicade requires a biosimilar trial and step therapy documentation before the brand-name drug can be approved.

Please note that there were two conflicting data points identified in the source material, which may affect the confidence in some of the details provided. Be sure to double-check any critical information before submitting prior authorizations._

## Summary

- **Focus Drug:** Herceptin
  - _Data-driven (high-signal): Herceptin (2 mentions in phone/denial) [Herceptin: 2]_
- **Fields Discovered:** 23
- **Fields Output:** 12
- **Conflicts Detected:** 2

## Best Route (Actionable)

_This is the primary output for form submission._

### Submission Method

**Preferred:** PORTAL
- URL: `www.anthem.com/providers`
**Fallback:** FAX
- Fax: `(844) 405-0296`

### Required Documents

- PA request form (retrieve from www.anthem.com/providers; best-known version: ANT-MED-PA-25)
- Chart notes within 90 days
- Lab results (common denial reason when missing)
- Step therapy / prior treatment failure documentation
- Biosimilar trial documentation or medical justification for brand

### Turnaround Times

- **Standard:** 5 business days
- **Urgent:** 24 hours

### Contact Information

- **Urgent Line:** `(800) 274-7767`
- **Appeal Fax:** `(844) 405-0299`
- **Appeal Phone:** `(800) 274-7767, Option 5`
- **Appeal Deadline:** 180 days

### Drug-Specific Requirements

#### Herceptin ⭐

- **Biosimilar Preferred:** True
- **Preferred Biosimilars:** Ogivri, Herzuma
- **Specific Testing:** HER2
> HER2 testing required
> High denial rate for missing biosimilar justification

#### Keytruda

- **Documentation Requirements:** Biomarker documentation
> Biomarker documentation, oncology treatment plan

#### Ocrevus

- **Specialist Required:** True
- **Documentation Requirements:** MRI within 12 months
> Neurologist must submit, MRI within 12 months

#### Remicade

- **Biosimilar Preferred:** True
- **Step Therapy Required:** True
- **Biosimilar Required:** True

### Restrictions & Warnings

- ⚠️ Herceptin: HER2 testing required
- ⚠️ Ocrevus: Specialist diagnosis confirmation required
- ⚠️ Ocrevus: Neurologist must submit, MRI within 12 months
- ⚠️ Remicade: Biosimilar trial required before brand drug approval
- ⚠️ Remicade: Step therapy / prior treatment failure required
- ⚠️ Common denial: Outdated Chart Notes (22%)
- ⚠️ Common denial: Incomplete Form (18%)

### Data Coverage

_Based on 4 sources. Cross-validated 11 fields against raw text (all matched). Verify with payer if additional documentation needed: Letter Of Medical Necessity, Prescription Order, Diagnosis Codes..._

**Verify with payer (not in extracted data):**
- Letter Of Medical Necessity
- Prescription Order
- Diagnosis Codes
- Prior Treatment History
- Specialist Attestation

---

## All Drug Details (Audit)

### Herceptin ⭐ (focus)

_Sources: BCB-SRC-002, BCB-SRC-001_

- **Biosimilar Preferred:** True
- **Preferred Biosimilars:** Ogivri, Herzuma
- **Specific Testing:** HER2

**Notes:**
> HER2 testing required
> High denial rate for missing biosimilar justification

### Keytruda

_Sources: BCB-SRC-001_

- **Documentation Requirements:** Biomarker documentation

**Notes:**
> Biomarker documentation, oncology treatment plan

### Ocrevus

_Sources: BCB-SRC-001_

- **Specialist Required:** True
- **Documentation Requirements:** MRI within 12 months

**Notes:**
> Neurologist must submit, MRI within 12 months

### Remicade

_Sources: BCB-SRC-001_

- **Biosimilar Preferred:** True
- **Step Therapy Required:** True
- **Biosimilar Required:** True

## Reconciled Route

### Appeal Deadline Days

**Value:** `180`
**Confidence:** 0.75 | **Source:** BCB-SRC-004 (denial_letter)

### Appeal Fax

**Value:** `(844) 405-0299`
**Confidence:** 0.75 | **Source:** BCB-SRC-004 (denial_letter)

### Appeal Phone

**Value:** `(800) 274-7767, Option 5`
**Confidence:** 0.75 | **Source:** BCB-SRC-004 (denial_letter)

### Coverage States

**Value:** `CA, NY, OH, GA, IN, VA`
**Confidence:** 0.70 | **Source:** BCB-SRC-001 (provider_manual)

### Fax Number

**Value:** `(844) 405-0296`
**Confidence:** 0.95 | **Source:** BCB-SRC-001 (provider_manual)

### Pa Form

**Value:** `ANT-MED-PA-25`
**Confidence:** 0.95 | **Source:** BCB-SRC-001 (provider_manual)

### Phone Urgent

**Value:** `(800) 274-7767`
**Confidence:** 0.90 | **Source:** BCB-SRC-001 (provider_manual)

### Portal Url

**Value:** `www.anthem.com/providers`
**Confidence:** 0.95 | **Source:** BCB-SRC-001 (provider_manual)

### Submission Methods

**Value:** `portal, fax, phone_urgent_only`
**Confidence:** 0.85 | **Source:** BCB-SRC-001 (provider_manual)

## Conflicts & Warnings

### Chart Note Window Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `BCB-SRC-001`: `60` (superseded)
- ✗ `BCB-SRC-002`: `60`
- ✗ `BCB-SRC-003`: `90`
- ✓ `BCB-SRC-004`: `90`

**Supersession:**
- Source BCB-SRC-001 (2025-01-01) predates policy update (2025-11-01)
- Policy update (2025-11-01) found in source BCB-SRC-003

**Selected:** `90`
**Confidence:** 0.81

### Common Denial Reasons

**Selected:** `missing_biosimilar_justification: 38% | outdated_chart_notes: 22% | incomplete_form: 18% | missing_labs: 12%`
**Confidence:** 0.36

### Turnaround

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `turnaround_urgent`: `24`
- ✗ `turnaround_standard`: `5`

**Selected:** `urgent: 24 | standard: 5`
**Confidence:** 0.89

## Decision Audit Trail

Detailed decision paths for key fields.

### Chart Note Window Days

```
1. field: chart_note_window_days
2. sources: 4
3. Source BCB-SRC-001 (2025-01-01) predates policy update (2025-11-01)
4. Policy update (2025-11-01) found in source BCB-SRC-003
5. freshness: 2026-03-18 (28d old) -> 0.898
6. authority: denial_letter -> 1.000
7. corroboration: 2/3 agree -> 0.500
8. total: 0.764
9. selected: 90 from BCB-SRC-004
10. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Turnaround

```
1. field: turnaround
2. qualifier_only_family: no base field, 2 qualifiers
3. urgent stated_policy: 24 (conf: 0.85)
4. standard stated_policy: 5 (conf: 0.92)
5. overall_confidence: avg of 2 components -> 0.887 (range: 0.85-0.92)
6. output: {'urgent': 24, 'standard': 5}
```
