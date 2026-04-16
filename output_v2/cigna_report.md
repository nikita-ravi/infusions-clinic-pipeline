# Prior Authorization Route: Cigna

## TL;DR

_Here is a 5-7 sentence executive summary for the reconciled Cigna prior authorization route data:

The preferred submission method for Cigna prior authorizations is through their provider portal at www.cignaforhcp.com. As a fallback, faxes can be sent to (800) 768-4700, but the deprecated number (800) 768-4695 must not be used. Standard turnaround time is 10-12 days due to a system migration, while urgent requests are processed within 24 hours. Required documents include the PA request form (CG-PA-002), chart notes, step therapy/prior treatment failure documentation, and optional biosimilar consideration. For the focus drug Entyvio, prior anti-TNF failure or contraindication is required, along with the standard documentation. Critically, Cigna is currently undergoing a system migration, which is expected to cause processing delays and potential portal issues. The data analysis revealed 5 conflicting fields, so some information may be uncertain._

## ⚠️ Payer Warnings

> **SYSTEM MIGRATION IN PROGRESS (source: CGN-SRC-002). Expect processing delays and potential portal issues.**


## Summary

- **Focus Drug:** Entyvio
  - _Data-driven (high-signal): Entyvio (2 mentions in phone/denial) [Entyvio: 2]_
- **Fields Discovered:** 27
- **Fields Output:** 10
- **Conflicts Detected:** 5

## Best Route (Actionable)

_This is the primary output for form submission._

### Submission Method

**Preferred:** PORTAL
- URL: `www.cignaforhcp.com`
  - _Portal is glitchy during system migration — fax as backup_
  - _System migration notice on page_
**Fallback:** FAX
- Fax: `(800) 768-4700`
  - _4700 is new dedicated infusion line since Jan 2026. 4695 still works but goes to general queue (slower)._
**Do NOT Use:**
- ~~(800) 768-4695~~

### Required Documents

- PA request form (retrieve from www.cignaforhcp.com; best-known version: CG-PA-002)
- Chart notes within 90 days
- Step therapy / prior treatment failure documentation
- Biosimilar consideration documentation (preferred but not required)

### Turnaround Times

- **Standard:** 10-12 days (system migration delays)
- **Urgent:** 24 hours

### Contact Information

- **General Phone:** `(800) 768-4688`
- **Appeal Fax:** `(800) 768-4699`
- **Appeal Phone:** `(800) 768-4688, Option 4`

### Drug-Specific Requirements

#### Entyvio ⭐

- **Auth Period Months:** 6
- **Prior Treatment Failure Required:** True
- **Diagnosis Restrictions:** Crohn's or UC only
> Anti-TNF failure or contraindication required

#### Keytruda

- **Auth Period Months:** 3
- **Turnaround Standard Days:** 5

#### Remicade

- **Step Therapy Required:** True
- **Auth Period Months:** 6
- **Auth Period Renewal Months:** 12
- **Auth Period Initial Months:** 6
- **Biosimilar Preferred:** True
> Biosimilar preferred for new starts (2025)

#### Tysabri

- **Auth Period Months:** 12
- **Specific Testing:** JCV antibody
- **Documentation Requirements:** TOUCH Prescribing Program enrollment verification
> JCV antibody testing + TOUCH enrollment required

### Restrictions & Warnings

- ⚠️ SYSTEM MIGRATION IN PROGRESS (source: CGN-SRC-002). Expect processing delays and potential portal issues.
- ⚠️ Entyvio: Anti-TNF failure or contraindication required
- ⚠️ Remicade: Step therapy / prior treatment failure required
- ⚠️ Tysabri: JCV antibody testing + TOUCH enrollment required

### Data Coverage

_Based on 4 sources. Cross-validated 9 fields against raw text (1 discrepancies found). Verify with payer if additional documentation needed: Letter Of Medical Necessity, Prescription Order, Diagnosis Codes..._

**Verify with payer (not in extracted data):**
- Letter Of Medical Necessity
- Prescription Order
- Diagnosis Codes
- Prior Treatment History
- Specialist Attestation

---

## All Drug Details (Audit)

### Entyvio ⭐ (focus)

_Sources: CGN-SRC-001_

- **Auth Period Months:** 6
- **Prior Treatment Failure Required:** True
- **Diagnosis Restrictions:** Crohn's or UC only

**Notes:**
> Anti-TNF failure or contraindication required

### Keytruda

_Sources: CGN-SRC-001_

- **Auth Period Months:** 3
- **Turnaround Standard Days:** 5

### Remicade

_Sources: CGN-SRC-001_

- **Step Therapy Required:** True
- **Auth Period Months:** 6
- **Auth Period Renewal Months:** 12
- **Auth Period Initial Months:** 6
- **Biosimilar Preferred:** True

**Notes:**
> Biosimilar preferred for new starts (2025)

### Tysabri

_Sources: CGN-SRC-001_

- **Auth Period Months:** 12
- **Specific Testing:** JCV antibody
- **Documentation Requirements:** TOUCH Prescribing Program enrollment verification

**Notes:**
> JCV antibody testing + TOUCH enrollment required

## Reconciled Route

### Appeal Fax

**Value:** `(800) 768-4699`
**Confidence:** 0.75 | **Source:** CGN-SRC-004 (denial_letter)

### Appeal Phone

**Value:** `(800) 768-4688, Option 4`
**Confidence:** 0.75 | **Source:** CGN-SRC-004 (denial_letter)

### Phone

**Value:** `(800) 768-4688`
**Confidence:** 0.90 | **Source:** CGN-SRC-001 (provider_manual)

### Phone Hours

**Value:** `M-F 8am-8pm EST, Sat 9am-1pm EST`
**Confidence:** 0.65 | **Source:** CGN-SRC-001 (provider_manual)

### Portal Url

**Value:** `www.cignaforhcp.com`
**Confidence:** 0.95 | **Source:** CGN-SRC-001 (provider_manual)

**Notes:**
> Portal is glitchy during system migration — fax as backup
> System migration notice on page

## Conflicts & Warnings

### Chart Note Window Days

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `CGN-SRC-001`: `60` (superseded)
- ✗ `CGN-SRC-002`: `90`
- ✗ `CGN-SRC-003`: `60` (superseded)
- ✓ `CGN-SRC-004`: `90`

**Supersession:**
- Source CGN-SRC-001 (2024-06-01) predates policy update (2026-01-01)
- Source CGN-SRC-003 (2025-08-01) predates policy update (2026-01-01)
- Policy update (2026-01-01) found in source CGN-SRC-004

**Selected:** `90`
**Confidence:** 0.91

### Fax Number

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `CGN-SRC-001`: `(800) 768-4695` (superseded)
- ✓ `CGN-SRC-002`: `(800) 768-4700`
- ✗ `CGN-SRC-003`: `(800) 768-4695` (superseded)
- ✗ `CGN-SRC-004`: `(800) 768-4700`

**Supersession:**
- Value '(800) 768-4695' deprecated by *_old field in CGN-SRC-002
- Value '(800) 768-4695' deprecated by *_old field in CGN-SRC-004
- Value matches deprecated *_old value
- Value matches deprecated *_old value

**Selected:** `(800) 768-4700`
**Confidence:** 0.90

### Pa Form

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `CGN-SRC-001`: `CG-PA-001` (superseded)
- ✓ `CGN-SRC-002`: `CG-PA-002`
- ✗ `CGN-SRC-003`: `CG-PA-001` (superseded)
- ✗ `CGN-SRC-004`: `CG-PA-002`

**Supersession:**
- Value 'CG-PA-001' deprecated by *_old field in CGN-SRC-002
- Value matches deprecated *_old value
- Value matches deprecated *_old value

**Selected:** `CG-PA-002`
**Confidence:** 0.90

### Submission Methods

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `CGN-SRC-001`: `portal, fax, phone_urgent_only`
- ✓ `CGN-SRC-002`: `portal, fax`
- ✗ `CGN-SRC-003`: `portal, fax, phone`

**Selected:** `portal, fax`
**Confidence:** 0.58

### Turnaround

⚠️ **Conflict detected across sources**

**Conflicting values:**
- ✗ `turnaround_urgent`: `24`
- ✗ `turnaround_standard`: `7`

**Selected:** `stated_policy: {urgent: 24, standard: 7} | operational_reality: {standard: {'min': 10, 'max': 12}, standard_cause: system migration delays}`
**Confidence:** 0.89

## Decision Audit Trail

Detailed decision paths for key fields.

### Chart Note Window Days

```
1. field: chart_note_window_days
2. sources: 4
3. Source CGN-SRC-001 (2024-06-01) predates policy update (2026-01-01)
4. Source CGN-SRC-003 (2025-08-01) predates policy update (2026-01-01)
5. Policy update (2026-01-01) found in source CGN-SRC-004
6. freshness: 2026-03-15 (31d old) -> 0.887
7. authority: denial_letter -> 1.000
8. corroboration: 2/2 agree -> 0.500
9. policy_boost: source has policy_update -> +1.000
10. total: 0.861
11. selected: 90 from CGN-SRC-004
12. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Fax Number

```
1. field: fax_number
2. sources: 4
3. Value '(800) 768-4695' deprecated by *_old field in CGN-SRC-002
4. Value '(800) 768-4695' deprecated by *_old field in CGN-SRC-004
5. Value matches deprecated *_old value
6. Value matches deprecated *_old value
7. freshness: 2026-03-24 (22d old) -> 0.919
8. authority: phone_transcript -> 0.750
9. corroboration: 2/2 agree -> 0.500
10. confidence_floor: 2/2 universal agreement -> 0.850
11. total: 0.850
12. selected: (800) 768-4700 from CGN-SRC-002
13. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Pa Form

```
1. field: pa_form
2. sources: 4
3. Value 'CG-PA-001' deprecated by *_old field in CGN-SRC-002
4. Value matches deprecated *_old value
5. Value matches deprecated *_old value
6. freshness: 2026-03-24 (22d old) -> 0.919
7. authority: phone_transcript -> 0.750
8. corroboration: 2/2 agree -> 0.500
9. confidence_floor: 2/2 universal agreement -> 0.850
10. total: 0.850
11. selected: CG-PA-002 from CGN-SRC-002
12. raw_text_validation: Validated against raw text (adjustment: +0.05)
```

### Submission Methods

```
1. field: submission_methods
2. sources: 3
3. freshness: 2026-03-24 (22d old) -> 0.919
4. authority: phone_transcript -> 0.750
5. corroboration: 1/3 agree -> 0.000
6. total: 0.584
7. selected: ['portal', 'fax'] from CGN-SRC-002
```

### Turnaround

```
1. field: turnaround
2. qualifier_only_family: no base field, 2 qualifiers
3. urgent stated_policy: 24 (conf: 0.92)
4. standard stated_policy: 7 (conf: 0.85)
5. standard operational_reality: 10-12 (system migration delays) (conf: 0.88)
6. overall_confidence: avg of 3 components -> 0.886 (range: 0.85-0.92)
7. output: {'stated_policy': {'urgent': 24, 'standard': 7}, 'operational_reality': {'standard': {'min': 10, 'max': 12}, 'standard_cause': 'system migration delays'}}
```
