"""NAV calculation engine."""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd

from etl.config import AppConfig
from etl.database import DatabaseManager

logger = logging.getLogger(__name__)


class NAVCalculator:
    """Calculates Net Asset Value and related metrics."""

    def __init__(self, config: AppConfig, db: DatabaseManager) -> None:
        self.config = config
        self.db = db

    def calculate_nav(self, fund_id: int, as_of_date: date) -> dict[str, float]:
        """Calculate NAV from holdings and cash positions."""
        holdings_query = """
            SELECT SUM(h.market_value) as total_holdings
            FROM holdings h
            WHERE h.fund_id = :fid AND h.as_of_date = :dt
        """
        cash_query = """
            SELECT cash_balance FROM cash_positions
            WHERE fund_id = :fid AND as_of_date = :dt
        """
        shares_query = """
            SELECT shares_outstanding FROM nav_history
            WHERE fund_id = :fid
            ORDER BY nav_date DESC LIMIT 1
        """
        params = {"fid": fund_id, "dt": as_of_date.isoformat()}

        holdings = self.db.execute_query(holdings_query, params)
        cash = self.db.execute_query(cash_query, params)
        shares = self.db.execute_query(shares_query, {"fid": fund_id})

        total_holdings = float(holdings["total_holdings"].iloc[0]) if not holdings.empty and holdings["total_holdings"].iloc[0] else 0
        cash_balance = float(cash["cash_balance"].iloc[0]) if not cash.empty else 0
        shares_out = int(shares["shares_outstanding"].iloc[0]) if not shares.empty else 1

        total_nav = total_holdings + cash_balance
        nav_per_share = total_nav / shares_out if shares_out else 0

        return {
            "total_nav": round(total_nav, 2),
            "nav_per_share": round(nav_per_share, 6),
            "shares_outstanding": shares_out,
            "total_holdings": round(total_holdings, 2),
            "cash_balance": round(cash_balance, 2),
        }

    def calculate_daily_return(self, fund_id: int, as_of_date: date) -> float | None:
        """Calculate daily return from NAV history."""
        query = """
            SELECT nav_per_share, nav_date FROM nav_history
            WHERE fund_id = :fid AND nav_date <= :dt
            ORDER BY nav_date DESC LIMIT 2
        """
        result = self.db.execute_query(query, {"fid": fund_id, "dt": as_of_date.isoformat()})
        if len(result) < 2:
            return None
        current = float(result["nav_per_share"].iloc[0])
        previous = float(result["nav_per_share"].iloc[1])
        return (current - previous) / previous if previous else 0

    def calculate_tracking_error(
        self, fund_id: int, start_date: date, end_date: date, window: int = 20
    ) -> float:
        """Calculate rolling tracking error vs benchmark."""
        query = """
            SELECT daily_return, benchmark_return FROM nav_history
            WHERE fund_id = :fid AND nav_date BETWEEN :start AND :end
            ORDER BY nav_date
        """
        result = self.db.execute_query(
            query,
            {"fid": fund_id, "start": start_date.isoformat(), "end": end_date.isoformat()},
        )
        if result.empty:
            return 0.0
        excess = result["daily_return"] - result["benchmark_return"]
        if len(excess) < window:
            return float(excess.std())
        return float(excess.rolling(window).std().iloc[-1])

    def update_daily_pricing(self, as_of_date: date) -> pd.DataFrame:
        """Recalculate and update daily pricing records."""
        funds = self.db.execute_query("SELECT fund_id, ticker FROM funds")
        records = []

        for _, fund in funds.iterrows():
            nav = self.calculate_nav(int(fund["fund_id"]), as_of_date)
            official_query = """
                SELECT official_nav FROM daily_pricing
                WHERE fund_id = :fid AND pricing_date = :dt
            """
            official = self.db.execute_query(
                official_query,
                {"fid": int(fund["fund_id"]), "dt": as_of_date.isoformat()},
            )
            official_nav = (
                float(official["official_nav"].iloc[0])
                if not official.empty
                else nav["nav_per_share"]
            )
            calculated = nav["nav_per_share"]
            variance_bps = (official_nav - calculated) / calculated * 10000 if calculated else 0

            records.append({
                "fund_id": int(fund["fund_id"]),
                "ticker": fund["ticker"],
                "pricing_date": as_of_date.isoformat(),
                "official_nav": official_nav,
                "calculated_nav": calculated,
                "nav_variance_bps": round(variance_bps, 4),
                "total_nav": nav["total_nav"],
            })

        return pd.DataFrame(records)
