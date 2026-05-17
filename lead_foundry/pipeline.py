"""Top-level pipeline: csv in, scored csv out."""

from __future__ import annotations

import csv
from dataclasses import fields
from pathlib import Path
from typing import Callable, Iterable

from .dedupe import dedupe_by_domain
from .models import Lead, ScoredLead
from .normalize import normalize_lead
from .score import ICP, score_all

Enricher = Callable[[list[Lead]], list[Lead]]

class Pipeline:
    """End-to-end CSV ingest → normalize → enrich → dedupe → score → CSV out."""

    def __init__(self, enricher: Enricher | None = None) -> None:
        self.enricher = enricher

    def run(
        self,
        csv_in: str | Path,
        icp_path: str | Path | None = None,
        icp: ICP | None = None,
    ) -> list[ScoredLead]:
        if icp is None:
            if icp_path is None:
                raise ValueError("must provide either icp= or icp_path=")
            icp = ICP.from_yaml(icp_path)
        leads = list(load_csv(csv_in))
        leads = [normalize_lead(l) for l in leads]
        if self.enricher is not None:
            leads = self.enricher(leads)
        leads = dedupe_by_domain(leads)
        return score_all(leads, icp)

# field aliases so users can throw any roughly-CSV shape at us.
ALIASES: dict[str, list[str]] = {
    "first_name":   ["first_name", "first", "fname", "given_name", "firstname"],
    "last_name":    ["last_name", "last", "lname", "surname", "lastname"],
    "email":        ["email", "email_address", "e-mail", "mail"],
    "phone":        ["phone", "phone_number", "tel", "telephone", "mobile", "cell"],
    "title":        ["title", "job_title", "role", "position"],
    "company":      ["company", "company_name", "organization", "org"],
    "domain":       ["domain", "company_domain"],
    "website":      ["website", "url", "homepage", "site"],
    "industry":     ["industry", "vertical", "sector"],
    "company_size": ["company_size", "employees", "headcount", "size"],
    "country":      ["country", "country_code", "nation"],
}

KNOWN_FIELDS = {f.name for f in fields(Lead)}

def _canonical(header: str) -> str | None:
    h = header.strip().lower().replace(" ", "_").replace("-", "_")
    for canonical, names in ALIASES.items():
        if h in names:
            return canonical
    if h in KNOWN_FIELDS:
        return h
    return None

def load_csv(path: str | Path) -> Iterable[Lead]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header_map = {
            raw: _canonical(raw) for raw in (reader.fieldnames or [])
        }
        for row in reader:
            kwargs: dict = {}
            extras: dict = {}
            for raw, val in row.items():
                if raw is None:
                    continue
                canon = header_map.get(raw)
                if canon is None:
                    if val:
                        extras[raw.strip()] = val.strip() if isinstance(val, str) else val
                    continue
                v = val.strip() if isinstance(val, str) else val
                if canon == "company_size" and v:
                    try:
                        v = int(v)
                    except (TypeError, ValueError):
                        v = None
                if v == "":
                    continue
                kwargs[canon] = v
            yield Lead(extras=extras, **kwargs)

def write_csv(scored: list[ScoredLead], path: str | Path) -> None:
    if not scored:
        Path(path).write_text("")
        return
    keys = [f.name for f in fields(Lead) if f.name != "extras"] + [
        "score", "verdict", "matched_rules"
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for sl in scored:
            row = {k: getattr(sl.lead, k, "") for k in keys if hasattr(sl.lead, k)}
            row["score"] = sl.score
            row["verdict"] = sl.verdict
            row["matched_rules"] = ";".join(sl.matched_rules)
            writer.writerow(row)
