# PA Route Reconciliation — Conflict Report

Generated: 2026-04-23 04:48:42

This report shows where source documents disagreed and how conflicts were resolved.
Use this to understand why certain values were selected and what evidence supports them.

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total Payers Reconciled | 5 |
| Fields with Conflicts | 64 |
| Supersession Events | 21 |
| Extraction Errors Caught | 2 |

## High-Risk Conflicts (Denial Impact)

These conflicts involve fields that commonly cause PA denials if incorrect.

### Aetna

- **fax_number**: Old value `(888) 267-3277` superseded → `(888) 267-3300`
- **chart_note_window_days**: Old value `60` superseded → `90`
- **Rituxan/step_therapy_required**: Extraction error detected — web_page extraction shows step_therapy_required: True but raw text has no supporting evidence

### Cigna

- **fax_number**: Old value `(800) 768-4695` superseded → `(800) 768-4700`
- **chart_note_window_days**: Old value `60` superseded → `90`

### Humana

- **chart_note_window_days**: Old value `60` superseded → `90`
- **Rituxan/step_therapy_required**: Varies by indication — check before submitting

### Anthem BCBS

- **chart_note_window_days**: Old value `60` superseded → `90`

### UnitedHealthcare

- **fax_number**: Old value `(800) 699-4711` superseded → `(800) 699-4702`
- **chart_note_window_days**: Old value `60` superseded → `90`

## Cross-Payer Analysis

This section identifies payers that are outliers for specific drug requirements.
Outliers may indicate stale policy data or upcoming policy changes.

### Biosimilar Requirement Outliers

| Drug | Payer | Value | Other Payers |
|------|-------|-------|--------------|
| Entyvio | **Aetna** | `not_stated` | Cigna: required |
| Entyvio | **Humana** | `not_stated` | Cigna: required |
| Remicade | **Aetna** | `not_stated` | Cigna: preferred, Humana: required, Anthem BCBS: required |
| Rituxan | **Aetna** | `not_stated` | Humana: required, Anthem BCBS: required, UnitedHealthcare: required |

### Step Therapy Variation

| Drug | Payer | Step Therapy | Notes |
|------|-------|--------------|-------|
| Entyvio | Aetna | `True` |  |
| Entyvio | Cigna | `True` |  |
| Entyvio | Humana | `False` |  |
| Herceptin | Anthem BCBS | `False` |  |
| Herceptin | UnitedHealthcare | `True` |  |
| Rituxan | Aetna | `False` |  |
| Rituxan | Humana | `indication_dependent` | Varies by diagnosis |
| Rituxan | Anthem BCBS | `True` |  |
| Rituxan | UnitedHealthcare | `True` |  |

---

# Per-Payer Conflict Details

## Aetna

### Extraction Errors

- **Rituxan/step_therapy_required** (web_page): Raw text shows 'CD20+ documentation required' with no mention of step therapy

### Payer-Level Field Conflicts

### submission_methods

**Selected Value:** `portal, fax, phone`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | fax, portal, phone_status | high |
| phone_transcript | 2026-03-22 | portal, fax | high |
| web_page | 2024-10-01 | portal, fax, phone_status | medium |
| denial_letter | 2026-03-10 | portal, fax | high |

**Reasoning:** All sources consistently show portal as preferred method (Availity), fax as secondary (though number changed), and phone for status inquiries only. Phone transcript confirms 'Availity is the preferred method now' and 'Phone inquiries regarding PA status' from manual.

### fax_number

**Selected Value:** `(888) 267-3300`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | ~~(888) 267-3277~~ | **superseded** |
| phone_transcript | 2026-03-22 | (888) 267-3300 | high |
| web_page | 2024-10-01 | ~~(888) 267-3277~~ | **superseded** |
| denial_letter | 2026-03-10 | (888) 267-3300 | high |

**Superseded Values:**
- ~~(888) 267-3277~~ — Decommissioned February 1, 2026 per phone rep and denial letter

**Reasoning:** Phone transcript (2026-03-22) explicitly states 'That fax number was decommissioned as of February 1st, 2026' referring to old number. Denial letter (2026-03-10) confirms 'this fax line is no longer active for infusion medication prior authorizations as of February 2026'. Both recent sources provide new number (888) 267-3300.

### portal_url

**Selected Value:** `www.availity.com`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | www.availity.com | high |
| phone_transcript | 2026-03-22 | Availity | medium |
| web_page | 2024-10-01 | www.availity.com | high |
| denial_letter | 2026-03-10 | www.availity.com | high |

**Reasoning:** Three sources provide full URL www.availity.com. Phone transcript mentions 'Availity' without full URL but references same portal. All sources consistently point to Availity as the portal.

### phone_status_only

**Selected Value:** `(800) 624-0756, Option 3, Option 1`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | (800) 624-0756, Option 3, then Option 1 | high |
| phone_transcript | 2026-03-22 | (800) 624-0756 | medium |
| web_page | 2024-10-01 | (800) 624-0756, Option 3 | medium |
| denial_letter | 2026-03-10 | (800) 624-0756, Option 3, Option 1 | high |

**Reasoning:** Provider manual and denial letter both specify full IVR path 'Option 3, then Option 1' or 'Option 3, Option 1'. Web page shows incomplete path 'Option 3' only. Phone transcript confirms this number works for PA inquiries.

### pa_form

**Selected Value:** `AET-PA-2025`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | AET-PA-2025 | high |
| web_page | 2024-10-01 | ~~AET-PA-2024~~ | **superseded** |

**Superseded Values:**
- ~~AET-PA-2024~~ — Superseded by newer form version AET-PA-2025

**Reasoning:** Provider manual (2025-01-15) shows AET-PA-2025 while web page (2024-10-01) shows AET-PA-2024. Form version with year 2025 supersedes 2024 version. Manual is more recent and would have updated form version.

### required_documents

**Selected Value:** `Completed Aetna Prior Authorization Request Form, Current chart notes, Lab results supporting medical necessity, Letter of medical necessity from prescribing physician, Step therapy compliance documentation (for applicable biologics)`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | 5 document types listed | high |
| phone_transcript | 2026-03-22 | PA form, chart notes, labs, letter, step therapy docs | high |
| web_page | 2024-10-01 | 5 document types listed | medium |

**Reasoning:** Provider manual provides most comprehensive list. Other sources mention similar requirements with consistent core documents across all sources.

### chart_note_window_days

**Selected Value:** `90`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | ~~60~~ | **superseded** |
| phone_transcript | 2026-03-22 | 90 | high |
| web_page | 2024-10-01 | ~~60~~ | **superseded** |
| denial_letter | 2026-03-10 | 90 | high |

**Superseded Values:**
- ~~60~~ — Updated to 90 days in February 2026 policy revision per phone rep and denial letter

**Reasoning:** Phone rep explicitly states 'It's 90 days now. That was updated in the February policy revision. The manual might not reflect that yet.' Denial letter confirms 'exceeds the 90-day documentation window per our updated policy (effective February 1, 2026)'. Both recent sources (phone + denial) agree on 90 days and explicitly reference policy change.

### turnaround_standard_days

**Selected Value:** `5`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | 5 | high |
| phone_transcript | 2026-03-22 | 5 | high |
| web_page | 2024-10-01 | 5-7 | medium |

**Reasoning:** All sources consistently state 5 business days as the standard policy turnaround. Phone transcript notes operational delays ('7-10 days' for fax) but confirms policy remains '5 business days once we have everything'.

### turnaround_portal_days

**Selected Value:** `5`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| phone_transcript | 2026-03-22 | 5 | high |
| web_page | 2024-10-01 | 3-5 | medium |

**Reasoning:** Phone transcript confirms 'Availity submissions are still on track at 5 days'. Web page shows '3-5 business days' average. Phone rep indicates portal maintains standard turnaround unlike fax delays.

### turnaround_fax_days

**Selected Value:** `7-10`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| phone_transcript | 2026-03-22 | 7-10 | high |
| web_page | 2024-10-01 | ~~5-7~~ | **superseded** |

**Superseded Values:**
- ~~5-7~~ — Outdated due to fax system transition causing delays per phone rep

**Reasoning:** Phone transcript states 'fax submissions are taking 7-10 business days right now because of the transition'. This reflects current operational reality due to fax number change. Web page shows outdated '5-7 business days' from before transition.

### appeal_fax

**Selected Value:** `(888) 267-3350`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| web_page | 2024-10-01 | ~~(888) 267-3277~~ | **superseded** |
| denial_letter | 2026-03-10 | (888) 267-3350 | high |

**Superseded Values:**
- ~~(888) 267-3277~~ — Web page shows old general PA fax number, denial letter provides dedicated appeals fax

**Reasoning:** Denial letter provides specific appeals fax number (888) 267-3350. Web page shows (888) 267-3277 which is the old general PA fax that was decommissioned. Denial letter is more recent and authoritative for appeals process.

### appeal_phone

**Selected Value:** `(800) 624-0756, Option 3, Option 1`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | (800) 624-0756, Option 3, then Option 1 | high |
| web_page | 2024-10-01 | (800) 624-0756, Option 3 | medium |
| denial_letter | 2026-03-10 | (800) 624-0756, Option 3, Option 1 | high |

**Reasoning:** Provider manual and denial letter both specify full IVR path 'Option 3, then Option 1' or 'Option 3, Option 1'. Web page shows incomplete path. Most recent sources provide complete navigation.

### system_migration_in_progress

**Selected Value:** `Yes`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| phone_transcript | 2026-03-22 | transition mentioned | high |
| denial_letter | 2026-03-10 | system change referenced | high |

**Reasoning:** Phone transcript indicates 'fax submissions are taking 7-10 business days right now because of the transition'. Denial letter references fax line change 'as of February 2026'. Evidence points to system transition affecting operations.

### Drug-Level Conflicts

#### Remicade

### biosimilar_requirement

**Selected Value:** `not_stated`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | none | high |
| phone_transcript | 2026-03-22 | not_stated | medium |

**Reasoning:** No source mentions biosimilar requirements for Remicade. Provider manual states 'No mention of biosimilar requirements'.

#### Keytruda

### specific_testing

**Selected Value:** `PD-L1`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | PD-L1 testing results | high |
| web_page | 2024-10-01 | PD-L1 | high |

**Reasoning:** Both provider manual and web page consistently require PD-L1 testing. Manual states 'PD-L1 testing results required', web page states 'PD-L1 testing required'.

#### Rituxan

### specific_testing

**Selected Value:** `CD20+`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-15 | CD20 positive status | high |
| web_page | 2024-10-01 | CD20+ | high |

**Reasoning:** Both provider manual and web page consistently require CD20+ testing. Manual states 'CD20 positive status documentation required', web page states 'CD20+ documentation required'.


---

## Cigna

### Payer-Level Field Conflicts

### submission_methods

**Selected Value:** `portal, fax, phone`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | portal, fax, phone | high |
| phone_transcript | 2026-03-24 | portal, fax | high |
| web_page | 2025-08-01 | portal, fax, phone | medium |
| denial_letter | 2026-03-15 | portal, fax | high |

**Reasoning:** All sources consistently list portal as recommended/fastest, fax as alternative, and phone for urgent/status. Provider manual states 'CignaforHCP Portal... Recommended for fastest processing'

### fax_number

**Selected Value:** `(800) 768-4700`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | ~~(800) 768-4695~~ | **superseded** |
| phone_transcript | 2026-03-24 | (800) 768-4700 | high |
| web_page | 2025-08-01 | ~~(800) 768-4695~~ | **superseded** |
| denial_letter | 2026-03-15 | (800) 768-4695 | medium |

**Superseded Values:**
- ~~(800) 768-4695~~ — Superseded January 2026 - now goes to slower general medical PA queue per phone rep

**Reasoning:** Phone rep explicitly stated new dedicated infusion line: 'For infusion drugs specifically, we have a new dedicated line: (800) 768-4700. The old 4695 number still works but it goes to the general medical PA queue, so it's slower.' Change effective January 2026. Denial letter confirms dedicated infusion line exists at 4700.

### portal_url

**Selected Value:** `www.cignaforhcp.com`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | www.cignaforhcp.com | high |
| phone_transcript | 2026-03-24 | www.cignaforhcp.com | high |
| web_page | 2025-08-01 | www.cignaforhcp.com | high |
| denial_letter | 2026-03-15 | CignaforHCP | medium |

**Reasoning:** Consistent across all sources. Phone rep and provider manual both specify full URL. Web page confirms same URL. Denial letter references 'CignaforHCP' portal which maps to same URL.

### pa_form

**Selected Value:** `CG-PA-002`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | ~~CG-PA-001~~ | **superseded** |
| phone_transcript | 2026-03-24 | CG-PA-002 | high |
| web_page | 2025-08-01 | ~~CG-PA-001~~ | **superseded** |
| denial_letter | 2026-03-15 | CG-PA-002 | high |

**Superseded Values:**
- ~~CG-PA-001~~ — Superseded January 2026 per phone rep and denial letter

**Reasoning:** Phone rep explicitly stated: 'use the new one, CG-PA-002, not the old 001'. Denial letter confirms: 'Effective January 2026, infusion drug precertifications require the updated form CG-PA-002. The new form includes required biosimilar attestation fields.'

### required_documents

**Selected Value:** `Cigna Precertification Request Form, Treating physician's notes (within 90 days), Diagnostic test results supporting the diagnosis, Treatment plan including dosing schedule, Prior treatment history (required for all biologic medications)`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | listed documents | medium |
| phone_transcript | 2026-03-24 | updated requirements | high |
| web_page | 2025-08-01 | listed documents | medium |

**Reasoning:** Core documents consistent across sources. Chart note window updated from 60 to 90 days per phone rep and denial letter. All sources require diagnostic results, treatment plan, and prior treatment history for biologics.

### chart_note_window_days

**Selected Value:** `90`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | ~~60~~ | **superseded** |
| phone_transcript | 2026-03-24 | 90 | high |
| web_page | 2025-08-01 | ~~60~~ | **superseded** |
| denial_letter | 2026-03-15 | 90 | high |

**Superseded Values:**
- ~~60~~ — Updated to 90 days January 2026 per phone rep and denial letter

**Reasoning:** Phone rep explicitly stated: 'chart notes within 90 days — we updated that recently, used to be 60. That's outdated. It's 90 days as of January 2026.' Denial letter confirms: 'outside the 90-day documentation window (updated from 60 days per January 2026 policy revision)'

### turnaround_standard_days

**Selected Value:** `10-12`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | 7 | medium |
| phone_transcript | 2026-03-24 | 10-12 | high |
| web_page | 2025-08-01 | 7 | medium |

**Superseded Values:**
- ~~7~~ — Current operational turnaround longer due to system migration per phone rep March 2026

**Reasoning:** Phone rep stated current operational reality: 'Standard is supposed to be 7 business days but right now it's more like 10-12 because of the system migration.' This reflects actual current turnaround vs. stated policy.

### appeal_fax

**Selected Value:** `(800) 768-4699`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | (800) 768-4699 | high |
| web_page | 2025-08-01 | (800) 768-4695 | low |
| denial_letter | 2026-03-15 | (800) 768-4699 | high |

**Superseded Values:**
- ~~(800) 768-4695~~ — Web page error - this is the old PA fax number, not appeals fax

**Reasoning:** Provider manual and denial letter both specify (800) 768-4699. Web page shows (800) 768-4695 but this appears to be an error as that's the old PA fax number.

### appeal_phone

**Selected Value:** `(800) 768-4688, Option 4`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | (800) 768-4688, Option 4 | high |
| web_page | 2025-08-01 | (800) 768-4688 | medium |
| denial_letter | 2026-03-15 | (800) 768-4688, Option 4 | high |

**Reasoning:** Provider manual and denial letter both specify 'Option 4' for appeals. Web page shows same number but missing the Option 4 specification.

### Drug-Level Conflicts

#### Tysabri

### specific_testing

**Selected Value:** `JCV antibody testing, TOUCH Prescribing Program enrollment verification`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | JCV and TOUCH requirements | high |
| web_page | 2025-08-01 | JCV frequency update | high |

**Reasoning:** Provider manual states: 'JCV antibody testing REQUIRED before authorization' and 'TOUCH Prescribing Program enrollment verification required'. Web page updates frequency: 'JCV antibody testing now required every 6 months'

### notes

**Selected Value:** `JCV antibody testing now required every 6 months (previously annual). TOUCH Prescribing Program enrollment verification required.`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-06-01 | TOUCH requirement | high |
| web_page | 2025-08-01 | JCV frequency change | high |

**Reasoning:** Important clinical requirements and policy update from provider manual and web page.


---

## Humana

### Payer-Level Field Conflicts

### submission_methods

**Selected Value:** `portal, fax, phone`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | portal, fax, phone | high |
| phone_transcript | 2026-03-19 | portal, fax, phone | high |
| web_page | 2025-04-01 | portal, fax, phone | high |
| denial_letter | 2026-03-08 | portal, fax | medium |

**Reasoning:** All sources consistently list portal (Availity) as preferred, fax as standard alternative, and phone for urgent only. Provider manual states 'PREFERRED — Availity', web page states 'AVAILITY (PREFERRED)', and phone rep confirms both methods work though mentions 'Availity integration has been having issues'.

### portal_url

**Selected Value:** `www.availity.com`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | www.availity.com | high |
| phone_transcript | 2026-03-19 | humana.com/providers | low |
| web_page | 2025-04-01 | www.availity.com | high |
| denial_letter | 2026-03-08 | Availity | medium |

**Superseded Values:**
- ~~humana.com/providers~~ — This was mentioned for form downloads, not PA submissions

**Reasoning:** Provider manual and web page both specify 'www.availity.com' as the portal URL. Phone transcript mentions 'humana.com/providers' but this was in context of finding the form, not the submission portal. Denial letter just says 'Availity' without URL. The specific Availity URL is the actual submission portal.

### pa_form

**Selected Value:** `HUM-AUTH-2026`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | ~~HUM-AUTH-2024~~ | **superseded** |
| phone_transcript | 2026-03-19 | HUM-AUTH-2026 | high |
| web_page | 2025-04-01 | ~~HUM-AUTH-2024~~ | **superseded** |
| denial_letter | 2026-03-08 | HUM-AUTH-2026 | high |

**Superseded Values:**
- ~~HUM-AUTH-2024~~ — Superseded January 1st, 2026 per phone rep and denial letter

**Reasoning:** Phone rep explicitly stated 'We actually released a new form — HUM-AUTH-2026. It went into effect January 1st. The old form will still get processed but it might get kicked back because it doesn't have the biosimilar attestation section.' Denial letter confirms this by referencing the old form as problematic: 'Submission used form HUM-AUTH-2024, which does not include the biosimilar attestation section. Please resubmit using HUM-AUTH-2026.'

### required_documents

**Selected Value:** `Humana PA Form, Physician notes, Lab results relevant to diagnosis, Letter of medical necessity, Treatment plan with dosing schedule, Insurance verification confirmation, Current medication list`  
**Confidence:** 0.88

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | Humana PA Form, Physician notes (within 60 days), Lab results relevant to diagnosis, Letter of medical necessity, Treatment plan with dosing schedule, Insurance verification confirmation | high |
| web_page | 2025-04-01 | Humana PA Form, Office visit notes (within 60 days), Supporting lab results, Letter of medical necessity, Current medication list, Treatment plan with dosing | high |

**Reasoning:** Provider manual provides most comprehensive list. Web page has similar requirements with slight variations ('office visit notes' vs 'physician notes'). Combined both lists for completeness as these represent official documented requirements.

### chart_note_window_days

**Selected Value:** `90`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | ~~60~~ | **superseded** |
| phone_transcript | 2026-03-19 | 90 | high |
| web_page | 2025-04-01 | ~~60~~ | **superseded** |
| denial_letter | 2026-03-08 | 90 | high |

**Superseded Values:**
- ~~60~~ — Changed to 90 days per January 2026 policy update

**Reasoning:** Phone rep explicitly stated 'chart notes within 90 days — we changed that from 60, that's on the new form'. Denial letter confirms: 'Chart notes provided are dated September 2025 — outside the 90-day window per the January 2026 policy update.' This is clear supersession of the 60-day requirement.

### turnaround_standard_days

**Selected Value:** `10-14`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | 7-10 | medium |
| phone_transcript | 2026-03-19 | 10-14 | high |
| web_page | 2025-04-01 | 7 | low |

**Superseded Values:**
- ~~7~~ — Official policy but not current operational reality due to system migration

**Reasoning:** Phone rep provided current operational reality: 'Standard is 7 business days but honestly we're running behind. The real turnaround is more like 10-14 days right now. We're dealing with a system migration.' This represents actual current performance vs. stated policy, which is more useful for provider planning.

### appeal_mail

**Selected Value:** `Humana Appeals, PO Box 14165, Lexington KY 40512`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | Humana Appeals Department, PO Box 14165, Lexington KY 40512 | medium |
| denial_letter | 2026-03-08 | Humana Appeals, PO Box 14165, Lexington KY 40512 | high |

**Reasoning:** Both sources agree on the PO Box and city/state/zip. Denial letter uses slightly shorter format 'Humana Appeals' vs provider manual 'Humana Appeals Department' but both are the same address. Using the more recent denial letter format.

### system_migration_in_progress

**Selected Value:** `Yes`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | No | low |
| phone_transcript | 2026-03-19 | Yes | high |
| web_page | 2025-04-01 | No | low |
| denial_letter | 2026-03-08 | No | low |

**Reasoning:** Phone rep explicitly mentioned 'We're dealing with a system migration' when explaining delays. This explains current operational issues and longer turnaround times.

### Drug-Level Conflicts

#### Remicade

### notes

**Selected Value:** `Conventional DMARD trial required before approval. Biosimilar attestation required for new starts.`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | Step therapy and biosimilar requirements | high |
| web_page | 2025-04-01 | Conventional therapy failure and biosimilar attestation | high |

**Reasoning:** Summary of key requirements from provider manual and web page.

#### Rituxan

### step_therapy_required

**Selected Value:** `indication_dependent`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | indication_dependent | high |
| phone_transcript | 2026-03-19 | indication_dependent | high |
| web_page | 2025-04-01 | indication_dependent | high |
| denial_letter | 2026-03-08 | Yes | medium |

**Reasoning:** Multiple sources consistently state step therapy is required for RA indication only. Phone rep: 'if it's for RA you need step therapy documentation. For lymphoma or CLL indications, no step therapy needed.' Provider manual: 'Step therapy required for RA indication only.'

### biosimilar_requirement

**Selected Value:** `required`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | none | low |
| phone_transcript | 2026-03-19 | not_stated | low |
| web_page | 2025-04-01 | not_stated | low |
| denial_letter | 2026-03-08 | required | high |

**Reasoning:** Denial letter states 'Humana requires documentation of trial and failure of at least one conventional DMARD (e.g., methotrexate) AND one biosimilar rituximab product before brand Rituxan will be authorized.' This indicates biosimilar trial is required before brand Rituxan.

### indication_specific_requirements

**Selected Value:** `{'rheumatoid_arthritis': {'step_therapy_required': True, 'conventional_dmard_failure_required': True, 'biosimilar_trial_required': True}, 'lymphoma': {'step_therapy_required': False}, 'CLL': {'step_therapy_required': False}}`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| phone_transcript | 2026-03-19 | indication_dependent | high |
| denial_letter | 2026-03-08 | RA_specific | high |

**Reasoning:** Clear indication-specific requirements. Phone rep: 'For RA you need step therapy documentation. For lymphoma or CLL indications, no step therapy needed.' Denial letter details RA-specific requirements including conventional DMARD and biosimilar trial.

### diagnosis_restrictions

**Selected Value:** `rheumatoid_arthritis, lymphoma, CLL`  
**Confidence:** 0.8

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | RA | medium |
| phone_transcript | 2026-03-19 | RA, lymphoma, CLL | high |
| denial_letter | 2026-03-08 | rheumatoid_arthritis | medium |

**Reasoning:** Sources specifically mention RA, lymphoma, and CLL as covered indications with different requirements.

### notes

**Selected Value:** `CD20+ testing required. Step therapy and biosimilar requirements vary by indication - required for RA, not required for lymphoma/CLL.`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| phone_transcript | 2026-03-19 | Indication-dependent requirements | high |
| denial_letter | 2026-03-08 | RA-specific requirements | high |

**Reasoning:** Summary of key indication-dependent requirements from multiple sources.

#### Entyvio

### step_therapy_required

**Selected Value:** `No`  
**Confidence:** 0.75

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-01-01 | No | medium |
| web_page | 2025-04-01 | conflicting | low |

**Reasoning:** Provider manual mentions 'Anti-TNF failure or contraindication documentation' which suggests step therapy with anti-TNF agents, but web page extraction shows conflicting information. Based on raw text, this appears to be prior treatment failure requirement rather than formal step therapy.


---

## Anthem BCBS

### Payer-Level Field Conflicts

### submission_methods

**Selected Value:** `portal, fax, phone`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-01 | portal, fax, phone | high |
| phone_transcript | 2026-03-20 | portal, fax, phone | high |
| web_page | 2025-11-01 | portal, fax, phone | high |
| denial_letter | 2026-03-18 | portal, fax | medium |

**Reasoning:** All sources consistently show portal as fastest (3-5 days), fax as standard (5-7 days), and phone for urgent only. Provider manual states 'For urgent authorization requests only' for phone, web page shows 'PORTAL (FASTEST)' and 'PHONE (URGENT)', indicating clear preference order.

### portal_url

**Selected Value:** `www.anthem.com/providers`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-01 | www.anthem.com/providers | high |
| web_page | 2025-11-01 | anthem.com/providers | medium |
| denial_letter | 2026-03-18 | anthem.com/providers | medium |

**Reasoning:** Provider manual shows full URL 'www.anthem.com/providers' while web page and denial letter show shortened 'anthem.com/providers'. The provider manual's full URL format is more complete and appropriate for official documentation. All point to the same destination.

### chart_note_window_days

**Selected Value:** `90`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-01 | ~~60~~ | **superseded** |
| phone_transcript | 2026-03-20 | ~~60~~ | **superseded** |
| web_page | 2025-11-01 | 90 | high |
| denial_letter | 2026-03-18 | 90 | high |

**Superseded Values:**
- ~~60~~ — Policy updated to 90 days in November 2025 per web page and denial letter confirmation

**Reasoning:** Policy updated from 60 to 90 days in November 2025. Web page explicitly states 'Office notes from most recent visit (within 90 days — updated Nov 2025)'. Denial letter confirms '90-day documentation window per our November 2025 policy update'. Provider manual (60 days) and phone transcript (60 days) are outdated, predating the November 2025 policy change.

### appeal_phone

**Selected Value:** `(800) 274-7767, Option 5`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-01 | (800) 274-7767, Option 5 | high |
| web_page | 2025-11-01 | (800) 274-7767 → Option 1 → Option 1 | low |
| denial_letter | 2026-03-18 | (800) 274-7767, Option 5 | high |

**Superseded Values:**
- ~~(800) 274-7767 → Option 1 → Option 1~~ — Web page path is for general PA inquiries, not appeals

**Reasoning:** Provider manual and denial letter both specify '(800) 274-7767, Option 5' for appeals. Web page shows different path '(800) 274-7767 → Option 1 → Option 1' but this appears to be for general PA inquiries, not appeals specifically.

### common_denial_reasons

**Selected Value:** `{'reason': 'Missing biosimilar justification', 'percentage': '38%'}, {'reason': 'Outdated chart notes', 'percentage': '22%'}, {'reason': 'Incomplete PA form', 'percentage': '18%'}, {'reason': 'Missing lab results', 'percentage': '12%'}`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| web_page | 2025-11-01 | denial statistics | high |
| phone_transcript | 2026-03-20 | corroboration | medium |

**Reasoning:** Web page provides specific denial statistics. Phone transcript corroborates this, noting 'we're seeing a lot of submissions come in missing the HER2 results or without the biosimilar justification, and then it gets pended'.

### Drug-Level Conflicts

#### Herceptin

### step_therapy_required

**Selected Value:** `No`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-01 | No | high |
| phone_transcript | 2026-03-20 | No | high |
| web_page | 2025-11-01 | Yes | low |
| denial_letter | 2026-03-18 | No | high |

**Reasoning:** While biosimilar is required/preferred, the sources don't describe this as traditional 'step therapy' but rather as biosimilar-first policy. Phone transcript clarifies this as biosimilar preference rather than step therapy failure requirement.

### biosimilar_requirement

**Selected Value:** `required`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-01 | ~~preferred~~ | **superseded** |
| phone_transcript | 2026-03-20 | preferred | medium |
| web_page | 2025-11-01 | required | high |
| denial_letter | 2026-03-18 | required | high |

**Superseded Values:**
- ~~preferred~~ — Policy changed to required effective July 2025 per denial letter

**Reasoning:** Policy evolved from 'preferred' to 'required'. Denial letter from March 2026 states 'biosimilar trastuzumab (Ogivri, Herzuma, Kanjinti, or Trazimera) is preferred for new patient starts' and cites 'policy effective July 2025'. Phone transcript confirms current enforcement of biosimilar requirement.

### preferred_biosimilars

**Selected Value:** `Ogivri, Herzuma, Kanjinti, Trazimera`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| phone_transcript | 2026-03-20 | Ogivri, Herzuma | medium |
| denial_letter | 2026-03-18 | Ogivri, Herzuma, Kanjinti, Trazimera | high |

**Reasoning:** Denial letter specifies 'biosimilar trastuzumab (Ogivri, Herzuma, Kanjinti, or Trazimera)'. Phone transcript mentions 'formulary prefers Ogivri or Herzuma' but denial letter provides complete list.

### specialist_required

**Selected Value:** `Yes`  
**Confidence:** 0.8

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-01 | No | medium |
| phone_transcript | 2026-03-20 | Yes | high |

**Reasoning:** Phone transcript mentions 'oncology treatment plan' requirement, though provider manual doesn't explicitly state oncologist requirement. Given HER2 testing and oncology context, specialist involvement is implied.

### notes

**Selected Value:** `HER2 testing showing positive status required. Biosimilar justification required if requesting brand Herceptin. Oncology treatment plan required.`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2025-01-01 | HER2 testing results | high |
| phone_transcript | 2026-03-20 | HER2 testing showing positive status, biosimilar justification, oncology treatment plan | high |

**Reasoning:** Compiled from phone transcript and provider manual requirements for Herceptin.


---

## UnitedHealthcare

### Extraction Errors

- **Unknown/turnaround_urgent_hours** (web_page): No supporting text found for 48 hours - appears to be extraction error

### Payer-Level Field Conflicts

### submission_methods

**Selected Value:** `portal, fax, phone`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | portal, fax, phone | medium |
| phone_transcript | 2026-03-18 | portal, fax | high |
| web_page | 2026-03-01 | portal, fax, phone | high |
| denial_letter | 2026-03-05 | portal, fax | high |

**Reasoning:** All sources consistently list portal as preferred, fax as secondary, and phone for urgent only. Web page explicitly states portal is 'PREFERRED' and phone is 'URGENT ONLY'.

### fax_number

**Selected Value:** `(800) 699-4702`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | ~~(800) 699-4711~~ | **superseded** |
| phone_transcript | 2026-03-18 | (800) 699-4702 | high |
| web_page | 2026-03-01 | (800) 699-4702 | high |
| denial_letter | 2026-03-05 | (800) 699-4711 | medium |

**Superseded Values:**
- ~~(800) 699-4711~~ — Still works but 4702 is preferred for specialty/infusion drugs per phone agent and web page

**Reasoning:** Phone agent explicitly recommended (800) 699-4702 for infusion drugs: '4711 is the general medical PA fax. It still works, but for infusion drugs specifically, 4702 goes to the specialty team and they process faster.' Web page confirms this with 'NOTE: Use (800) 699-4702 for faster processing of infusion drugs'. Denial letter also mentions 4702 for future specialty drug submissions.

### portal_url

**Selected Value:** `www.uhcprovider.com`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | www.uhcprovider.com | medium |
| phone_transcript | 2026-03-18 | uhcprovider.com | high |
| web_page | 2026-03-01 | www.uhcprovider.com | high |
| denial_letter | 2026-03-05 | uhcprovider.com | high |

**Reasoning:** Consistent across all sources. Provider manual and web page use full www. format while phone and denial use shortened version, but both resolve to same site.

### pa_form

**Selected Value:** `UHC-PA-200`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | ~~UHC-PA-100~~ | **superseded** |
| phone_transcript | 2026-03-18 | UHC-PA-200 | high |
| web_page | 2026-03-01 | UHC-PA-200 | high |
| denial_letter | 2026-03-05 | UHC-PA-200 | high |

**Superseded Values:**
- ~~UHC-PA-100~~ — Being phased out per phone agent, replaced by UHC-PA-200

**Reasoning:** Phone agent explicitly stated 'Just use form UHC-PA-200 — that's the new specialty drug form. The old UHC-PA-100 is being phased out.' Web page confirms 'Use form UHC-PA-200 (Specialty Drug Prior Authorization)' and states 'New form UHC-PA-200 replaces UHC-PA-100'. Denial letter also references UHC-PA-200.

### required_documents

**Selected Value:** `UHC-PA-200 form, Clinical notes from most recent visit, Relevant lab/diagnostic results, Letter of medical necessity, Step therapy/biosimilar documentation, Prescription/order for the infused medication`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | UHC-PA-100, Clinical notes, Lab results, LMN, Prescription, Prior treatment history | medium |
| web_page | 2026-03-01 | UHC-PA-200, Chart notes, Lab results, LMN, Step therapy documentation | high |

**Reasoning:** Provider manual lists core documents, web page adds step therapy documentation requirement effective March 2026. Phone agent confirms biosimilar documentation is critical.

### chart_note_window_days

**Selected Value:** `90`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | ~~60~~ | **superseded** |
| phone_transcript | 2026-03-18 | ~~60~~ | **superseded** |
| web_page | 2026-03-01 | 90 | high |
| denial_letter | 2026-03-05 | 90 | high |

**Superseded Values:**
- ~~60~~ — Extended to 90 days per March 2026 policy update

**Reasoning:** Web page explicitly states 'Chart note window extended to 90 days (previously 60 days)' and 'Chart notes (within 90 days — updated March 2026)'. Denial letter confirms '90 days' requirement. Provider manual and phone transcript show outdated 60-day requirement.

### turnaround_standard_days

**Selected Value:** `5`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | 5 | medium |
| phone_transcript | 2026-03-18 | 5 | high |
| web_page | 2026-03-01 | 5-7 | medium |

**Reasoning:** Provider manual states 'All PA determinations are made within 5 business days of complete submission'. Phone agent confirms '5 business days standard'. Web page shows ranges but provider manual gives definitive policy.

### turnaround_urgent_hours

**Selected Value:** `24`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | 24 | medium |
| phone_transcript | 2026-03-18 | 24 | high |
| web_page | 2026-03-01 | 48 | extraction_error |

**Reasoning:** Provider manual states 'Urgent requests: determination within 24 hours'. Phone agent confirms '24 hours urgent'. Web page appears to have extraction error showing 48 hours.

### common_denial_reasons

**Selected Value:** `Missing biosimilar trial documentation, Incomplete step therapy documentation`  
**Confidence:** 0.85

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| phone_transcript | 2026-03-18 | Missing biosimilar documentation | high |
| denial_letter | 2026-03-05 | Missing biosimilar trial | high |

**Reasoning:** Phone agent states biosimilar documentation is 'the number one reason we deny Remicade requests'. Denial letter confirms denial due to missing biosimilar trial documentation.

### Drug-Level Conflicts

#### Remicade

### biosimilar_requirement

**Selected Value:** `required`  
**Confidence:** 0.95

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | ~~preferred~~ | **superseded** |
| phone_transcript | 2026-03-18 | required | high |
| web_page | 2026-03-01 | required | high |
| denial_letter | 2026-03-05 | required | high |

**Superseded Values:**
- ~~preferred~~ — Changed to required per March 2026 policy update

**Reasoning:** Policy changed from 'preferred' to 'required'. Phone agent: 'tried a biosimilar first'. Web page: 'Biosimilar step therapy is now REQUIRED for Remicade' (March 2026). Denial letter confirms biosimilars 'must be trialed'.

### notes

**Selected Value:** `Weight-based dosing documentation required`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | Weight-based dosing documentation required | medium |
| web_page | 2026-03-01 | Weight-based dosing docs | high |

**Reasoning:** Provider manual explicitly states 'Weight-based dosing documentation required' and web page confirms 'Weight-based dosing docs'.

#### Keytruda

### specific_testing

**Selected Value:** `PD-L1, MSI-H, TMB`  
**Confidence:** 0.9

| Source | Date | Value | Weight |
|--------|------|-------|--------|
| provider_manual | 2024-12-01 | PD-L1, MSI-H, TMB | medium |
| web_page | 2026-03-01 | Biomarker testing | high |

**Reasoning:** Provider manual specifies 'Biomarker testing results (PD-L1, MSI-H, TMB) as applicable'. Web page confirms 'Biomarker testing' requirement.


---
