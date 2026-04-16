# Payer Route Reconciliation Pipeline (Option B)

A schema-driven reconciliation pipeline that resolves conflicting prior authorization data across multiple sources, producing confidence-ranked routes with full audit trails.

## Quick Start

```bash
# Install dependencies
pip install pydantic anthropic rich streamlit python-dotenv

# Set up API key (optional - enables LLM features)
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Run pipeline for all payers
python -m reconciliation_v2.main --all

# Run for specific payer
python -m reconciliation_v2.main --payer cigna

# Launch dashboard
streamlit run reconciliation_v2/frontend/app.py
```

## What It Does

Given conflicting source data (provider manuals, phone transcripts, web pages, denial letters), the pipeline:

1. **Extracts & normalizes** fields across sources (phone numbers, URLs, form codes)
2. **Detects conflicts** and applies supersession logic (deprecated fax numbers, policy updates)
3. **Scores confidence** using freshness × authority × corroboration
4. **Produces structured output** with decision audit trails
5. **Generates reports** (JSON + Markdown) with conflicts highlighted

## Output

For each payer:
- `output_v2/{payer}_reconciled.json` - Machine-readable reconciled data
- `output_v2/{payer}_report.md` - Human-readable report with audit trail

### Sample Output Structure

```json
{
  "payer": "Cigna",
  "best_route": {
    "submission": {
      "preferred_method": "portal",
      "preferred_url": "www.cignaforhcp.com",
      "fallback_method": "fax",
      "fallback_fax": "(800) 768-4700",
      "do_not_use": ["(800) 768-4695"]
    },
    "turnaround": {
      "standard": "10-12 days (system migration delays)",
      "urgent": "24 hours"
    },
    "all_drug_requirements": {
      "Entyvio": {
        "auth_period_months": 6,
        "prior_treatment_failure_required": true,
        "notes": ["Anti-TNF failure or contraindication required"]
      }
    }
  },
  "fields": {
    "fax_number": {
      "value": "(800) 768-4700",
      "confidence": 0.90,
      "has_conflicts": true,
      "superseded_values": ["(800) 768-4695"],
      "decision_path": ["...audit trail..."]
    }
  }
}
```

## Architecture

```
[Extracted JSON] → [Deterministic Pipeline] → [Structured Output]
                           ↓
              ┌────────────┴────────────┐
              │   Schema Discovery      │
              │   Field Family Detection│
              │   Supersession Logic    │
              │   Confidence Scoring    │
              │   Drug Reconciliation   │
              └─────────────────────────┘
                           ↓
                   [LLM Enhancement]
                   (Executive Summary)
                   (Drug Requirements)
```

**Key Design Decisions:**
- **Deterministic core**: Same input → same output, fully auditable
- **LLM at edges only**: Extraction and summarization, not reconciliation logic
- **No hardcoded values**: All drug names, payer names discovered from data
- **Supersession detection**: Automatically handles deprecated fax numbers, old form versions

## Scoring Formula

```
confidence = freshness × authority × (1 + corroboration) × policy_boost
```

| Factor | How It Works |
|--------|--------------|
| **Freshness** | Exponential decay, 180-day half-life |
| **Authority** | denial_letter (1.0) > phone (0.75) > web/manual (0.5) |
| **Corroboration** | Multiple sources agreeing boosts confidence |
| **Policy boost** | Sources citing policy updates get priority |

## Project Structure

```
reconciliation_v2/
├── discovery/           # Schema & field family detection
├── pipeline/
│   ├── reconcile.py     # Main reconciliation logic
│   ├── scoring.py       # Confidence scoring
│   ├── supersession.py  # Deprecated value detection
│   └── raw_text_validator.py  # Cross-validate against source files
├── llm/
│   ├── client.py        # Anthropic API with caching
│   ├── drug_requirements.py   # Extract drug requirements
│   └── executive_summary.py   # Generate TL;DR
├── reports/             # JSON & Markdown generation
├── frontend/
│   └── app.py           # Streamlit dashboard
└── main.py              # CLI entry point
```

## LLM Usage

The pipeline uses Claude Haiku for:
- **Executive summaries**: TL;DR for each payer route
- **Drug requirement extraction**: Structured fields from prose notes

**Cost**: ~$0.02 per full run (all 5 payers) with aggressive caching.

LLM features are optional - the pipeline works without an API key, just without summaries.

## Tests

```bash
pytest reconciliation_v2/tests/ -v
```

## Dashboard

```bash
streamlit run reconciliation_v2/frontend/app.py
```

Features:
- Payer selector with conflict counts
- Best route summary with warnings
- Drug-specific requirements (all drugs, tabbed view)
- Conflicts & audit trail viewer
- Raw source evidence

## Files

| File | Purpose |
|------|---------|
| `payer_sources/*/` | Raw source files (manuals, transcripts, etc.) |
| `extracted_route_data.json` | Pre-extracted structured data |
| `output_v2/` | Pipeline output (JSON + Markdown) |
| `.env` | API key (create this file) |
