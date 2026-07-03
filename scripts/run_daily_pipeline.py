#!/usr/bin/env python3
"""Run the daily ETF operations pipeline."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.pipeline import DailyPipeline


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run daily ETF operations pipeline")
    parser.add_argument("--date", type=str, default="2024-12-31", help="As-of date")
    args = parser.parse_args()

    as_of = date.fromisoformat(args.date)
    pipeline = DailyPipeline()
    results = pipeline.run(as_of)

    print(f"\n{'='*60}")
    print(f"Pipeline Status: {results['status']}")
    print(f"Date: {results['date']}")
    print(f"{'='*60}")

    for step, data in results.get("steps", {}).items():
        print(f"\n{step.upper()}:")
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    print(f"  {k}:")
                    for k2, v2 in v.items():
                        print(f"    {k2}: {v2}")
                else:
                    print(f"  {k}: {v}")
        else:
            print(f"  {data}")


if __name__ == "__main__":
    main()
