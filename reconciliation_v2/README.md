# Reconciliation Pipeline v2

A schema-driven payer route reconciliation system that resolves conflicting prior authorization data across multiple sources.

## Architecture: LLM Bookends

```
[LLM Extraction] → JSON → [Deterministic Pipeline] → JSON → [LLM Report Generation]
      ↑                           ↑                              ↑
  Flexible parsing         Auditable, testable            Natural language
```

The pipeline is **fully deterministic** - given the same extracted JSON input, it produces identical output every time. LLMs handle the fuzzy edges (extraction, reporting) while the core logic is transparent and auditable.

## Quick Start

```bash
# Run for all payers
python -m reconciliation_v2.main

# Run for specific payer
python -m reconciliation_v2.main --payer aetna

# Override focus drug selection
python -m reconciliation_v2.main --payer humana --drug Rituxan

# Run tests
pytest reconciliation_v2/tests/ -v
```

## Core Concepts

### Field Families

The system discovers field relationships via pattern matching:

| Pattern | Example | Relationship |
|---------|---------|--------------|
| `{X, X_old}` | `fax_number`, `fax_number_old` | Supersession pair |
| `{X, X_old_status}` | `pa_form`, `pa_form_old_status` | Deprecation with reason |
| `{X, X_policy_update}` | `chart_note_window_days`, `chart_note_policy_update` | Policy date marker |
| `{base_qualifier_unit}` | `turnaround_standard_days`, `turnaround_urgent_hours` | Qualifier family |

### Three Supersession Triggers

1. **{X, X_old} pair**: Value in X_old is deprecated; any source reporting that value is superseded
2. **X_old_status**: Contains reason for deprecation (e.g., "Updated 2025-01")
3. **X_policy_update**: Sources predating the policy date are zeroed out

### Scoring Formula

```
score = freshness × authority × (1 + corroboration) × policy_boost
```

**Freshness** (exponential decay, 180-day half-life):
```
freshness = 0.5 ^ (age_days / 180)
```

**Authority weights**:
| Source Type | Weight |
|-------------|--------|
| `denial_letter` | 1.00 |
| `phone_transcript` | 0.75 |
| `web_page` | 0.50 |
| `provider_manual` | 0.50 |

**Corroboration**:
```
corroboration = 1 - 0.5^(n_agreeing - 1)  // counts non-superseded sources only
```

**Confidence Floor** (universal agreement):
```
When n/n sources agree (n >= 2): floor = 0.7 + 0.075 × n
```

### Operational Reality Detection

Phone transcripts may contain range values with explanations:
```
"turnaround_standard_days": "10-12 (system migration delays)"
```

These are preserved alongside stated policy:
```json
{
  "stated_policy": {"standard": 7, "urgent_hours": 48},
  "operational_reality": {
    "standard": {"min": 10, "max": 12},
    "standard_cause": "system migration delays"
  }
}
```

### Context Fields

Fields named `note`, `notes`, `denial_reason`, or `denial_reasons` are collected into `payer_context` rather than reconciled - they provide operational intelligence without needing conflict resolution.

## Project Structure

```
reconciliation_v2/
├── discovery/
│   ├── schema.py          # Schema discovery from extracted JSON
│   └── field_family.py    # Field family detection via patterns
├── pipeline/
│   ├── constants.py       # Authority weights, context fields
│   ├── value_collection.py # Collect values per field
│   ├── supersession.py    # Apply 3 supersession triggers
│   ├── scoring.py         # Freshness, authority, corroboration
│   ├── reconcile.py       # Main reconciliation logic
│   └── report.py          # Markdown report generation
├── tests/
│   └── test_reconciliation.py  # 26 tests covering all components
└── main.py                # CLI entry point
```

## Key Design Decisions

1. **No hardcoded field/payer names**: All logic is pattern-based
2. **Deterministic scoring**: No randomness, fully reproducible
3. **Explicit supersession**: Clear audit trail for deprecated values
4. **Dual-value preservation**: Stated policy AND operational reality both kept
5. **Data-driven drug selection**: Picks drug with most fresh mentions in high-signal sources

## Test Coverage

```
pytest reconciliation_v2/tests/ -v
```

Tests cover:
- Schema discovery (payer detection, nested fields, metadata)
- Field family detection (supersession pairs, policy updates, qualifiers)
- Supersession triggers (old pairs, policy dates)
- Scoring primitives (freshness decay, authority, corroboration, confidence floor)
- Operational reality detection
- Drug selection (data-driven, fallback, override)
- Integration tests (end-to-end reconciliation for all payers)

## Output Format

Each payer produces:
- `{payer}_reconciled.json`: Machine-readable reconciled data
- `{payer}_report.md`: Human-readable report with audit trail

## Future Improvements

- **Confidence calibration**: Tune scoring weights based on ground truth
- **Source reliability tracking**: Learn which sources are historically accurate
- **Temporal patterns**: Detect seasonal variations in turnaround times
- **Cross-payer learning**: Transfer insights between similar payers

## Architectures Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| Pure LLM | Handles ambiguity well | Non-deterministic, expensive | Rejected |
| Pure rules | Fast, deterministic | Brittle, requires maintenance | Rejected |
| **LLM Bookends** | Best of both | Requires careful boundary design | **Selected** |
| Graph-based | Natural for relationships | Overkill for current scale | Future consideration |
