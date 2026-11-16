"""ICP scoring engine."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Callable

import dns.exception
import dns.resolver
import yaml

from .models import Lead, ScoredLead

MXLookup = Callable[[str], "bool | None"]


def dns_mx_lookup(domain: str, resolver: Any = None, timeout: float = 3.0) -> bool | None:
    """Ask DNS whether ``domain`` can receive mail.

    Returns True when the domain publishes a usable MX record, or has no MX
    but does have an A/AAAA record (the implicit MX of RFC 5321 section 5.1).
    Returns False for NXDOMAIN, for a null MX (RFC 7505: a single MX of
    preference 0 pointing at the root) and for a domain with no MX and no
    address. Returns None when the lookup itself failed (timeout, no
    reachable nameserver), so callers can tell "unknown" from "no".
    """
    if resolver is None:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = timeout
    try:
        answer = resolver.resolve(domain, "MX")
    except dns.resolver.NXDOMAIN:
        return False
    except dns.resolver.NoAnswer:
        return _has_address(resolver, domain)
    except dns.exception.DNSException:
        return None
    records = list(answer)
    if not records:
        return _has_address(resolver, domain)
    if len(records) == 1 and records[0].preference == 0 and str(records[0].exchange) == ".":
        return False
    return True


def _has_address(resolver: Any, domain: str) -> bool | None:
    failed = False
    for rdtype in ("A", "AAAA"):
        try:
            if list(resolver.resolve(domain, rdtype)):
                return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            continue
        except dns.exception.DNSException:
            failed = True
    return None if failed else False


class MXChecker:
    """Live MX check with a per-domain cache, so a list with 500 leads at
    the same company costs one DNS query, not 500."""

    def __init__(self, lookup: MXLookup | None = None, timeout: float = 3.0) -> None:
        self._lookup = lookup or (lambda d: dns_mx_lookup(d, timeout=timeout))
        self._cache: dict[str, bool | None] = {}

    def has_mx(self, domain: str) -> bool | None:
        domain = domain.strip().lower().rstrip(".")
        if not domain:
            return False
        if domain not in self._cache:
            self._cache[domain] = self._lookup(domain)
        return self._cache[domain]


def _email_shape_ok(email: str) -> bool:
    return bool(email and "@" in email and "." in email.rsplit("@", 1)[1])

@dataclass
class Rule:
    field: str
    weight: int
    contains: list[str] | None = None
    equals: str | None = None
    between: tuple[int, int] | None = None
    has_valid_mx: bool | None = None
    name: str | None = None

    def matches(self, lead: Lead, mx: MXChecker | None = None) -> bool:
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
            if not _email_shape_ok(lead.email):
                return False
            if mx is None:
                # offline mode: the email shape is all we check.
                return True
            # an unknown result (lookup failed) earns no points.
            return mx.has_mx(lead.email.rsplit("@", 1)[1]) is True
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
    mx_checker: MXChecker | None = dc_field(default=None, repr=False, compare=False)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ICP":
        data = yaml.safe_load(Path(path).read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ICP":
        rules = [_parse_rule(r) for r in data.get("rules", [])]
        verdicts = data.get("verdicts", {}) or {}
        mx_checker = None
        if data.get("mx_lookup"):
            mx_checker = MXChecker(timeout=float(data.get("mx_timeout", 3.0)))
        return cls(
            name=data.get("name", "default ICP"),
            rules=rules,
            hot_threshold=int(verdicts.get("hot", 70)),
            warm_threshold=int(verdicts.get("warm", 40)),
            mx_checker=mx_checker,
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
        if rule.matches(lead, icp.mx_checker):
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
