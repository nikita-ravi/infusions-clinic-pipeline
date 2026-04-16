"""Phase 7: LLM reasoning writer."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from reconciliation.models.decision import FieldReconciliation

# Cache directory for LLM responses
CACHE_DIR = Path(".cache/reasoning")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def generate_reasoning(
    field_rec: FieldReconciliation,
    payer: str,
    api_key: str | None = None,
) -> str:
    """
    Generate human-readable reasoning for a field reconciliation.

    Uses Anthropic Haiku with prompt caching to minimize costs.
    Results are cached to disk by input hash for free re-runs.

    Args:
        field_rec: The field reconciliation result
        payer: Payer name
        api_key: Anthropic API key (or from env)

    Returns:
        2-3 sentence explanation of the reconciliation decision
    """
    # Check disk cache first
    cache_key = _generate_cache_key(field_rec, payer)
    cached_result = _read_cache(cache_key)
    if cached_result:
        return cached_result

    # Generate prompt
    prompt = _build_prompt(field_rec, payer)

    # Call Anthropic API
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            # Fallback: return decision path as text if no API key
            return " → ".join(field_rec.decision_path[:3])

    client = Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-haiku-4-20250514",
            max_tokens=200,
            temperature=0.3,  # Low temperature for consistency
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        reasoning = response.content[0].text.strip()

        # Cache result to disk
        _write_cache(cache_key, reasoning)

        return reasoning

    except Exception as e:
        # Fallback on error
        return f"Unable to generate reasoning: {str(e)}"


def _build_prompt(field_rec: FieldReconciliation, payer: str) -> str:
    """Build the prompt for reasoning generation."""
    field_name_readable = field_rec.field_name.replace("_", " ").title()

    # Build context about conflicts
    conflict_context = ""
    if field_rec.conflicts_detected and field_rec.raw_values:
        conflict_context = "\n\nConflicting values from sources:\n"
        for source_id, value in field_rec.raw_values.items():
            marker = "✓" if source_id in field_rec.contributing_sources else "✗"
            conflict_context += f"- {marker} {source_id}: {_format_value(value)}\n"

    # Build decision path summary (last 3 rules)
    key_decisions = field_rec.decision_path[-3:] if len(field_rec.decision_path) > 3 else field_rec.decision_path

    prompt = f"""You are explaining a prior authorization route reconciliation decision to an operations team member.

Payer: {payer}
Field: {field_name_readable}
Selected Value: {_format_value(field_rec.value)}
Confidence: {field_rec.confidence:.2f}

Key Decision Steps:
{chr(10).join(f"- {step}" for step in key_decisions)}
{conflict_context}
Write 2-3 clear, concise sentences explaining:
1. What value was selected and why
2. If there were conflicts, how they were resolved
3. Any caveats or warnings (if confidence < 0.7)

Tone: Factual, helpful, no jargon. Focus on what the ops person needs to know.
Do not use phrases like "I selected" or "I determined" - use passive voice like "was selected" or "based on".
"""

    return prompt


def _format_value(value: Any) -> str:
    """Format value for display in prompt."""
    if value is None:
        return "None"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return " | ".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


def _generate_cache_key(field_rec: FieldReconciliation, payer: str) -> str:
    """Generate a cache key from the reconciliation inputs."""
    # Create a deterministic hash from the inputs
    cache_input = {
        "payer": payer,
        "field_name": field_rec.field_name,
        "value": str(field_rec.value),
        "confidence": round(field_rec.confidence, 2),
        "decision_path": field_rec.decision_path,
        "conflicts_detected": field_rec.conflicts_detected,
        "raw_values": {k: str(v) for k, v in field_rec.raw_values.items()} if field_rec.raw_values else {},
    }

    cache_str = json.dumps(cache_input, sort_keys=True)
    return hashlib.sha256(cache_str.encode()).hexdigest()


def _read_cache(cache_key: str) -> str | None:
    """Read cached reasoning from disk."""
    cache_file = CACHE_DIR / f"{cache_key}.txt"
    if cache_file.exists():
        return cache_file.read_text()
    return None


def _write_cache(cache_key: str, reasoning: str) -> None:
    """Write reasoning to disk cache."""
    cache_file = CACHE_DIR / f"{cache_key}.txt"
    cache_file.write_text(reasoning)
