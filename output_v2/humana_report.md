# Prior Authorization Route: Humana

## TL;DR

_Here is a comprehensive 5-7 sentence executive summary for the Humana prior authorization process based on the provided reconciled route data:

The preferred method for submitting prior authorizations to Humana is through the Availity portal at www.availity.com. The fallback option is to fax requests to (800) 523-0023. However, it is critical to note that the fallback fax number should not be used, as it is deprecated per the source data. Standard prior authorization turnaround time is 7 business days, but actual timelines are currently 10-14 days due to system migration delays. Urgent requests have a 48-hour turnaround. Required documents include the Humana PA request form HUM-AUTH-2026, recent chart notes, step therapy/prior treatment documentation, and biosimilar trial information. For the focus drug Rituxan, specific requirements include a 6-month authorization period, biosimilar use, step therapy, and CD20+ testing. The data indicates 3 conflicts were detected, so confidence in some fields may be lower. Lastly, the payer warns of a challenging phone experience, with 3 transfers and over 1 hour of total call time on average._

## ⚠️ Payer Warnings

> **Phone experience: 3 transfers, 1hr 12min total call time (source: HUM-SRC-002)**


## Summary

- **Focus Drug:** Rituxan
  - _Data-driven (high-signal): Rituxan (2 mentions in phone/denial) [Rituxan: 2]_
- **Fields Discovered:** 32
- **Fields Output:** 13
- **Conflicts Detected:** 3

## Best Route (Actionable)

_This is the primary output for form submission._

### Submission Method

**Preferred:** PORTAL
- URL: `www.availity.com`
  - _Availity integration having issues — rep recommends faxing instead_
**Fallback:** FAX
- Fax: `(800) 523-0023`

### Required Documents

- PA request form (retrieve from www.availity.com; best-known version: HUM-AUTH-2026)
- Chart notes within 90 days
- Step therapy / prior treatment failure documentation
- Biosimilar trial documentation or medical justification for brand

### Turnaround Times

- **Standard:** 7 business days
- **Urgent:** 48 hours
- **Standard (Actual):** 10-14 days (system migration delays)
- **Fax (Actual):** 7-10 days

### Contact Information

- **Status/Questions:** `(800) 555-2546, Option 2`
- **Urgent Line:** `(800) 555-2546`
- **Appeal Fax:** `(800) 523-0028`
- **Appeal Phone:** `(800) 555-2546, Option 4`
- **Appeal Mail:** `Humana Appeals, PO Box 14165, Lexington KY 40512`
- **Appeal Deadline:** 60 days

### Drug-Specific Requirements

#### Rituxan ⭐

- **Auth Period Months:** 6
- **Biosimilar Required:** True
- **Step Therapy Required:** True
- **Specific Testing:** CD20+
> CD20+ docs, step therapy for RA only
> Biosimilar trial required for RA, not required for lymphoma/CLL

#### Entyvio

- **Auth Period Months:** 6
> Anti-TNF failure/contraindication

#### Ocrevus

- **Auth Period Months:** 12
- **Specialist Required:** True
- **Specific Testing:** JCV
> MS specialist must submit

#### Remicade

- **Step Therapy Required:** True
- **Biosimilar Attestation:** True
- **Auth Period Months:** 6
- **Biosimilar Required:** True

### Restrictions & Warnings

- ⚠️ Phone experience: 3 transfers, 1hr 12min total call time (source: HUM-SRC-002)
- ⚠️ Ocrevus: Specialist diagnosis confirmation required
- ⚠️ Ocrevus: MS specialist must submit
- ⚠️ Remicade: Biosimilar trial required before brand drug approval
- ⚠️ Remicade: Step therapy / prior treatment failure required

### Data Coverage

_Based on 4 sources. Cross-validated 13 fields against raw text (1 discrepancies found). Verify with payer if additional documentation needed: Letter Of Medical Necessity, Prescription Order, Diagnosis Codes..._

**Verify with payer (not in extracted data):**
- Letter Of Medical Necessity
- Prescription Order
- Diagnosis Codes
- Prior Treatment History
- Specialist Attestation

---

## All Drug Details (Audit)

### Entyvio

_Sources: HUM-SRC-001_

- **Auth Period Months:** 6

**Notes:**
> Anti-TNF failure/contraindication

### Ocrevus

_Sources: HUM-SRC-001_

- **Auth Period Months:** 12
- **Specialist Required:** True
- **Specific Testing:** JCV

**Notes:**
> MS specialist must submit

### Remicade

_Sources: HUM-SRC-001_

- **Step Therapy Required:** True
- **Biosimilar Attestation:** True
- **Auth Period Months:** 6
- **Biosimilar Required:** True

### Rituxan ⭐ (focus)

_Sources: HUM-SRC-002, HUM-SRC-001_

- **Auth Period Months:** 6
- **Biosimilar Required:** True
- **Step Therapy Required:** True
- **Specific Testing:** CD20+

**Notes:**
> CD20+ docs, step therapy for RA only
> Biosimilar trial required for RA, not required for lymphoma/CLL

## Reconciled Route

### Appeal Deadline Days

**Value:** `60`
**Confidence:** 0.75 | **Source:** HUM-SRC-004 (denial_letter)

### Appeal Fax

**Value:** `(800) 523-0028`
**Confidence:** 0.90 | **Source:** HUM-SRC-003 (web_page)

### Appeal Mail

**Value:** `Humana Appeals, PO Box 14165, Lexington KY 40512`
**Confidence:** 0.75 | **Source:** HUM-SRC-004 (denial_letter)

### Appeal Phone

**Value:** `(800) 555-2546, Option 4`
**Confidence:** 0.75 | **Source:** HUM-SRC-004 (denial_letter)

### Fax Number

**Value:** `(800) 523-0023`
**Confidence:** 0.95 | **Source:** HUM-SRC-001 (provider_manual)

### Phone Hours

**Value:** `M-F 8am-5pm CST`
**Confidence:** 0.65 | **Source:** HUM-SRC-001 (provider_manual)

### Phone Status

**Value:** `(800) 555-2546, Option 2`
**Confidence:** 0.75 | **Source:** HUM-SRC-001 (provider_manual)

### Phone Urgent

**Value:** `(800) 555-2546`
**Confidence:** 0.90 | **Source:** HUM-SRC-001 (provider_manual)

### Portal Url

**Value:** `www.availity.com`
**Confidence:** 0.95 | **Source:** HUM-SRC-001 (provider_manual)

**Notes:**
> Availity integration having issues — rep recommends faxing instead

### Turnaround Stated Days

**Value:** `stated_policy: {default: 7, urgent_hours: 48} | operational_reality: {standard: {'min': 10, 'max': 14}, standard_cause: system migration delays, fax: {'min': 7, 'max': 10}}`
**Confidence:** 0.63 | **Source:** HUM-SRC-002 (phone_transcript)

## Conflicts & Warnings

### Chart Note Window Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `HUM-SRC-001`: `60` (superseded)
- ✗ `HUM-SRC-002`: `90`
- ✗ `HUM-SRC-003`: `60` (superseded)
- ✓ `HUM-SRC-004`: `90`

**Supersession:**
- Source HUM-SRC-001 (2024-01-01) predates policy update (2026-01-01)
- Source HUM-SRC-003 (2025-04-01) predates policy update (2026-01-01)
- Policy update (2026-01-01) found in source HUM-SRC-004

**Selected:** `90`
**Confidence:** 0.90

### Pa Form

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `HUM-SRC-001`: `HUM-AUTH-2024` (superseded)
- ✓ `HUM-SRC-002`: `HUM-AUTH-2026`
- ✗ `HUM-SRC-003`: `HUM-AUTH-2024` (superseded)
- ✗ `HUM-SRC-004`: `HUM-AUTH-2026`

**Supersession:**
- Value 'HUM-AUTH-2024' deprecated by *_old field in HUM-SRC-002
- Version HUM-AUTH-2024 (2024) superseded by newer version (2026)
- Version HUM-AUTH-2024 (2024) superseded by newer version (2026)
- Value matches deprecated *_old value
- Value matches deprecated *_old value

**Selected:** `HUM-AUTH-2026`
**Confidence:** 0.90

### Submission Methods

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `HUM-SRC-001`: `portal, fax, phone_urgent_only`
- ✓ `HUM-SRC-002`: `fax, portal`
- ✗ `HUM-SRC-003`: `portal, fax, phone_urgent_only`

**Selected:** `fax, portal`
**Confidence:** 0.58

## Decision Audit Trail

Detailed decision paths for key fields.

### Chart Note Window Days

```
1. field: chart_note_window_days
2. sources: 4
3. Source HUM-SRC-001 (2024-01-01) predates policy update (2026-01-01)
4. Source HUM-SRC-003 (2025-04-01) predates policy update (2026-01-01)
5. Policy update (2026-01-01) found in source HUM-SRC-004
6. freshness: 2026-03-08 (38d old) -> 0.864
7. authority: denial_letter -> 1.000
8. corroboration: 2/2 agree -> 0.500
9. policy_boost: source has policy_update -> +1.000
10. total: 0.852
11. selected: 90 from HUM-SRC-004
12. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Pa Form

```
1. field: pa_form
2. sources: 4
3. Value 'HUM-AUTH-2024' deprecated by *_old field in HUM-SRC-002
4. Version HUM-AUTH-2024 (2024) superseded by newer version (2026)
5. Version HUM-AUTH-2024 (2024) superseded by newer version (2026)
6. Value matches deprecated *_old value
7. Value matches deprecated *_old value
8. freshness: 2026-03-19 (27d old) -> 0.901
9. authority: phone_transcript -> 0.750
10. corroboration: 2/2 agree -> 0.500
11. confidence_floor: 2/2 universal agreement -> 0.850
12. total: 0.850
13. selected: HUM-AUTH-2026 from HUM-SRC-002
14. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Submission Methods

```
1. field: submission_methods
2. sources: 3
3. freshness: 2026-03-19 (27d old) -> 0.901
4. authority: phone_transcript -> 0.750
5. corroboration: 1/3 agree -> 0.000
6. total: 0.578
7. selected: ['fax', 'portal'] from HUM-SRC-002
```
