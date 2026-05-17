"""Dedupe leads by company domain.

When two leads share a domain, prefer the row with the most complete data
(more non-empty fields wins, ties broken by longer email + earlier in list).
"""

from __future__ import annotations

from dataclasses import asdict

from .models import Lead

def completeness(lead: Lead) -> int:
    """Count non-empty scalar fields."""
    d = asdict(lead)
    d.pop("extras", None)
    return sum(1 for v in d.values() if v not in (None, "", 0))

def dedupe_by_domain(leads: list[Lead]) -> list[Lead]:
    """Return one lead per domain. Empty-domain leads pass through untouched."""
    by_domain: dict[str, Lead] = {}
    no_domain: list[Lead] = []
    for lead in leads:
        if not lead.domain:
            no_domain.append(lead)
            continue
        existing = by_domain.get(lead.domain)
        if existing is None:
            by_domain[lead.domain] = lead
            continue
        # keep the more-complete one; merge extras
        better = lead if completeness(lead) > completeness(existing) else existing
        loser = existing if better is lead else lead
        merged_extras = {**loser.extras, **better.extras}
        better.extras = merged_extras
        by_domain[lead.domain] = better
    return list(by_domain.values()) + no_domain
