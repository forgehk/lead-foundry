"""lead-foundry CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import Pipeline, load_csv, write_csv
from .score import ICP

def _build(csv_in: Path, icp_path: Path, out: Path) -> int:
    scored = Pipeline().run(csv_in, icp_path=icp_path)
    write_csv(scored, out)
    print(f"lead-foundry: {len(scored)} leads → {out}")
    counts: dict[str, int] = {}
    for sl in scored:
        counts[sl.verdict] = counts.get(sl.verdict, 0) + 1
    for verdict in ("hot", "warm", "cold"):
        if counts.get(verdict):
            print(f"  {verdict:<5}: {counts[verdict]}")
    return 0

def _inspect(csv_in: Path) -> int:
    leads = list(load_csv(csv_in))
    print(f"lead-foundry inspect: {csv_in}")
    print(f"  rows:         {len(leads)}")
    print(f"  with email:   {sum(1 for l in leads if l.email)}")
    print(f"  with phone:   {sum(1 for l in leads if l.phone)}")
    print(f"  with domain:  {sum(1 for l in leads if l.domain)}")
    print(f"  with title:   {sum(1 for l in leads if l.title)}")
    countries = {}
    for l in leads:
        if l.country:
            countries[l.country] = countries.get(l.country, 0) + 1
    if countries:
        print("  countries:    " + ", ".join(f"{k}={v}" for k, v in sorted(countries.items())))
    return 0

def _score(csv_in: Path, icp_path: Path, as_json: bool) -> int:
    icp = ICP.from_yaml(icp_path)
    leads = list(load_csv(csv_in))
    from .score import score_all
    scored = score_all(leads, icp)
    if as_json:
        print(json.dumps([sl.to_dict() for sl in scored], indent=2))
    else:
        for sl in scored:
            print(f"  {sl.verdict:<5} {sl.score:>3}  {sl.lead.full_name or sl.lead.email or sl.lead.domain}")
    return 0

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lead-foundry", description="Normalize/dedupe/score leads.")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Full pipeline: normalize, dedupe, score, write CSV.")
    b.add_argument("csv", type=Path)
    b.add_argument("--icp", type=Path, required=True)
    b.add_argument("--out", type=Path, default=Path("scored.csv"))

    i = sub.add_parser("inspect", help="Quick stats on a raw CSV.")
    i.add_argument("csv", type=Path)

    s = sub.add_parser("score", help="Score-only (assume already-normalized input).")
    s.add_argument("csv", type=Path)
    s.add_argument("--icp", type=Path, required=True)
    s.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "build":
        return _build(args.csv.resolve(), args.icp.resolve(), args.out.resolve())
    if args.command == "inspect":
        return _inspect(args.csv.resolve())
    if args.command == "score":
        return _score(args.csv.resolve(), args.icp.resolve(), args.json)
    return 1

if __name__ == "__main__":
    sys.exit(main())
