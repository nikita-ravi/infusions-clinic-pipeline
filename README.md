# PA Route Reconciliation Pipeline

A skill-based LLM pipeline that reconciles conflicting prior authorization information across multiple payer sources. Built for ops teams who need to know which fax number actually works, not which one the manual says.

## Quick Start

Requires **Python 3.9+**

```bash
# 1. Set up API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Run reconciliation for all payers
python agentic_prototype_v2/reconciliation_agent.py

# 4. Generate conflict report
python agentic_prototype_v2/generate_conflict_report.py
```

Uses **Claude Sonnet** (`claude-sonnet-4-20250514`) for reconciliation.

Outputs:
- `reconciled_*.json` — structured route data per payer
- `conflict_report.md` — human-readable audit trail

---

## The Problem

You have 4 sources for Aetna's PA submission info:

| Source | Fax Number | Chart Note Window |
|--------|------------|-------------------|
| Provider Manual (Jan 2025) | (888) 267-3277 | 60 days |
| Phone Transcript (Mar 2026) | (888) 267-3300 | 90 days |
| Web Page (Oct 2024) | (888) 267-3277 | 60 days |
| Denial Letter (Mar 2026) | (888) 267-3300 | 90 days |

Which is correct? The phone rep says the old fax was "decommissioned February 1st." The denial letter cites a "90-day window per updated policy (effective February 1, 2026)."

If you use the wrong fax, your submission goes nowhere. If you use 60-day-old chart notes, you get denied. The information exists — it's just scattered across sources that don't agree.

---

## Why Not Deterministic Rules?

I built both. Here's what happened.

### The Deterministic Approach

```python
# Hardcoded source weights
AUTHORITY = {
    "denial_letter": 1.0,
    "phone_transcript": 0.75,
    "provider_manual": 0.5,
    "web_page": 0.4
}

confidence = freshness * 0.35 + authority * 0.35 + corroboration * 0.20
```

**Where it worked:** Simple fields with clear supersession. Fax number changed? Newer source wins.

**Where it broke:**

1. **Indication-specific requirements**: Humana's phone rep said "Rituxan step therapy is required for RA, but not for lymphoma or CLL." A weighted average can't output `{"RA": true, "lymphoma": false}`. It picks one boolean and loses critical information.

2. **Nuanced supersession**: The manual says 60 days. The phone rep says "It's 90 now, the manual might not reflect that yet." The rep isn't just newer — they're explicitly acknowledging the manual is stale. Deterministic weights can't encode "source A says source B is wrong."

3. **Extraction errors**: The extracted JSON said `Rituxan.step_therapy_required = true` from the web page. But the raw web page text says "Rituxan: CD20+ documentation required. Initial auth period: 6 months." No mention of step therapy. The extraction hallucinated, and deterministic scoring trusted it.

4. **Cross-field reasoning**: A phone rep says fax turnaround is "7-10 days right now because of the transition." Is 7-10 the new policy, or temporary operational delay? Deterministic rules can't distinguish — you need reasoning over context.

**The core issue:** Healthcare payer data has implicit semantics that require interpretation. "Preferred" vs "required" biosimilar. Initial vs renewal auth periods. Indication-dependent step therapy. You can write rules for known cases, but you'll keep finding new edge cases.

---

## The Skill-Based Approach

Instead of encoding rules in Python, I encoded **methodology** in a skill file that Claude follows.

### What's a Skill?

A skill is a markdown document that teaches Claude how to approach a specific domain problem. For reconciliation, `pa-reconciliation/SKILL.md` contains:

1. **Field inventory**: Every field to reconcile, with semantic notes
2. **Source authority hierarchy**: Which sources to trust and why
3. **Supersession detection**: How to identify when one source invalidates another
4. **Confidence scoring framework**: Freshness, specificity, corroboration, context
5. **Edge case handling**: Indication-specific requirements, extraction error detection, cross-payer outlier flagging
6. **Anti-hallucination rules**: Only cite values that exist in source text

### Why This Works

**The skill is the guardrail, the LLM is the reasoning engine.**

```
┌─────────────────────────────────────────────────────────────┐
│                    RECONCILIATION FLOW                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SKILL.md (Methodology)     +    Claude (Reasoning)         │
│  ─────────────────────           ──────────────────         │
│  • Source hierarchy              • Parse natural language   │
│  • Supersession rules            • Detect implicit context  │
│  • Field definitions             • Handle novel edge cases  │
│  • Confidence framework          • Explain decisions        │
│  • Anti-hallucination            • Cross-reference sources  │
│                                                             │
│                           ↓                                 │
│                                                             │
│               Structured JSON + Reasoning                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Without the skill, Claude reasons ad-hoc — it might weigh sources differently each run. Without Claude, you're stuck with hardcoded rules that can't handle nuance. Together: **deterministic framework + flexible reasoning**.

### Concrete Example: Supersession Detection

Deterministic approach needs explicit `fax_number_old` fields:

```python
if f"{field}_old" in source:
    mark_superseded(source[f"{field}_old"])
```

Skill-based approach reads natural language:

```markdown
## Supersession Detection

Look for language that explicitly deprecates old information:

**Strong signals:**
- "That fax number was decommissioned"
- "Please use [new value] instead"
- "As of [date], the old [X] is no longer valid"

**Medium signals:**
- "The manual might not reflect that yet"
- "We changed that in [month]"
```

When Claude sees the phone transcript:

> "The provider manual says chart notes within 60 days. Is it 60 or 90?"
> "It's 90 days now. That was updated in the February policy revision. The manual might not reflect that yet."

It recognizes the supersession pattern and marks the manual's 60-day value as outdated — even though there's no `chart_note_window_days_old` field in the data.

---

## Edge Cases Handled in SKILL.md

### 1. Extraction Error Detection (Step 0)

Problem: The extraction said `Rituxan.step_therapy_required = true` but the raw text had no supporting evidence.

Solution in skill:

```markdown
### Step 0: Verify Extracted Data Against Raw Text

Before reconciling, spot-check extracted field values against raw source text.
If an extracted value has NO supporting text in the raw source:
- Mark it as "extraction_error"
- Remove it from consideration
- Note it in output under "extraction_errors"

Priority fields to verify:
- step_therapy_required (high denial impact)
- biosimilar_requirement (high denial impact)
- specific_testing (missing test = automatic denial)
```

Result: Agent caught the hallucination, excluded it, and noted:
```json
"extraction_errors": [
  "web_page extraction shows step_therapy_required: True but raw text has no supporting evidence"
]
```

### 2. Indication-Specific Requirements

Problem: Rituxan step therapy varies by diagnosis — required for RA, not for lymphoma.

Solution in skill:

```markdown
- `indication_specific_requirements` - requirements that vary by diagnosis.
  **CRITICAL:** Some drugs have different rules per indication. Parse raw text
  for phrases like "for [diagnosis]", "when used for [indication]".
  Output as a dict keyed by indication.
```

Result:
```json
{
  "step_therapy_required": {
    "selected_value": "indication_dependent",
    "indication_specific_requirements": {
      "rheumatoid_arthritis": {"step_therapy_required": true},
      "lymphoma": {"step_therapy_required": false},
      "CLL": {"step_therapy_required": false}
    }
  }
}
```

### 3. Biosimilar-First as Step Therapy

Problem: Some payers require "biosimilar trial and clinical failure documentation" but don't call it "step therapy." Semantically, it's the same thing.

Solution in skill:

```markdown
- `step_therapy_required` - boolean. **Note:** If any source uses the phrase
  "biosimilar step therapy attestation" or requires "documentation of biosimilar
  trial and clinical failure" for a drug, set `step_therapy_required: true`.
  Biosimilar-first policies are functionally step therapy.
```

### 4. Cross-Payer Outlier Detection

Problem: Aetna doesn't require biosimilars for Remicade, but 4 other payers do. Is Aetna's policy stale?

Solution in skill:

```markdown
### Step 6: Flag Cross-Payer Outliers

After reconciling, compare drug-level policies across payers to identify outliers:
- If 4/5 payers require biosimilar-first but one doesn't, flag it
- Outlier may indicate stale policy or upcoming change

Output as `cross_payer_warnings`.
```

### 5. Anti-Hallucination Rules

```markdown
## What NOT to Do

5. **Don't hallucinate values** - Only cite values that actually exist in the
   extracted JSON or raw source text. If a field is not present for a drug
   in a source, treat it as **absent** — do not infer, assume, or fabricate.

6. **Don't invent conflicts** - A conflict only exists when two or more sources
   explicitly provide different values. If only one source mentions a field
   and others are silent, that is NOT a conflict.
```

---

## Scalability

### Why This Scales

1. **New payers**: Add source files to `payer_sources/new_payer/`. Run extraction. Run reconciliation. The skill applies unchanged.

2. **New fields**: Add to the field inventory in SKILL.md. The agent starts reconciling it immediately — no code changes.

3. **Policy changes**: When payers change requirements, the methodology stays the same. Phone reps will say "that changed in [month]" and the skill knows how to handle supersession.

4. **New edge cases**: Add a rule to SKILL.md. Example: We discovered biosimilar-first = step therapy. Added one paragraph to the skill. Every future run applies it.

### Cost

~$0.15-0.20 per payer per run (Claude Sonnet). For 5 payers: ~$1.00 total.

### Throughput

Sequential: ~2 min per payer (API latency dominated)
Parallel: Could run all payers concurrently, limited by API rate limits

---

## Project Structure

```
ruma/
├── agentic_prototype_v2/           # The pipeline
│   ├── reconciliation_agent.py     # Main agent (skill + Claude API)
│   ├── generate_conflict_report.py # Report generator
│   ├── data/
│   │   └── extracted_data.json     # Pre-extracted structured data
│   └── reconciled_*.json           # Output files
│
├── pa-reconciliation/
│   └── SKILL.md                    # Reconciliation methodology (v1.2.0)
│
├── payer_sources/                  # Raw source files
│   ├── aetna/
│   │   ├── provider_manual.txt
│   │   ├── phone_transcript.txt
│   │   ├── web_page.txt
│   │   └── denial_letter.txt
│   └── ... (5 payers)
│
├── .env                            # ANTHROPIC_API_KEY
├── requirements.txt
├── DISCOVERY_AGENT_DESIGN.md       # Phone tree agent design (optional)
└── README.md
```

---

## Output Format

### Reconciled JSON

```json
{
  "payer": "Aetna",
  "fields": {
    "fax_number": {
      "selected_value": "(888) 267-3300",
      "confidence": 0.95,
      "reasoning": "Phone transcript and denial letter both cite new number. Phone rep explicitly stated old number was 'decommissioned February 1st'.",
      "superseded_values": [
        {"value": "(888) 267-3277", "reason": "Decommissioned February 2026"}
      ],
      "sources_considered": [
        {"source": "phone_transcript", "date": "2026-03-22", "value": "(888) 267-3300", "weight": "high"},
        {"source": "provider_manual", "date": "2025-01-15", "value": "(888) 267-3277", "weight": "superseded"}
      ]
    }
  },
  "drugs": {
    "Rituxan": {
      "step_therapy_required": {
        "selected_value": false,
        "confidence": 0.7,
        "extraction_errors": ["web_page extraction shows true but raw text has no evidence"]
      }
    }
  },
  "extraction_errors": [...],
  "cross_payer_warnings": [...]
}
```

### Conflict Report

Markdown report showing:
- Summary stats (conflicts found, supersession events, extraction errors)
- High-risk conflicts (fields that cause denials if wrong)
- Cross-payer analysis (outlier detection)
- Per-payer detailed breakdowns with source tables

---

## Key Insights

1. **The methodology is the product.** The skill file captures domain expertise about how to weigh conflicting healthcare information. The code is just orchestration.

2. **Explicit > implicit.** When a phone rep says "the manual might not reflect that yet," that's more valuable than any freshness heuristic. Teach the LLM to recognize these signals.

3. **Verify against raw text.** Extraction hallucinates. The reconciliation layer must be a safety net. If an extracted value has no supporting evidence in the source, exclude it.

4. **Surface uncertainty.** Ops teams don't need false confidence. They need to know which fields are solid (0.95) and which need manual verification (0.70). The reasoning field explains why.

5. **Denial impact drives priority.** Wrong fax number = submission lost. Wrong chart note window = denial. Wrong appeal deadline = missed window. The skill prioritizes high-impact fields for verification.

---

## What's Next

- **Confidence calibration**: Compare predicted confidence against actual approval rates
- **Incremental updates**: Re-reconcile only changed sources instead of full runs
- **Feedback loop**: When ops manually overrides a value, update the skill with learned patterns
- **Multi-modal sources**: Handle PDFs and HTML tables directly in extraction
