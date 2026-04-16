"""Source data models."""

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Type of source document."""

    PROVIDER_MANUAL = "provider_manual"
    PHONE_TRANSCRIPT = "phone_transcript"
    WEB_PAGE = "web_page"
    DENIAL_LETTER = "denial_letter"


class SourceRecord(BaseModel):
    """A single source record with metadata."""

    source_id: str
    source_type: SourceType
    source_name: str
    source_date: date
    retrieved_date: date
    data: dict[str, Any] = Field(default_factory=dict)

    @property
    def age_days(self) -> int:
        """Days since source date."""
        from datetime import datetime

        return (datetime.now().date() - self.source_date).days

    @property
    def authority_weight(self) -> float:
        """Base authority weight for this source type."""
        weights = {
            SourceType.DENIAL_LETTER: 1.5,
            SourceType.PHONE_TRANSCRIPT: 1.3,
            SourceType.WEB_PAGE: 1.0,
            SourceType.PROVIDER_MANUAL: 0.7,
        }
        return weights[self.source_type]


class PayerData(BaseModel):
    """Full payer data with all sources."""

    payer: str
    sources: list[SourceRecord]
