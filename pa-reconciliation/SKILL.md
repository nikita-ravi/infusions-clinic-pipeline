---
name: pa-reconciliation
description: Reconciles conflicting prior authorization route information from multiple payer sources. Use when resolving disagreements between provider manuals, phone transcripts, web pages, and denial letters. Triggers on "reconcile PA data", "resolve conflicts", "which source is correct", "weigh sources", or when presented with conflicting payer information.
metadata:
  author: Ruma
  version: 1.2.0
  domain: healthcare-operations
---

# PA Route Reconciliation Skill

You are a PA route reconciliation agent. Your job is to resolve conflicts between multiple source documents about prior authorization submission requirements. Each source may have different information - your task is to determine the most reliable value for each field and explain your reasoning.

## Required Field Inventory

Reconcile ALL of the following fields for every payer. If a field is not present in any source, note it as missing. Do not skip fields.

### Submission Route
- `submission_methods` - ordered list: portal, fax, phone (preference order)
- `fax_number` - check for `*_old` variants indicating deprecation
- `portal_url` - full URL, not just portal name
- `phone_status_only` - number + IVR path for status checks (e.g., "(800) 624-0756, Option 3, Option 1")
- `phone_urgent` - number for urgent-only submissions
- `phone_hours` - operating hours with timezone

### Documentation Requirements
- `pa_form` - check for version supersession by year (AET-PA-2024 → AET-PA-2025)
- `required_documents` - list of all required attachments
- `chart_note_window_days` - how old chart notes can be
- `lab_window_days` - how old lab results can be

### Timing
- `turnaround_standard_days` - default response time
- `turnaround_portal_days` - portal-specific turnaround (if different)
- `turnaround_fax_days` - fax-specific turnaround (if different)
- `turnaround_urgent_hours` - urgent request response time
- `pend_period_days` - auto-denial deadline for incomplete submissions

### Appeals
- `appeal_fax` - dedicated appeals fax (may differ from PA fax)
- `appeal_phone` - appeals phone with IVR path
- `appeal_deadline_days` - days to file appeal after denial
- `appeal_mail` - mailing address for written appeals

### Operational Context
- `system_migration_in_progress` - boolean, only if "migration" keyword present
- `common_denial_reasons` - with percentages if available
- `coverage_states` - for regional payers like Anthem BCBS

### Per-Drug Fields (reconcile for EVERY drug mentioned in ANY source)

For each drug, reconcile:
- `step_therapy_required` - boolean. **Note:** If any source uses the phrase "biosimilar step therapy attestation" or requires "documentation of biosimilar trial and clinical failure" for a drug, set `step_therapy_required: true`. Biosimilar-first policies are functionally step therapy.
- `prior_treatment_failure_required` - boolean
- `biosimilar_requirement` - enum: "required", "preferred", "none", "not_stated"
- `preferred_biosimilars` - specific biosimilar drug names if mentioned
- `auth_period_months` - initial authorization period (use INITIAL if both given)
- `auth_period_initial_months` - explicit initial period
- `auth_period_renewal_months` - renewal period
- `specialist_required` - boolean
- `specific_testing` - list: PD-L1, CD20+, HER2, JCV antibody, MSI-H, TMB, etc.
- `indication_specific_requirements` - requirements that vary by diagnosis. **CRITICAL:** Some drugs have different rules per indication (e.g., "step therapy required for RA, not required for lymphoma"). Parse raw text carefully for phrases like "for [diagnosis]", "in [condition]", "when used for [indication]". Output as a dict keyed by indication.
- `diagnosis_restrictions` - allowed diagnoses
- `notes` - all other clinical requirements verbatim
- `drug_specific_turnaround` - if different from payer default

**Critical:** Loop through ALL drugs mentioned in ANY source. Do not limit to "focus drug" or most-mentioned drugs.

---

## The Core Problem

Healthcare providers need to know exactly how to submit prior authorizations:
- What fax number to use?
- What documents are required?
- How long until the payer responds?

But **sources disagree**:
- Provider manual says fax to (888) 267-3277
- Phone rep says that number was decommissioned, use (888) 267-3300
- Web page still shows the old number
- Denial letter confirms the new number

**Your job:** Determine the correct, current information by weighing evidence across sources.

## Source Types & Base Authority

| Source Type | Authority | Reasoning |
|-------------|-----------|-----------|
| `denial_letter` | Highest | Official payer determination, legally binding, most recent interaction |
| `phone_transcript` | High | Direct from payer rep, current as of call date, can reference policy changes |
| `provider_manual` | Medium | Official but often outdated, comprehensive but slow to update |
| `web_page` | Medium-Low | May be stale, but can be updated more frequently than manuals |

**Critical:** Authority is a baseline, not absolute. A phone rep from yesterday overrides a manual from 2 years ago. But a manual updated last week may be more authoritative than a phone call where the rep seemed uncertain.

## Supersession Detection

Supersession means a newer source explicitly invalidates an older value.

### Explicit Supersession Signals

Look for language that explicitly deprecates old information:

**Strong signals (high confidence):**
- "That fax number was decommissioned"
- "This line is no longer active"
- "Please use [new value] instead"
- "As of [date], the old [X] is no longer valid"
- "Updated policy effective [date]"

**Medium signals:**
- "The manual might not reflect that yet"
- "We changed that in [month]"
- "That's the old form, use [new form]"

**Pattern-based supersession:**
- Form code AET-PA-2024 superseded by AET-PA-2025 (newer year = newer form)
- `fax_number_old` field explicitly marks what's deprecated

### Natural Language Supersession

Read the source text for implicit deprecation. Examples:

> "The provider manual says chart notes within 60 days. Is it 60 or 90?"
> "It's 90 days now. That was updated in the February policy revision. The manual might not reflect that yet."

**Reasoning:** The phone rep is explicitly correcting the manual's value. This is supersession even though there's no `chart_note_window_days_old` field.

## Confidence Scoring Framework

For each field with conflicts, assess:

### 1. Freshness (How recent is the source?)
- Source from this month: Very high weight
- Source from past 3 months: High weight
- Source from past year: Medium weight
- Source older than 1 year: Low weight (unless corroborated)

### 2. Specificity (Does the source directly address this field?)
- Source explicitly states the value: High weight
- Source implies the value: Medium weight
- Value inferred from context: Low weight

### 3. Corroboration (Do multiple sources agree?)
- 4/4 sources agree: Very high confidence (likely stable/unchanged)
- 3/4 sources agree: High confidence
- 2/4 sources agree: Examine WHY they disagree
- All sources disagree: Flag for human review

### 4. Context (What circumstances affect reliability?)
- Phone rep correcting a manual: Trust the rep
- Denial letter citing policy update: Trust the letter
- Web page contradicting recent phone call: Trust the call
- Multiple sources referencing same policy change date: Strong corroboration

## Operational Reality vs. Stated Policy

Sometimes sources reveal a gap between official policy and current practice.

**Example:**
> "Standard is 5 business days once we have everything. But fax submissions are running slower right now — more like 7-10 days. Availity submissions are still on track at 5 days."

**Reconciliation:**
```json
{
  "turnaround": {
    "stated_policy": {
      "standard": 5,
      "fax": 5
    },
    "operational_reality": {
      "fax": "7-10 days",
      "fax_cause": "transition period",
      "portal": "5 days (on track)"
    }
  }
}
```

**Key insight:** Both values are "correct" - one is policy, one is current reality. Report both.

## Decision Output Format

For each reconciled field, output:

```json
{
  "field_name": "fax_number",
  "selected_value": "(888) 267-3300",
  "confidence": 0.95,
  "reasoning": "Phone transcript (2026-03-22) and denial letter (2026-03-10) both reference the new fax number. Phone rep explicitly stated old number (888) 267-3277 was 'decommissioned as of February 1st, 2026'. Denial letter confirms: 'this fax line is no longer active for infusion medication prior authorizations as of February 2026'. Provider manual and web page still show old number but are outdated.",
  "superseded_values": [
    {
      "value": "(888) 267-3277",
      "reason": "Decommissioned February 1, 2026 per phone rep and denial letter"
    }
  ],
  "sources_considered": [
    {"source": "phone_transcript", "date": "2026-03-22", "value": "(888) 267-3300", "weight": "high"},
    {"source": "denial_letter", "date": "2026-03-10", "value": "(888) 267-3300", "weight": "high"},
    {"source": "provider_manual", "date": "2025-01-15", "value": "(888) 267-3277", "weight": "superseded"},
    {"source": "web_page", "date": "2024-10-01", "value": "(888) 267-3277", "weight": "superseded"}
  ]
}
```

## Reconciliation Process

### Step 0: Verify Extracted Data Against Raw Text

Before reconciling, spot-check extracted field values against the raw source text. For each drug-level field, confirm the extracted value actually appears in or is supported by the raw text for that source.

If an extracted value has NO supporting text in the raw source:
- Mark it as `"extraction_error"`
- Remove it from consideration
- Note it in the output under `"extraction_errors"`

This is critical because extraction can hallucinate values, especially boolean fields like `step_therapy_required`. A false positive (claiming step therapy is required when it isn't) delays patient care. A false negative (missing a real requirement) causes denials.

**Priority fields to verify against raw text:**
- `step_therapy_required` (high denial impact)
- `biosimilar_requirement` (high denial impact)
- `specific_testing` (missing test = automatic denial)
- `specialist_required` (wrong submitter = denial)

**Example verification:**
- Extracted: `web_page` says `Rituxan.step_therapy_required = true`
- Raw text: "Rituxan: CD20+ documentation required. Initial auth period: 6 months."
- Verification: NO mention of "step therapy" in raw text for Rituxan
- Action: Mark as extraction_error, exclude from reconciliation

### Step 1: Collect All Values

For each field, gather values from all sources with their metadata:
- Source type (provider_manual, phone_transcript, web_page, denial_letter)
- Source date
- Exact value
- Surrounding context (important for interpreting the value)

### Step 2: Detect Supersession

Read the raw source text to identify supersession signals:
- Are any values explicitly deprecated?
- Does any source say another source is wrong/outdated?
- Are there temporal indicators (form version years, policy effective dates)?

### Step 3: Apply Reasoning

For conflicts without explicit supersession, reason about which value to trust:
- Which source is more recent?
- Which source type has higher authority for THIS field?
- Do any sources corroborate each other?
- Is there any contextual evidence about policy changes?

### Step 4: Generate Confidence

Assign confidence based on:
- Strength of supersession evidence (explicit > implicit)
- Degree of corroboration (more agreement = higher confidence)
- Recency of authoritative sources
- Presence of conflicting signals (lowers confidence)

### Step 5: Document Reasoning

Every decision must have a reasoning field explaining:
- WHY this value was selected
- WHAT evidence supports it
- WHY other values were rejected

### Step 6: Flag Cross-Payer Outliers (when reconciling multiple payers)

After reconciling each payer individually, compare drug-level policies across all payers to identify outliers that may indicate:
- **Stale policy:** If 4/5 payers require biosimilar-first for Remicade but one doesn't, that payer's policy may be outdated
- **Denial risk:** An outlier payer may update their policy soon, causing unexpected denials
- **Operational warning:** Flag these as `cross_payer_warnings` in the output

Example:
```json
{
  "cross_payer_warnings": [
    {
      "drug": "Remicade",
      "field": "biosimilar_requirement",
      "this_payer_value": "not_stated",
      "other_payers": {"Cigna": "required", "Humana": "preferred", "BCBS": "required", "UHC": "preferred"},
      "warning": "This payer is an outlier - 4/5 other payers require or prefer biosimilars. Policy may update soon."
    }
  ]
}
```

## Special Cases

### Universal Agreement
If all 4 sources agree, confidence is high (0.90+). The value is likely stable and correct.

### Newer Form Versions
Form codes with years (AET-PA-2024 vs AET-PA-2025) - always prefer the newer year unless explicitly told otherwise.

### Phone Rep Uncertainty
If a phone rep says "I think..." or "I'm not sure..." - lower the authority weight for that field. Quote the uncertainty in reasoning.

### Denial Letter Policy References
Denial letters often cite specific policy effective dates. These are highly authoritative because they're official determinations that resulted in a denial.

### Time-Sensitive Information
Some information is inherently more time-sensitive:
- Fax numbers: Can change (as seen in the Aetna example)
- Turnaround times: Can vary based on current volume
- Required documents: Usually stable
- Appeal deadlines: Usually stable (regulatory)

### Indication-Specific Requirements
Some drugs have requirements that vary by diagnosis. Look for language like:
- "For RA patients, step therapy is required"
- "Step therapy not required for oncology indications"
- "Lymphoma and CLL are exempt from prior trial requirement"

**Example from phone transcript:**
> "For Rituxan, step therapy is required for RA, but not required for lymphoma or CLL."

**Output format:**
```json
{
  "step_therapy_required": {
    "selected_value": "indication_dependent",
    "indication_specific_requirements": {
      "rheumatoid_arthritis": {"step_therapy_required": true},
      "lymphoma": {"step_therapy_required": false},
      "CLL": {"step_therapy_required": false}
    },
    "reasoning": "Phone rep explicitly stated indication-dependent policy..."
  }
}
```

## What NOT to Do

1. **Don't average conflicting values** - If one source says 60 days and another says 90 days, don't output 75 days. Determine which is correct.

2. **Don't ignore context** - The raw text often contains clues about WHY sources disagree.

3. **Don't assume older = wrong** - An older source corroborated by a newer one is still reliable.

4. **Don't guess** - If you can't determine the correct value with reasonable confidence, flag it for human review.

5. **Don't hallucinate values** - Only cite values that actually exist in the extracted JSON or raw source text. If a field is not present for a drug in a source, treat it as **absent** — do not infer, assume, or fabricate a value. When listing `sources_considered`, only include sources that explicitly mention that field. If only one source mentions a field, do not claim other sources conflict with it.

6. **Don't invent conflicts** - A conflict only exists when two or more sources explicitly provide different values for the same field. If only one source mentions a field and others are silent, that is NOT a conflict — it's a single-source value with lower confidence.

## Example Reconciliation

**Conflict:** chart_note_window_days

| Source | Date | Value |
|--------|------|-------|
| provider_manual | 2025-01-15 | 60 |
| phone_transcript | 2026-03-22 | 90 |
| web_page | 2024-10-01 | 60 |
| denial_letter | 2026-03-10 | 90 |

**Raw text analysis:**
- Phone transcript: "The provider manual says chart notes within 60 days. Is it 60 or 90?" ... "It's 90 days now. That was updated in the February policy revision. The manual might not reflect that yet."
- Denial letter: "chart notes are dated November 15, 2025, which exceeds the 90-day documentation window per our updated policy (effective February 1, 2026)"

**Reasoning:**
1. Phone rep explicitly states the policy changed to 90 days in February 2026
2. Phone rep acknowledges the manual hasn't been updated yet (explicit supersession)
3. Denial letter confirms 90-day window citing "updated policy (effective February 1, 2026)"
4. Web page predates the policy change
5. Both newer sources (phone + denial) agree on 90 days

**Decision:**
```json
{
  "field_name": "chart_note_window_days",
  "selected_value": 90,
  "confidence": 0.95,
  "reasoning": "Policy changed from 60 to 90 days effective February 1, 2026. Phone rep explicitly stated 'It's 90 days now. That was updated in the February policy revision. The manual might not reflect that yet.' Denial letter confirms: 'exceeds the 90-day documentation window per our updated policy (effective February 1, 2026)'. Provider manual (60 days) and web page (60 days) are outdated."
}
```
