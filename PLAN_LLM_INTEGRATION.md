# Plan: LLM Integration + Bug Fixes

## Current State
- Pure deterministic pipeline: scoring formulas, pattern matching, regex
- Works well for structured conflicts but struggles with:
  - Semantic equivalence (is "phone" same as "phone_urgent_only"?)
  - Prose parsing (extracting requirements from drug notes)
  - Low-confidence tiebreaking

---

## PART 1: Bug Fixes (No LLM)

### 1.1 Fix Version Regex (~15 min)
**Problem:** Current regex matches false positives like 3-digit numbers or irrelevant patterns.
```python
# Current (too permissive)
r'^(.+?)[-_]?(20\d{2})$'  # Matches 4-digit year
r'^(.+?)[-_]?(\d{2})$'    # Matches 2-digit year (problematic)
```

**Fix:** Require explicit version patterns:
```python
# Stricter patterns:
# 1. 4-digit year: 2020-2029
r'^(.+?)[-_](202[0-9])$'

# 2. Explicit version prefix: v1, v2, V2025
r'^(.+?)[-_]?[vV](\d+)$'

# 3. Drop 2-digit year fallback entirely
```

**Files:** `supersession.py:extract_version_info()`

---

### 1.2 Fix Form-Code Raw-Text Validation (~20 min)
**Problem:** Pattern `r'\b[A-Z]{2,4}[-_]?(?:AUTH|MED|PA|FORM)?[-_]?\d{2,4}\b'` misses complex codes like "ANT-MED-PA-25".

**Current extraction:**
- Raw text: "ANT-MED-PA-25"
- Extracted: "MED-PA-25" (missing "ANT-")

**Fix:** More flexible form code pattern:
```python
# Capture alphanumeric codes with multiple segments
form_pattern = r'\b([A-Z]{2,5}(?:[-_][A-Z]{2,5})*[-_]\d{2,4})\b'
# Matches: ANT-MED-PA-25, HUM-AUTH-2026, AET-PA-2025
```

**Files:** `raw_text_validator.py:load_raw_text()`

---

### 1.3 Prefix-Compatibility Detection (~30 min)
**Problem:** "(800) 274-7767" and "(800) 274-7767, Option 1, Option 1" flagged as conflict when the second is just more specific.

**Current behavior:**
- Different string values → conflict
- Confidence penalty applied

**Fix:** Before marking conflict, check prefix compatibility:
```python
def values_are_prefix_compatible(val_a: str, val_b: str) -> bool:
    """Check if one value is a prefix/specificity refinement of another."""
    a_normalized = normalize_for_prefix(val_a)
    b_normalized = normalize_for_prefix(val_b)
    return a_normalized.startswith(b_normalized) or b_normalized.startswith(a_normalized)

# For phone fields specifically:
# - Extract base phone number
# - If base numbers match, prefer the more specific one
# - No conflict penalty, just specificity preference
```

**Files:** `canonicalize.py` (new function), `scoring.py` (check before corroboration penalty)

---

## PART 2: LLM Integration

### 2.1 Architecture Decision

**Approach:** LLM as optional enhancement layer, not replacement.
- Pipeline remains deterministic by default
- LLM called only for specific tasks where rules fail
- Results cached to avoid repeated calls
- Graceful degradation if LLM unavailable

```
┌─────────────────────────────────────────────────────────┐
│                    RECONCILIATION PIPELINE              │
├─────────────────────────────────────────────────────────┤
│  extracted_route_data.json                              │
│           ↓                                             │
│  ┌─────────────────────────────────────┐               │
│  │  DETERMINISTIC LAYER (existing)     │               │
│  │  - Field family detection           │               │
│  │  - Supersession triggers            │               │
│  │  - Scoring formula                  │               │
│  │  - Raw text validation              │               │
│  └─────────────────────────────────────┘               │
│           ↓                                             │
│  ┌─────────────────────────────────────┐               │
│  │  LLM ENHANCEMENT LAYER (new)        │               │
│  │  - Low-confidence tiebreaker        │               │
│  │  - Drug requirement extraction      │               │
│  │  - Semantic equivalence check       │               │
│  │  - Focus drug selection             │               │
│  └─────────────────────────────────────┘               │
│           ↓                                             │
│  best_route + conflicts                                 │
└─────────────────────────────────────────────────────────┘
```

---

### 2.2 LLM Task: Focus Drug Selection (~1 hr)

**Current:** Heuristic - count "fresh mentions" of drug names across sources.

**Problem:** Fails when denial letter mentions a different drug than manual emphasizes.

**LLM Approach:**
```python
def select_focus_drug_with_llm(
    denial_letter_text: str,
    drug_mentions: dict[str, list[str]],  # drug -> [sources]
    payer_name: str,
) -> tuple[str, str]:  # (drug_name, reasoning)
    """
    Ask LLM to select the most relevant focus drug.

    Prompt:
    - Here's a denial letter excerpt
    - Here are drugs mentioned across sources with context
    - Which drug should be the focus for this PA route?
    - Why?
    """
```

**Trigger:** Always run for focus drug selection (replaces heuristic).

**Files:** New `reconciliation_v2/llm/focus_drug.py`

---

### 2.3 LLM Task: Drug Requirement Extraction (~1.5 hr)

**Current:** Keyword matching in drug notes:
```python
if "specialist" in note_lower:
    fields["specialist_required"] = True
```

**Problem:** Misses payer-specific patterns:
- "HER2 testing documentation" → `her2_testing_required`
- "anti-TNF failure" → `anti_tnf_failure_docs_required`
- "CD20 positive" → `cd20_documentation_required`

**LLM Approach:**
```python
def extract_drug_requirements_with_llm(
    drug_name: str,
    all_notes: list[str],  # Notes from all sources
    payer_name: str,
) -> dict[str, Any]:
    """
    Ask LLM to extract structured requirements from prose notes.

    Prompt:
    - Here are all notes about {drug_name} from {payer_name}
    - Extract structured requirements:
      - specialist_required: bool
      - prior_treatment_failure_required: bool
      - specific_testing_required: list[str]
      - documentation_requirements: list[str]
      - auth_period_initial_months: int
      - auth_period_renewal_months: int
    """
```

**Trigger:** After deterministic extraction, if notes exist but structured fields are sparse.

**Files:** New `reconciliation_v2/llm/drug_requirements.py`

---

### 2.4 LLM Task: Low-Confidence Tiebreaker (~1 hr)

**Current:** When confidence < 0.5, we output the best-scoring value but flag uncertainty.

**Problem:** Sometimes the "lower scoring" value is actually correct (e.g., phone rep has stale info but scored higher due to recency).

**LLM Approach:**
```python
def llm_tiebreak_field(
    field_name: str,
    candidates: list[dict],  # [{value, source_type, source_date, context}]
    raw_text_excerpts: dict[str, str],  # source_id -> relevant excerpt
) -> tuple[Any, str, float]:  # (selected_value, reasoning, confidence_boost)
    """
    Ask LLM to evaluate conflicting values.

    Prompt:
    - Field: {field_name}
    - Candidates:
      - Source A (denial_letter, 2026-03-10): value X
      - Source B (phone_transcript, 2026-03-20): value Y
    - Raw text context: ...
    - Which is more likely correct and why?
    """
```

**Trigger:** When final confidence < 0.50 AND has_conflicts == True.

**Files:** New `reconciliation_v2/llm/tiebreaker.py`

---

### 2.5 LLM Task: Semantic Equivalence (~45 min)

**Current:** `canonicalize_for_equality()` uses normalization (lowercase, strip whitespace, sort lists).

**Problem:** Can't detect semantic equivalence:
- "fax, portal" vs "portal, fax" → handled by sorting
- "phone" vs "phone_status_only" → NOT handled
- "5 business days" vs "5" → NOT handled

**LLM Approach:**
```python
def are_semantically_equivalent(
    field_name: str,
    value_a: Any,
    value_b: Any,
) -> tuple[bool, str]:  # (equivalent, reasoning)
    """
    Ask LLM if two values are semantically equivalent.

    Only called when:
    - Canonical comparison says "different"
    - Values look similar (fuzzy match > 0.7)
    """
```

**Trigger:** In corroboration calculation, before penalizing for disagreement.

**Files:** New `reconciliation_v2/llm/semantic.py`, modify `scoring.py`

---

## PART 3: Implementation Order

### Phase 1: Bug Fixes (1 hour)
1. Fix version regex in `supersession.py`
2. Fix form-code pattern in `raw_text_validator.py`
3. Add prefix-compatibility check

### Phase 2: LLM Infrastructure (30 min)
1. Create `reconciliation_v2/llm/` module
2. Add LLM client abstraction (support Claude API)
3. Add caching layer for LLM responses
4. Add config for enable/disable LLM

### Phase 3: LLM Tasks (3 hours)
1. Focus drug selection (simplest, good test case)
2. Drug requirement extraction (highest value)
3. Low-confidence tiebreaker
4. Semantic equivalence (optional, can defer)

### Phase 4: Testing & Validation (1 hour)
1. Run all payers with LLM enabled
2. Compare outputs with/without LLM
3. Verify LLM improves low-confidence fields
4. Check for regressions

---

## Files to Create/Modify

**New Files:**
- `reconciliation_v2/llm/__init__.py`
- `reconciliation_v2/llm/client.py` - LLM abstraction
- `reconciliation_v2/llm/focus_drug.py`
- `reconciliation_v2/llm/drug_requirements.py`
- `reconciliation_v2/llm/tiebreaker.py`
- `reconciliation_v2/llm/semantic.py` (optional)

**Modified Files:**
- `supersession.py` - fix version regex
- `raw_text_validator.py` - fix form code pattern
- `canonicalize.py` - add prefix compatibility
- `scoring.py` - integrate prefix check
- `reconcile.py` - integrate LLM calls
- `constants.py` - add LLM config flags

---

## Success Criteria

1. **Bug fixes:**
   - pa_form validation passes for BCBS (ANT-MED-PA-25)
   - phone_urgent shows as "specificity refinement" not conflict
   - No false version detections

2. **LLM integration:**
   - Focus drug matches denial letter subject when applicable
   - Drug requirements include payer-specific fields (her2_testing, etc.)
   - Low-confidence fields get LLM reasoning in decision_path
   - Pipeline still works with LLM disabled (graceful degradation)

3. **Performance:**
   - LLM calls cached per payer run
   - <5 LLM calls per payer (avoid over-reliance)
   - Total pipeline time <30s per payer with LLM
