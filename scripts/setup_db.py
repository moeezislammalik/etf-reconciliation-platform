#!/usr/bin/env python3
"""Initialize database schema and configuration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.config import load_config
from etl.database import DatabaseManager


def main() -> None:
    config = load_config()
    db = DatabaseManager(config)
    print("Initializing database schema...")
    db.initialize_schema()
    print(f"Database ready: {config.database.connection_string}")

    tables = [
        "funds", "securities", "holdings", "trades", "market_prices",
        "nav_history", "settlements", "exceptions", "cash_positions",
        "portfolio_weights", "corporate_actions", "daily_pricing", "pipeline_runs",
    ]
    print("\nTable status:")
    for table in tables:
        exists = db.table_exists(table)
        count = db.get_table_count(table) if exists else 0
        status = f"{count:,} rows" if exists else "NOT FOUND"
        print(f"  {table:25s} {status}")


if __name__ == "__main__":
    main()
