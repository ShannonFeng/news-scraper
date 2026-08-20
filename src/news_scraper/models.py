from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    url: str
    source: str
    published_at: datetime | None = None
    summary: str = ""
    content: str = ""

    @property
    def published_at_iso(self) -> str | None:
        if self.published_at is None:
            return None
        return self.published_at.astimezone(UTC).isoformat()


@dataclass(frozen=True)
class Classification:
    important: bool
    company_name: str
    company_description: str
    coverage_match: str
    ownership_assessment: str
    location_assessment: str
    disqualifiers: list[str]
    attractive_metrics: list[str]
    confidence: float
    summary: str
    sms: str
    reasoning: str
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Classification:
        return cls(
            important=bool(payload["important"]),
            company_name=str(payload["company_name"]),
            company_description=str(payload["company_description"]),
            coverage_match=str(payload["coverage_match"]),
            ownership_assessment=str(payload["ownership_assessment"]),
            location_assessment=str(payload["location_assessment"]),
            disqualifiers=[str(item) for item in payload["disqualifiers"]],
            attractive_metrics=[str(item) for item in payload["attractive_metrics"]],
            confidence=float(payload["confidence"]),
            summary=str(payload["summary"]),
            sms=str(payload["sms"]),
            reasoning=str(payload["reasoning"]),
            raw=payload,
        )
