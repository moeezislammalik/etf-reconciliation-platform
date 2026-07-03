#!/usr/bin/env python3
"""Export star schema CSV files for Power BI import."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from etl.config import load_config
from etl.database import DatabaseManager

EXPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "exports" / "powerbi"


def export_table(db: DatabaseManager, query: str, filename: str) -> None:
    df = db.execute_query(query)
    filepath = EXPORT_DIR / filename
    df.to_csv(filepath, index=False)
    print(f"  Exported {filename}: {len(df):,} rows")


def main() -> None:
    config = load_config()
    db = DatabaseManager(config)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("Exporting Power BI star schema tables...")

    exports = {
        "Dim_Fund.csv": "SELECT fund_id, ticker, fund_name, benchmark, asset_class, expense_ratio, aum_billions FROM funds",
        "Dim_Security.csv": "SELECT security_id, cusip, ticker, security_name, security_type, sector, country FROM securities",
        "Fact_NAV.csv": """
            SELECT n.fund_id, n.nav_date, n.nav_per_share, n.total_nav,
                   n.shares_outstanding, n.daily_return, n.benchmark_return, n.tracking_error
            FROM nav_history n
        """,
        "Fact_Holdings.csv": """
            SELECT fund_id, security_id, as_of_date, quantity, market_value, cost_basis
            FROM holdings
        """,
        "Fact_Trades.csv": """
            SELECT trade_id, fund_id, security_id, trade_date, settlement_date,
                   side, quantity, price, gross_amount, net_amount, trade_status, broker
            FROM trades
        """,
        "Fact_Settlements.csv": """
            SELECT settlement_id, trade_id, fund_id, settlement_date,
                   expected_amount, actual_amount, settlement_status, fail_reason
            FROM settlements
        """,
        "Fact_Exceptions.csv": """
            SELECT exception_id, fund_id, exception_type, severity, description,
                   status, as_of_date, detected_at
            FROM exceptions
        """,
        "Fact_Cash.csv": """
            SELECT fund_id, as_of_date, cash_balance, accrued_expenses,
                   pending_settlements, available_cash
            FROM cash_positions
        """,
        "Fact_PortfolioWeights.csv": """
            SELECT fund_id, security_id, as_of_date, weight_pct, target_weight, drift_bps
            FROM portfolio_weights
        """,
        "Fact_MarketPrices.csv": """
            SELECT security_id, price_date, open_price, high_price, low_price, close_price, volume
            FROM market_prices
        """,
        "Fact_DailyPricing.csv": """
            SELECT fund_id, pricing_date, official_nav, calculated_nav,
                   nav_variance_bps, pricing_status
            FROM daily_pricing
        """,
    }

    for filename, query in exports.items():
        export_table(db, query, filename)

    print(f"\nExport complete. Files saved to: {EXPORT_DIR}")


if __name__ == "__main__":
    main()
