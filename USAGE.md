# Quick Start Guide

## Running the Pipeline

### Option 1: Rules-Only (No LLM, Recommended First)

```bash
cd /Users/nikitaravi/Desktop/ruma
python -m reconciliation.main
```

**Output:**
```
Payer Route Reconciliation Pipeline
Focus drug: Remicade

Loading payer data...
✓ Loaded 5 payers

Processing Aetna...
  ✓ JSON: output/aetna_reconciled.json
  ✓ Markdown: output/aetna_report.md
...
✓ Pipeline complete!
```

**Check the results:**
```bash
cat output/aetna_report.md
cat output/aetna_reconciled.json
```

### Option 2: With LLM Reasoning (Requires API Key)

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-api-key-here"

# Run with reasoning
python -m reconciliation.main --with-reasoning
```

**What happens:**
1. Pipeline runs all rules (same as Option 1)
2. For each reconciled field, generates 2-3 sentence explanation via Haiku
3. Caches results to `.cache/reasoning/`
4. Adds `reasoning` field to JSON output
5. Includes reasoning in Markdown reports

**Example reasoning output:**

Without LLM:
```json
{
  "field": "fax_number",
  "value": "8882673300",
  "confidence": 1.0,
  "reasoning": null
}
```

With LLM:
```json
{
  "field": "fax_number",
  "value": "8882673300",
  "confidence": 1.0,
  "reasoning": "The fax number 888-267-3300 was selected based on a March 2026 phone transcript and denial letter, both confirming the old number (888-267-3277) was decommissioned February 1, 2026. High confidence (1.0) due to recent, corroborating sources with explicit deprecation signals."
}
```

**Cost:**
- First run: ~$0.02-0.05 (45-50 Haiku calls)
- Subsequent runs: $0 (hits cache)

## Viewing Results

### JSON Output (for programmatic use)

```bash
jq '.fields.fax_number' output/aetna_reconciled.json
```

```json
{
  "value": "8882673300",
  "confidence": 1.0,
  "decision_path": [
    "explicit_deprecation: Found fax_number_old → fax_number pair in AET-SRC-002",
    "recency_boost: Source is 23 days old → Boost: +0.30",
    "authority_boost: Source type: phone_transcript → Boost: +0.20"
  ],
  "contributing_sources": ["AET-SRC-002"],
  "superseded_sources": [],
  "conflicts_detected": true,
  "reasoning": "..."
}
```

### Markdown Reports (for humans)

```bash
less output/aetna_report.md
```

**Sections:**
1. **Summary** - Overall stats (conflicts, confidence distribution)
2. **Reconciled Route** - High-confidence fields (the answer)
3. **Conflicts & Warnings** - Fields with issues
4. **Decision Audit Trail** - Full rule-by-rule explanation

## Interpreting Confidence Scores

| Score | Meaning | Action |
|-------|---------|--------|
| 0.9-1.0 | Very high | Use this value confidently |
| 0.7-0.89 | High | Use, but verify if critical |
| 0.5-0.69 | Medium | Review conflicts, may need manual check |
| 0.0-0.49 | Low | Manual verification required |

## Common Scenarios

### Scenario 1: Quick lookup for ops team

**Question:** "What's the current fax number for Aetna Remicade PAs?"

**Answer:**
```bash
jq '.fields.fax_number.value' output/aetna_reconciled.json
# → "8882673300"

jq '.fields.fax_number.confidence' output/aetna_reconciled.json
# → 1.0
```

**Result:** `(888) 267-3300` with confidence 1.0 → Use it.

### Scenario 2: Investigating a conflict

**Question:** "Why are there two UHC fax numbers?"

**Check the report:**
```bash
grep -A 20 "### Fax Number" output/unitedhealthcare_report.md
```

**Output:**
```markdown
### Fax Number
⚠️ Conflict detected across sources

Conflicting values:
- ✗ UHC-SRC-001: (800) 699-4711  (general PA line)
- ✓ UHC-SRC-002: (800) 699-4702  (specialty line, "faster for infusion drugs")

Selected: (800) 699-4702
Confidence: 0.95
```

**Reasoning (with LLM):**
"The specialty fax number 800-699-4702 was selected over the general line (800-699-4711) based on the March 2026 phone transcript where the rep explicitly stated '4702 goes to the specialty team and processes faster for infusion drugs.' High confidence (0.95) due to recent source and specialty routing preference."

### Scenario 3: Comparing payers

**Question:** "Which payers require biosimilar step therapy for Remicade?"

```bash
for payer in aetna unitedhealthcare cigna blue_cross_blue_shield humana; do
  echo -n "$payer: "
  jq -r '.fields.remicade_requirements.value.biosimilar_required // "N/A"' \
    output/${payer}_reconciled.json
done
```

**Output:**
```
aetna: N/A
unitedhealthcare: True
cigna: N/A
blue_cross_blue_shield: N/A
humana: N/A
```

## Troubleshooting

### "Error: payer_sources/extracted_route_data.json not found"

You're not in the right directory. Run:
```bash
cd /Users/nikitaravi/Desktop/ruma
```

### "ModuleNotFoundError: No module named 'pydantic'"

Install dependencies:
```bash
pip install pydantic anthropic rich pytest
```

### LLM reasoning not working

Check API key:
```bash
echo $ANTHROPIC_API_KEY
```

If empty, set it:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Or pass it directly:
```bash
python -m reconciliation.main --with-reasoning --api-key "your-key-here"
```

### Cache is stale

Clear cache to regenerate reasoning:
```bash
rm -rf .cache/reasoning/
python -m reconciliation.main --with-reasoning
```

## Next Steps

1. **Review the rules-only output first** (free, fast)
2. **Check conflicts in markdown reports** (human-readable)
3. **Verify high-confidence fields** against your knowledge
4. **Add LLM reasoning** when you have API key
5. **Iterate on rules** if any decisions seem wrong

## File Locations

- **Input:** `payer_sources/extracted_route_data.json`
- **Output:** `output/{payer}_reconciled.json` (JSON)
- **Reports:** `output/{payer}_report.md` (Markdown)
- **Cache:** `.cache/reasoning/` (LLM results)
- **Code:** `reconciliation/` (pipeline modules)
