#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from app.services.salary_sources.aggregator import probe_salary_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe salary sources for LARI salary module research.")
    parser.add_argument("--role", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--year", required=True, type=int)
    args = parser.parse_args()

    response = probe_salary_sources(args.role, args.region, args.year)
    print(json.dumps(response.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
