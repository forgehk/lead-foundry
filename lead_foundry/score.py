"""ICP scoring engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import Lead, ScoredLead

@dataclass
class Rule:
    field: str
    weight: int
    contains: list[str] | None = None
    equals: str | None = None
    between: tuple[int, int] | None = None
    has_valid_mx: bool | None = None
    name: str | None = None

    def matches(self, lead: Lead) -> bool:
        val = _field_value(lead, self.field)
        if self.contains is not None:
            if val is None:
                return False
            s = str(val).lower()
            return any(c.lower() in s for c in self.contains)
        if self.equals is not None:
            return str(val).strip().lower() == str(self.equals).strip().lower()
        if self.between is not None:
            try:
                num = int(val) if val is not None and val != "" else None
            except (TypeError, ValueError):
                return False
            if num is None:
                return False
            lo, hi = self.between
            return lo <= num <= hi
        if self.has_valid_mx is True:
            # we don't actually do a live MX lookup; just check email shape.
            return bool(lead.email and "@" in lead.email and "." in lead.email.rsplit("@", 1)[1])
        return False

    @property
    def label(self) -> str:
        return self.name or f"{self.field}/{self._op()}"

    def _op(self) -> str:
        if self.contains is not None:
            return f"contains:{','.join(self.contains)}"
        if self.equals is not None:
            return f"eq:{self.equals}"
        if self.between is not None:
            return f"in:{self.between[0]}-{self.between[1]}"
        if self.has_valid_mx is True:
            return "valid_mx"
        return "?"

@dataclass
class ICP:
    name: str
    rules: list[Rule]
    hot_threshold: int = 70
    warm_threshold: int = 40

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ICP":
        data = yaml.safe_load(Path(path).read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ICP":
        rules = [_parse_rule(r) for r in data.get("rules", [])]
        verdicts = data.get("verdicts", {}) or {}
        return cls(
            name=data.get("name", "default ICP"),
            rules=rules,
            hot_threshold=int(verdicts.get("hot", 70)),
            warm_threshold=int(verdicts.get("warm", 40)),
        )

def _parse_rule(data: dict[str, Any]) -> Rule:
    between = data.get("between")
    return Rule(
        field=data["field"],
        weight=int(data["weight"]),
        contains=data.get("contains"),
        equals=data.get("equals"),
        between=(int(between[0]), int(between[1])) if between else None,
        has_valid_mx=data.get("has_valid_mx"),
        name=data.get("name"),
    )

def _field_value(lead: Lead, field: str) -> Any:
    if hasattr(lead, field):
        return getattr(lead, field)
    return lead.extras.get(field)

def score_one(lead: Lead, icp: ICP) -> ScoredLead:
    total = 0
    matched: list[str] = []
    for rule in icp.rules:
        if rule.matches(lead):
            total += rule.weight
            matched.append(rule.label)
    total = max(0, min(100, total))
    if total >= icp.hot_threshold:
        verdict = "hot"
    elif total >= icp.warm_threshold:
        verdict = "warm"
    else:
        verdict = "cold"
    return ScoredLead(lead=lead, score=total, verdict=verdict, matched_rules=matched)

def score_all(leads: list[Lead], icp: ICP) -> list[ScoredLead]:
    return sorted(
        (score_one(l, icp) for l in leads),
        key=lambda sl: sl.score,
        reverse=True,
    )
