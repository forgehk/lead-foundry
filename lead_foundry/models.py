"""Lead and ScoredLead dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class Lead:
    # Identity
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    title: str = ""

    # Company
    company: str = ""
    domain: str = ""
    website: str = ""
    industry: str = ""
    company_size: int | None = None
    country: str = ""

    # Free-form extras (enrichment fields land here)
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

@dataclass
class ScoredLead:
    lead: Lead
    score: int
    verdict: str       # 'hot' | 'warm' | 'cold'
    matched_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.lead.to_dict(),
            "score": self.score,
            "verdict": self.verdict,
            "matched_rules": self.matched_rules,
        }
