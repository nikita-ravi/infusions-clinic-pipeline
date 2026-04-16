# Prior Authorization Route Reconciliation Pipeline

## The Problem

Infusion clinics need to know exactly how to submit a prior authorization to a specific payer for a specific drug. The answer varies by payer, changes frequently, and lives scattered across provider manuals, payer websites, phone reps, and denial letters — all of which contradict each other.

**Example conflict**: Aetna's provider manual says fax to `(888) 267-3277`. The phone rep says that number was decommissioned in February 2026 and the new number is `(888) 267-3300`. The manual says chart notes within 60 days; the denial letter cites a January 2026 policy update changing it to 90 days. Which is correct?

This pipeline takes 4 conflicting sources per payer and produces a single trustworthy route with per-field confidence scores and a full audit trail explaining every decision.

**Dataset scope**: 5 payers (Aetna, Anthem/BCBS, Cigna, Humana, UnitedHealthcare) with 4 sources each and 4-5 drugs per payer, totaling 20 source documents and 21 (payer, drug) reconciliations.

## Quick Start

### Streamlit Dashboard (Recommended)

```bash
pip install -r requirements.txt
streamlit run reconciliation_v2/frontend/app.py
```

Opens an interactive dashboard with payer selector, conflict viewer, and audit trails. Uses pre-reconciled output from `output_v2/`.

### Run Reconciliation Pipeline

```bash
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=your-key" > .env  # optional, enables LLM summaries
python -m reconciliation_v2.main --all    # outputs to output_v2/
```

### Run Agentic Extraction (Experimental)

```bash
pip install -r requirements.txt

# Set up API key (required for agentic extraction)
echo "ANTHROPIC_API_KEY=your-key" > .env

# Option A: Run extraction only (outputs to agentic_prototype/extracted_data.json)
python -m agentic_prototype.extraction_agent

# Option B: Run full pipeline (extraction + reconciliation → output_agentic/)
python -m agentic_prototype.run_full_pipeline
```

See [The Agentic Extraction Experiment](#the-agentic-extraction-experiment) for details on the three-tier defense architecture.

---

## Design Philosophy

**Deterministic core, LLM at edges.** The reconciliation logic is entirely deterministic — same input, same output, fully auditable. When an ops person asks "why did you tell me to fax this number?", the answer traces to specific sources, not "the model thought so." The LLM (Claude Haiku, ~$0.02/run) only handles executive summaries and prose extraction. It never touches confidence scores or value selection.

**Schema-driven, not hand-tuned.** The pipeline discovers field families from structural patterns: `fax_number` + `fax_number_old` → supersession pair, `turnaround_standard` + `turnaround_urgent` → qualifier family. Adding a new payer requires zero code changes.

**Three field classes:**

| Class | Example | Handling |
|-------|---------|----------|
| Reconciliation target | `fax_number` (4 sources disagree) | Apply scoring primitives, pick winner |
| Single-source fact | `appeal_mail` (only denial letter has it) | Pass through with attribution |
| Operational context | `system_migration_in_progress` | Surface as warning, don't reconcile |

---

## The Five Reconciliation Primitives

| Primitive | What It Does |
|-----------|--------------|
| **Freshness** | Exponential decay, 180-day half-life. 6-month-old source retains 50% weight. |
| **Authority** | Source type weight. Denial letters (1.0) > phone (0.75) > web/manuals (0.5). |
| **Corroboration** | Sources agreeing. Universal agreement (4/4) triggers confidence floor ≥0.85. |
| **Supersession** | Explicit invalidation via `{field, field_old}` pairs or policy update dates. |
| **Qualification** | When values differ by qualifier (portal vs fax), output structured dict. |

**Scoring formula** (weighted sum with confidence floors):
```
confidence = freshness×0.35 + authority×0.35 + corroboration×0.20 + policy_boost×0.10
confidence = max(confidence, floor)  // floors: universal agreement, post-supersession, high-authority single-source
```

### Concrete Example: Aetna fax_number

Four sources provide a fax number:
- **Manual** (Jan 2025) and **web page** (Oct 2024): `(888) 267-3277`
- **Phone transcript** (Mar 2026) and **denial letter** (Mar 2026): `(888) 267-3300`

Both fresh sources carry `fax_number_old: (888) 267-3277` with status "Decommissioned February 1, 2026."

The engine detects the `{fax_number, fax_number_old}` supersession pair, marks the two older sources as superseded, scores the remaining sources (denial letter wins on authority, phone corroborates), and outputs `(888) 267-3300` at 0.85 confidence. A reviewer asking "why not 267-3277?" can trace the decision to a specific supersession event with dated deprecation.

---

## Data Problems We Encountered

### Problem 1: Same Field, Different Contexts

Aetna's web page lists two turnaround times: portal 3-5 days, fax 5-7 days. Early versions collapsed these into one field and picked 3-5, losing the fax-specific information.

**Fix**: Added `turnaround_portal_days` and `turnaround_fax_days` as separate fields.

### Problem 2: Initial vs Renewal Auth Periods

Aetna's manual: "Remicade: Initial auth 6 months. Renewal 12 months." Early extraction grabbed 12 (renewal). For a new PA, ops needs the initial period — thinking you have 12 months when you have 6 causes authorization lapses.

**Fix**: Added `auth_period_initial_months` and `auth_period_renewal_months`. Primary field defaults to initial.

### Problem 3: "Preferred" vs "Required" Biosimilar

Cigna's manual: "biosimilar preferred for new starts." Early extraction marked this as `required`. But preferred ≠ required — one delays treatment unnecessarily, the other gets denied.

**Fix**: Strict keyword detection. "Required" only when text contains required/must/mandatory.

### Problem 4: Phone Option Numbers Dropped

BCBS denial letter: "Appeal phone: (800) 274-7767, Option 5". Early extraction dropped ", Option 5". Ops calling without Option 5 gets routed to general services, wasting 30+ minutes.

**Fix**: Preserve full phone strings including option routing.

### Problem 5: Source Dates from Wrong Metadata

Aetna web page has "Scraped date: March 2026" and "Last updated on page: October 2024". Early extraction used scraped date, making stale content appear fresh and corrupting confidence scores.

**Fix**: Prioritize "Last updated" content dates over scrape metadata.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECONCILIATION PIPELINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Extracted JSON]                                                │
│        ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 1: Schema Discovery                                │    │
│  │ • Detect field families (*_old pairs, qualifiers)        │    │
│  │ • Classify: reconcile vs pass-through vs context         │    │
│  └─────────────────────────────────────────────────────────┘    │
│        ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 2: Supersession Detection                          │    │
│  │ • {field, field_old} pairs                               │    │
│  │ • *_old_status deprecation strings                       │    │
│  │ • *_policy_update dated invalidation                     │    │
│  │ • Version detection (AET-PA-2024 → AET-PA-2025)          │    │
│  └─────────────────────────────────────────────────────────┘    │
│        ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 3: Confidence Scoring                              │    │
│  │ • Freshness (180-day half-life)                          │    │
│  │ • Authority (denial > phone > web/manual)                │    │
│  │ • Corroboration (agreement bonus)                        │    │
│  │ • Confidence floors (universal agreement, etc.)          │    │
│  └─────────────────────────────────────────────────────────┘    │
│        ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 4: Raw Text Validation                             │    │
│  │ • Cross-check selected values against source files       │    │
│  │ • Flag mismatches, adjust confidence                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│        ↓                                                         │
│  [Reconciled Output + Audit Trail]                               │
│        ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ LLM Enhancement (Claude Haiku, optional)                 │    │
│  │ • Executive summary generation                           │    │
│  │ • Drug requirement extraction from prose                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Output per payer:**
- `output_v2/{payer}_reconciled.json` — Machine-readable with full audit trails
- `output_v2/{payer}_report.md` — Human-readable report with conflicts highlighted

**Drug reconciliation**: The unit is (payer, drug), not just payer. Per-payer drug counts:
- Aetna: Remicade, Entyvio, Keytruda, Rituxan (4)
- Anthem/BCBS: Herceptin, Keytruda, Ocrevus, Remicade, Rituxan (5)
- Cigna: Entyvio, Keytruda, Remicade, Tysabri (4)
- Humana: Entyvio, Ocrevus, Remicade, Rituxan, Tysabri (5)
- UHC: Herceptin, Keytruda, Ocrevus, Remicade, Rituxan (5)

---

## The Agentic Extraction Experiment

The v2 pipeline uses pre-extracted JSON. For production scale across hundreds of payers, we need extraction from raw source files. I built an LLM-first extraction prototype (`agentic_prototype/`) to evaluate this path.

### V1 Agentic Results: Systematic Failures

| Field | Failure Mode | Impact |
|-------|--------------|--------|
| `turnaround_standard_days` | Extracted `90` (chart note window) as turnaround | Ops expects 3-month wait when actual is 7 days |
| `portal_url` | Truncated to bare name (`"Availity"`) | Ops can't find submission URL |
| `biosimilar_requirement` | "Preferred" inflated to "required" | Unnecessary treatment delays |
| `auth_period_months` | Grabbed renewal (12) instead of initial (6) | Authorization lapses |
| `appeal_phone` | Dropped option routing | Ops misrouted, misses appeal deadline |

### V2 Agentic: Three-Tier Defense

**Tier 1 — Prompt-level**: Explicit field disambiguation ("turnaround ≠ chart_note_window ≠ auth_period"), source-phrase grounding (every value must cite verbatim text), payer isolation.

**Tier 2 — Schema-level**: Pattern validation (`pa_form` must match `[A-Z]{2,5}-...-\d{2,4}`), URL format validation, enum constraints (`biosimilar_requirement` is `required|preferred|none|not_stated`).

**Tier 3 — Post-extraction**: Turnaround sanity check (≥30 days flagged), biosimilar keyword verification, cross-payer drug removal, auth period correction (use initial if both present).

### Results After Fixes

| Metric | V1 | V2 |
|--------|----|----|
| Turnaround correct | 2/5 | 5/5 |
| Biosimilar accuracy | 3/5 | 5/5 |
| Auth period (initial) | 2/5 | 5/5 |
| Cross-payer contamination | 2 instances | 0 |

### Why the Deterministic Pipeline Ships

The deterministic pipeline's failure mode is bounded to "missing data." If a regex doesn't match, the field is null — it doesn't hallucinate.

The agentic pipeline, even with three-tier defense, can produce plausible-looking wrong values. For a take-home, **correctness > ambition**.

**For production scale**: The agentic approach is the path forward — regex doesn't generalize across 500 payers with different document layouts. The three-tier defense makes LLM extraction trustworthy by bounding failure modes.

---

## Tools Considered and Rejected

**LangChain/LangGraph**: Straight-line pipeline, no orchestration needed.
**Vector retrieval / RAG**: 100KB of source data fits in context.
**MCP**: No external systems to call.
**AutoGPT-style agents**: Auditability is the product, not autonomy.

Each would be pattern-matching on "modern LLM architecture" rather than solving the reconciliation problem.

---

## Known Limitations

- **Indication-conditional rules as prose**: Humana Rituxan requires step therapy for RA but not lymphoma — this flows through as notes, not structured fields.
- **Shared policy sections under-extracted**: "For Remicade and Entyvio: must fail conventional therapy" captures Remicade but may miss Entyvio.
- **No plan-type differentiation**: Commercial vs Medicare vs Medicaid rules not separated.
- **Web-only drugs may filter out**: Output requires 2+ sources or high-authority source; web-only mentions can fall through.

---

## What Would Come Next

**Reconciliation pipeline:**
- Event-driven re-reconciliation when new sources arrive
- Confidence calibration against actual approval rates
- SQLite audit trail for compliance

**Agentic extraction:**
- Eval harness with annotated ground truth
- Structured table extraction from HTML/PDF
- Per-extraction confidence scoring

---

## Project Structure

```
reconciliation_v2/           # Deterministic pipeline (production)
├── discovery/               # Schema & field family detection
├── pipeline/
│   ├── reconcile.py         # Main reconciliation logic
│   ├── scoring.py           # Confidence scoring (weighted sum + floors)
│   ├── supersession.py      # Deprecated value detection
│   └── raw_text_validator.py
├── llm/                     # Claude Haiku for summaries
├── reports/                 # JSON & Markdown generation
├── frontend/app.py          # Streamlit dashboard (powered by v2 pipeline)
└── main.py

agentic_prototype/           # LLM extraction experiment
├── extraction_agent.py      # Three-tier extraction with validation
├── pipeline.py              # Reconciliation adapter
└── run_full_pipeline.py
```

---

## Streamlit Dashboard

The dashboard provides an interactive interface for exploring reconciled PA routes. Features:
- Payer selector with conflict counts
- Best route summary (fax, phone, portal)
- Drug-specific requirements (tabbed view)
- Conflicts & audit trail viewer
- Raw source evidence

---

**Cost**: ~$0.02/run for LLM features (Claude Haiku with caching). Pipeline works without API key.
