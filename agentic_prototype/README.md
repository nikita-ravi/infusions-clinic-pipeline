# Agentic Extraction Prototype

This prototype demonstrates how an **agentic extraction layer** would work alongside the **deterministic reconciliation pipeline**.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   RAW SOURCES                    AGENTIC LAYER                  │
│   ────────────                   ────────────                   │
│   provider_manual.txt    ──┐                                    │
│   phone_transcript.txt   ──┼──→  Extraction Agent  ──┐          │
│   web_page.txt           ──┤     (LLM-powered)       │          │
│   denial_letter.txt      ──┘                         │          │
│                                                      ↓          │
│                                              Structured JSON    │
│                                                      │          │
│   ─────────────────────────────────────────────────────────────│
│                                                      │          │
│                              DETERMINISTIC LAYER     │          │
│                              ──────────────────      │          │
│                                                      ↓          │
│                                           Reconciliation        │
│                                           (reconciliation_v2)   │
│                                                      │          │
│                                                      ↓          │
│                                           Trusted Route         │
│                                           + Confidence Scores   │
│                                           + Audit Trail         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Why This Design?

| Layer | Agentic (LLM) | Deterministic (Rules) |
|-------|---------------|----------------------|
| **Extraction** | ✅ Handles messy text, varying formats | ❌ Brittle regex/parsing |
| **Reconciliation** | ❌ Non-deterministic, hard to audit | ✅ Same input → same output |

**Best of both worlds**: LLM flexibility for parsing, rule-based reliability for output.

## Files

| File | Purpose |
|------|---------|
| `extraction_agent.py` | LLM-powered extraction from raw text |
| `pipeline.py` | Full demo: extraction → reconciliation |
| `extracted_data.json` | Output from extraction agent |

## Usage

```bash
# Run extraction agent on all payers
cd agentic_prototype
python extraction_agent.py

# Run full pipeline demo
python pipeline.py

# Then use output with reconciliation_v2
cp reconciliation_input.json ../payer_sources/extracted_route_data.json
cd ..
python -m reconciliation_v2.main --all
```

## Cost

For 5 payers × 4 sources = 20 LLM calls:
- **Model**: Claude 3 Haiku
- **Est. cost**: ~$0.10-0.20
- **With caching**: $0 after first run

## What the Agent Extracts

From each source document, the agent extracts:

```json
{
  "fax_number": "(800) 768-4700",
  "fax_number_old": "(800) 768-4695",
  "portal_url": "www.cignaforhcp.com",
  "turnaround_standard_days": "10-12 (system migration)",
  "turnaround_urgent_hours": 24,
  "drugs": {
    "Remicade": {
      "auth_period_months": 6,
      "step_therapy_required": true,
      "biosimilar_preferred": true,
      "notes": "Biosimilar preferred for new starts (2025)"
    }
  },
  "system_migration_in_progress": true
}
```

## Comparison with Provided Data

The extraction agent aims to match or exceed the provided `extracted_route_data.json`:

- **Same schema**: Output format matches what reconciliation expects
- **More context**: Agent can capture nuances like "(system migration)"
- **Drug extraction**: Agent extracts ALL drugs mentioned, not just key ones

## Extending This

To add new capabilities:

1. **Source Discovery Agent**: Scrape payer websites for PA pages
2. **Phone Agent**: Navigate IVR trees (see Option C writeup)
3. **Monitoring Agent**: Detect when sources change
4. **Verification Agent**: Cross-check extraction against raw text
