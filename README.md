# lead-foundry

> Turn a CSV of raw lead data into a scored, deduped, outreach-ready list. Pluggable enrichment, configurable ICP scoring, no SaaS lock-in.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)]() [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What it does

Most lead-gen pipelines are 90% the same boring work: clean phone numbers, normalize emails, dedupe by company, score each lead against your ICP, export. SaaS tools want $200/mo to do this poorly. `lead-foundry` does it locally in a few hundred lines of Python.

```bash
# in:  raw_leads.csv  (messy CSV from any source)
# out: scored.csv     (deduped, normalized, ICP-scored)

lead-foundry build raw_leads.csv \
  --icp icp.yaml \
  --out scored.csv
```

It also has a pluggable **enrichment** hook so you can wire in whatever data source you want (Apify, Clearbit, custom scraper, your CRM) without rewriting the pipeline.

---

## Why I built this

While running DarkForge AI's automation work, I kept rebuilding the same lead-prep pipeline for every project: clean phones to E.164, normalize emails, parse company domains, dedupe by domain, score against the project's ICP, export. `lead-foundry` consolidates that pipeline into one config-driven CLI.

It's also a good "tell me about your favorite project" interview answer because it covers:

- **Data normalization** at multiple field levels (phone, email, name, domain)
- **Pluggable architecture** — enrichment is an interface, not a hardcoded provider
- **Dedup with conflict resolution** — what do you do when two rows describe the same company with conflicting data?
- **Scoring & ranking** — weighted multi-factor scoring against a configurable ICP
- **Testable design** — every stage has unit tests against fixtures

---

## Quick start

```bash
pip install lead-foundry

# inspect what's in a raw file
lead-foundry inspect raw_leads.csv

# run the full pipeline
lead-foundry build raw_leads.csv --icp icp.yaml --out scored.csv

# score-only mode (assumes already-normalized input)
lead-foundry score normalized.csv --icp icp.yaml
```

---

## ICP config (`icp.yaml`)

```yaml
# Ideal Customer Profile — what we want to score against.
name: "DarkForge ICP — wellness DTC"

# Each rule contributes points if it matches.
rules:
  - field: industry
    contains: ["wellness", "supplements", "fitness"]
    weight: 30

  - field: company_size
    between: [10, 200]
    weight: 25

  - field: country
    equals: "US"
    weight: 15

  - field: title
    contains: ["founder", "ceo", "head of marketing", "ecom"]
    weight: 20

  - field: email
    has_valid_mx: true
    weight: 10

# Score thresholds
verdicts:
  hot: 70       # >= 70 score = HOT
  warm: 40      # >= 40 score = WARM
  cold: 0       # everything else
```

---

## Pipeline stages

```
┌──────────────┐    ┌───────────┐    ┌──────────┐    ┌───────┐    ┌────────┐
│   raw csv    │───▶│ normalize │───▶│  enrich  │───▶│ score │───▶│  out   │
│              │    │  phone,   │    │ optional │    │  ICP  │    │  csv   │
│              │    │  email,   │    │  hook    │    │       │    │        │
│              │    │  company  │    │          │    │       │    │        │
└──────────────┘    └─────┬─────┘    └──────────┘    └───────┘    └────────┘
                          │
                          ▼
                    ┌──────────┐
                    │  dedupe  │
                    │ by domain│
                    └──────────┘
```

Each stage is a function with a typed signature; you can run them independently for testing or skip whichever ones you don't need.

---

## Plugging in your enrichment

```python
from lead_foundry import Lead, Pipeline

def my_enricher(leads: list[Lead]) -> list[Lead]:
    for lead in leads:
        # call Apify / Clearbit / your CRM here
        lead.company_size = lookup_company_size(lead.domain)
        lead.industry = lookup_industry(lead.domain)
    return leads

pipeline = Pipeline(enricher=my_enricher)
scored = pipeline.run("raw_leads.csv", icp_path="icp.yaml")
```

The default `pipeline.run` runs without an enricher — useful when you already have enriched data and just want normalize/score/dedupe.

---

## Roadmap

- [x] Phone normalization (E.164)
- [x] Email normalization + simple MX sanity
- [x] Domain extraction from email + website
- [x] Dedupe by company domain
- [x] Configurable ICP YAML
- [x] Weighted multi-factor scoring
- [x] CSV in / CSV out
- [x] JSON output mode
- [ ] Apify provider plugin
- [ ] Email deliverability check via real MX lookup
- [ ] Asynchronous enrichment with rate-limit awareness
- [ ] Optional LLM-based industry classification

---

## License

[MIT](LICENSE)

---

*Built by [@forgehk](https://github.com/forgehk) — [DarkForge AI](https://darkforgeai.com)*
