# Prior Authorization Route Reconciliation

## What This Does

Takes 4 conflicting sources per payer (provider manual, phone transcript, web page, denial letter) and produces a single trustworthy PA submission route. The hard part isn't extraction — it's deciding what to trust when sources disagree.

**Quick start:**
```bash
pip install -r requirements.txt
streamlit run reconciliation_v2/frontend/app.py
```

---

## The Core Problem

Aetna's provider manual says fax to `(888) 267-3277`. The phone rep says that number was decommissioned in February and the new number is `(888) 267-3300`. The manual says chart notes within 60 days; the denial letter cites a policy update changing it to 90 days.

Which is correct? You can't just pick the most recent — a phone rep might be wrong. You can't just trust official documents — they lag behind policy changes by months. You need a system that weighs multiple signals and shows its work.

---

## How I Approached It

### Layer 1: Schema Discovery

Before reconciling anything, the pipeline scans all sources for a payer and figures out what fields exist. It detects patterns:

- `fax_number` + `fax_number_old` → this is a supersession pair, the old value was deprecated
- `turnaround_standard` + `turnaround_urgent` + `turnaround_fax` → these are qualifiers of the same base field
- `system_migration_in_progress` → this is operational context, surface it as a warning, don't reconcile it

This means I didn't have to hardcode field relationships. When I add a new payer with different field naming, the schema discovery adapts.

### Layer 2: Supersession Detection

The most useful signal in the data turned out to be explicit deprecation. When the phone transcript says:

> "That fax number was decommissioned as of February 1st. Use (888) 267-3300 instead."

The extraction captures both `fax_number: (888) 267-3300` and `fax_number_old: (888) 267-3277`. The pipeline sees this pair, finds which sources still have the old value, and marks them as superseded. They're excluded from scoring entirely.

Same logic applies to form versions. `AET-PA-2024` gets superseded by `AET-PA-2025` based on the version number pattern.

### Layer 3: Confidence Scoring

For fields that aren't cleanly superseded, I score each source:

```
confidence = freshness × 0.35 + authority × 0.35 + corroboration × 0.20 + policy_boost × 0.10
```

**Freshness**: Exponential decay with 180-day half-life. A 6-month-old source retains 50% weight.

**Authority**: Source type matters. A denial letter is official policy (1.0). A phone rep is direct but fallible (0.75). Provider manuals and web pages may be stale (0.5).

**Corroboration**: If 4/4 sources agree, confidence floor is 0.85 regardless of other factors. Agreement is strong signal.

**Policy boost**: If a source explicitly mentions a policy update date, it gets a boost — it's aware of changes others might not reflect yet.

### Layer 4: Raw Text Validation

This was added after I found extraction errors. The pipeline takes the final selected value and searches for it in the raw source file. If `fax_number: (888) 267-3300` was selected from `AET-SRC-002`, I verify that string actually appears in `payer_sources/aetna/phone_transcript.txt`.

If it's not found, confidence gets penalized. If it is found, confidence gets a small boost. This catches hallucinations and extraction mistakes.

---

## Problems I Ran Into

### Problem 1: Turnaround vs Chart Note Window Confusion

Early extraction pulled `90` as `turnaround_standard_days`. But 90 days isn't a turnaround time — that's the chart note documentation window. The LLM was grabbing numbers without understanding context.

**Fix**: Added explicit field disambiguation in the extraction prompt: "turnaround is decision time (typically 3-14 days). chart_note_window is documentation recency (typically 60-90 days). Do not confuse these."

### Problem 2: Initial vs Renewal Auth Periods

Aetna's manual says "Remicade: Initial auth 6 months. Renewal 12 months." Early extraction grabbed 12 months. For a new PA, ops needs the initial period — using renewal causes authorization lapses.

**Fix**: Added `auth_period_initial_months` and `auth_period_renewal_months` as separate fields. The primary `auth_period_months` defaults to initial.

### Problem 3: "Preferred" vs "Required" Biosimilar

Cigna's manual says "biosimilar preferred for new starts." Early extraction marked this as `required`. But preferred ≠ required — one causes unnecessary delays, the other gets denied.

**Fix**: Strict keyword detection in post-processing. Only mark as "required" if the text contains "required", "must", or "mandatory". Otherwise "preferred" or "not_stated".

### Problem 4: Phone Options Getting Dropped

BCBS denial letter says "Appeal phone: (800) 274-7767, Option 5". Early extraction dropped ", Option 5". Ops calling without the option gets routed to general services, wasting 30+ minutes.

**Fix**: Preserve full phone strings including option routing. Validate against raw text to catch truncation.

### Problem 5: Source Dates From Wrong Metadata

Aetna's web page has "Scraped: March 2026" and "Last updated: October 2024". Early extraction used the scrape date, making stale content appear fresh and corrupting confidence scores.

**Fix**: Prioritize "Last updated" content dates over retrieval metadata. Added date extraction logic that looks for page-level update timestamps first.

---

## The Agentic Extraction Experiment

The main pipeline uses pre-extracted JSON. For production scale (hundreds of payers), I built an LLM extraction prototype in `agentic_prototype/`.

### What Broke Initially

| Field | Failure | Impact |
|-------|---------|--------|
| `turnaround_standard_days` | Extracted `90` (chart note window) | Ops expects 3-month wait when actual is 7 days |
| `biosimilar_requirement` | "Preferred" → "required" | Unnecessary treatment delays |
| `auth_period_months` | Grabbed renewal instead of initial | Authorization lapses |
| `appeal_phone` | Dropped option routing | Ops misrouted, misses deadline |

### Three-Tier Defense

**Tier 1 — Prompt-level**: Explicit field disambiguation, source phrase grounding (every value must cite verbatim text), payer isolation (don't let Aetna info bleed into Cigna output).

**Tier 2 — Schema-level**: Pattern validation (PA forms must match `[A-Z]{2,5}-...-\d{2,4}`), URL validation, enum constraints (`biosimilar_requirement` must be `required|preferred|none|not_stated`).

**Tier 3 — Post-extraction**: Sanity checks (turnaround ≥30 days is suspicious), keyword verification for biosimilar, auth period correction (use initial if both present).

### After Fixes

| Metric | Before | After |
|--------|--------|-------|
| Turnaround correct | 2/5 payers | 5/5 |
| Biosimilar accurate | 3/5 payers | 5/5 |
| Auth period (initial) | 2/5 payers | 5/5 |

The deterministic pipeline ships because its failure mode is bounded — if extraction fails, the field is null, not hallucinated. The agentic approach is the path forward for scale, but needs the three-tier defense to be trustworthy.

---

## Running It

### Streamlit Dashboard
```bash
pip install -r requirements.txt
streamlit run reconciliation_v2/frontend/app.py
```

Four tabs: Payer Route (the actionable output), Audit Trail (scoring breakdown per field), Compare Payers (side-by-side drug requirements), Pipeline Info (architecture and stats).

### Run Reconciliation Pipeline
```bash
python -m reconciliation_v2.main --all
```

Outputs to `output_v2/`. Reads from `payer_sources/extracted_route_data.json`.

### Run Agentic Extraction
```bash
echo "ANTHROPIC_API_KEY=your-key" > .env
python -m agentic_prototype.extraction_agent
python -m agentic_prototype.run_full_pipeline
```

Extracts from raw source files in `payer_sources/*/`. Outputs to `output_agentic/`.

---

## Project Structure

```
reconciliation_v2/           # Main pipeline
├── discovery/               # Schema detection, field families
├── pipeline/
│   ├── reconcile.py         # Core reconciliation logic
│   ├── scoring.py           # Confidence calculation
│   ├── supersession.py      # Deprecated value detection
│   └── raw_text_validator.py # Validation against source files
├── frontend/app.py          # Streamlit dashboard
└── main.py

agentic_prototype/           # LLM extraction experiment
├── extraction_agent.py      # Three-tier extraction
└── run_full_pipeline.py     # Extraction → reconciliation

payer_sources/               # Raw source files
├── aetna/
│   ├── provider_manual.txt
│   ├── phone_transcript.txt
│   ├── web_page.txt
│   └── denial_letter.txt
├── ... (5 payers)
└── extracted_route_data.json

output_v2/                   # Reconciled output (used by Streamlit)
```

---

## What I'd Do Next

- **Confidence calibration**: Compare confidence scores against actual approval rates to tune the weights
- **Incremental updates**: Re-reconcile only affected fields when a new source arrives
- **Structured table extraction**: Handle HTML/PDF tables in the agentic pipeline
- **Eval harness**: Annotated ground truth to measure extraction accuracy systematically
