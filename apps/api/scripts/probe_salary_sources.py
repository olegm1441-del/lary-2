#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.salary_sources.aggregator import probe_salary_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe salary sources for LARI salary module research.")
    parser.add_argument("--role")
    parser.add_argument("--region")
    parser.add_argument("--year", type=int)
    parser.add_argument("--batch", help="Path to JSON array of {role, region, year} probe cases.")
    args = parser.parse_args()

    if args.batch:
        report = []
        cases = json.loads(Path(args.batch).read_text(encoding="utf-8"))
        for case in cases:
            role = str(case.get("role") or "")
            region = str(case.get("region") or "")
            year = int(case.get("year") or args.year or 2025)
            try:
                response = probe_salary_sources(role, region, year)
                recommended = response.recommended
                report.append(
                    {
                        "role": role,
                        "region": region,
                        "year": year,
                        "source_statuses": {item.source: item.status for item in response.results},
                        "recommended_source": recommended.source if recommended else None,
                        "salary_value": recommended.salary_value if recommended else None,
                        "source_url": recommended.source_url if recommended else None,
                        "matched_role": recommended.matched_role if recommended else None,
                        "warnings": response.warnings,
                    }
                )
            except Exception as exc:  # noqa: BLE001 - batch report must survive one broken source/case.
                report.append({"role": role, "region": region, "year": year, "error": exc.__class__.__name__})
        print(json.dumps({"cases": report}, ensure_ascii=False, indent=2))
        return

    if not args.role or not args.region or not args.year:
        parser.error("--role, --region and --year are required unless --batch is used")

    response = probe_salary_sources(args.role, args.region, args.year)
    print(json.dumps(response.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
