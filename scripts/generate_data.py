#!/usr/bin/env python3
"""Seed the database with one year of ETF trading activity and market data."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.config import load_config
from etl.data_generator import SyntheticDataGenerator
from etl.database import DatabaseManager


def main() -> None:
    config = load_config()
    db = DatabaseManager(config)

    print("=" * 60)
    print("ETF Synthetic Data Generator")
    print(f"Period: {config.data_start_date} to {config.data_end_date}")
    print("=" * 60)

    print("\nInitializing schema...")
    db.initialize_schema()

    print("\nLoading historical data (this may take a few minutes)...")
    start = time.time()
    generator = SyntheticDataGenerator(config, db)
    counts = generator.generate_all()
    elapsed = time.time() - start

    print(f"\nGeneration complete in {elapsed:.1f}s")
    print("\nRecord counts:")
    total = 0
    for table, count in counts.items():
        print(f"  {table:25s} {count:>10,}")
        total += count
    print(f"  {'TOTAL':25s} {total:>10,}")

    print("\nDatabase summary:")
    for table in counts:
        db_count = db.get_table_count(table)
        print(f"  {table:25s} {db_count:>10,} (verified)")


if __name__ == "__main__":
    main()
