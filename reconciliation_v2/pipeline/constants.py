"""Pipeline constants - authority weights, decay parameters, etc."""

# Authority weights based on enforcement proximity:
# - denial_letter: Direct evidence of current policy enforcement. When a payer
#   denies a claim, they cite the exact policy being applied right now.
# - phone_transcript: Real-time rep knowledge, but subject to individual variance
#   and reps sometimes being wrong about policy details.
# - web_page and provider_manual: Equalized at 0.50 each. They're roughly equally
#   authoritative for general fields, and freshness should be the tiebreaker
#   between them. This lets more recent sources win when authority is similar.
AUTHORITY_WEIGHTS = {
    "denial_letter": 1.0,
    "phone_transcript": 0.75,
    "web_page": 0.50,
    "provider_manual": 0.50,
}

# Exponential decay half-life in days
# After half_life days, a source has 50% freshness
# After 2*half_life days, 25% freshness, etc.
DEFAULT_FRESHNESS_HALF_LIFE_DAYS = 180

# Field output filter thresholds
MIN_SOURCES_FOR_OUTPUT = 2  # Field appears in >= 2 sources
MAX_DAYS_FOR_SINGLE_SOURCE = 90  # Or field is from source within 90 days

# Patterns that indicate operational reality vs stated policy
OPERATIONAL_REALITY_PATTERNS = [
    r"\(.*(?:migration|transition|delays?|temporary|currently|during).*\)",
    r"\d+-\d+\s*(?:days?|hours?)",  # Ranges like "10-12 days"
]

# Payer-level context fields (not reconciliation targets)
# These are collected as context, not reconciled as conflicts
PAYER_CONTEXT_FIELDS = {
    "system_migration_in_progress",
    "phone_experience_note",
}

# Fields that should be collected (all values preserved) rather than reconciled
# These are operational context - useful info but not submission instructions
# NOTE: This does NOT apply to *_note suffixed fields (like portal_note) - those
# are correctly handled as siblings to their base field
COLLECTED_CONTEXT_FIELDS = {
    "note",
    "notes",
    "denial_reason",  # Case-specific evidence, not general route field
    "denial_reasons",  # Plural variant
}
