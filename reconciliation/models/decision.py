"""Decision tracking models."""

from typing import Any

from pydantic import BaseModel, Field


class RuleFired(BaseModel):
    """A single rule that was applied."""

    rule_name: str
    description: str
    outcome: str
    metadata: dict = Field(default_factory=dict)


class DecisionPath(BaseModel):
    """Ordered list of rules that led to a decision."""

    rules: list[RuleFired] = Field(default_factory=list)

    def add(self, rule_name: str, description: str, outcome: str, **metadata):
        """Add a rule to the decision path."""
        self.rules.append(
            RuleFired(rule_name=rule_name, description=description, outcome=outcome, metadata=metadata)
        )

    def to_list(self) -> list[str]:
        """Convert to list of human-readable strings."""
        return [
            f"{r.rule_name}: {r.description} → {r.outcome}"
            for r in self.rules
        ]


class FieldReconciliation(BaseModel):
    """Reconciliation result for a single field."""

    field_name: str
    value: str | int | float | list | dict | None
    confidence: float = Field(ge=0.0, le=1.0)
    decision_path: list[str]
    contributing_sources: list[str]  # source_ids
    superseded_sources: list[str] = Field(default_factory=list)  # source_ids
    reasoning: str | None = None  # LLM-generated explanation
    conflicts_detected: bool = False
    raw_values: dict[str, Any] = Field(default_factory=dict)  # source_id -> value


class PayerReconciliation(BaseModel):
    """Complete reconciliation for a payer."""

    payer: str
    fields: dict[str, FieldReconciliation]
    summary: dict = Field(default_factory=dict)
