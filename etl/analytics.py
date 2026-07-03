"""Advanced portfolio analytics engine."""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd

from etl.config import AppConfig
from etl.database import DatabaseManager

logger = logging.getLogger(__name__)


class PortfolioAnalytics:
    """Calculates portfolio metrics, risk measures, and attribution."""

    def __init__(self, config: AppConfig, db: DatabaseManager) -> None:
        self.config = config
        self.db = db
        self.risk_free_rate = config.analytics.risk_free_rate
        self.trading_days = config.analytics.trading_days_per_year

    def get_fund_returns(self, fund_id: int, start_date: date, end_date: date) -> pd.Series:
        query = """
            SELECT nav_date, daily_return FROM nav_history
            WHERE fund_id = :fid AND nav_date BETWEEN :start AND :end
            ORDER BY nav_date
        """
        df = self.db.execute_query(
            query,
            {"fid": fund_id, "start": start_date.isoformat(), "end": end_date.isoformat()},
        )
        if df.empty:
            return pd.Series(dtype=float)
        return df.set_index("nav_date")["daily_return"]

    def calculate_portfolio_return(self, fund_id: int, start_date: date, end_date: date) -> float:
        returns = self.get_fund_returns(fund_id, start_date, end_date)
        if returns.empty:
            return 0.0
        return float((1 + returns).prod() - 1)

    def calculate_volatility(self, fund_id: int, start_date: date, end_date: date) -> float:
        returns = self.get_fund_returns(fund_id, start_date, end_date)
        if len(returns) < 2:
            return 0.0
        return float(returns.std() * np.sqrt(self.trading_days))

    def calculate_sharpe_ratio(self, fund_id: int, start_date: date, end_date: date) -> float:
        returns = self.get_fund_returns(fund_id, start_date, end_date)
        if len(returns) < 2:
            return 0.0
        daily_rf = self.risk_free_rate / self.trading_days
        excess = returns - daily_rf
        std = excess.std()
        if std == 0 or np.isnan(std):
            return 0.0
        return float(excess.mean() / std * np.sqrt(self.trading_days))

    def calculate_tracking_error(self, fund_id: int, start_date: date, end_date: date) -> float:
        query = """
            SELECT daily_return, benchmark_return FROM nav_history
            WHERE fund_id = :fid AND nav_date BETWEEN :start AND :end
            ORDER BY nav_date
        """
        df = self.db.execute_query(
            query,
            {"fid": fund_id, "start": start_date.isoformat(), "end": end_date.isoformat()},
        )
        if len(df) < 2:
            return 0.0
        excess = df["daily_return"] - df["benchmark_return"]
        return float(excess.std() * np.sqrt(self.trading_days))

    def get_sector_allocation(self, fund_id: int, as_of_date: date) -> pd.DataFrame:
        query = """
            SELECT s.sector, SUM(h.market_value) as market_value
            FROM holdings h
            JOIN securities s ON h.security_id = s.security_id
            WHERE h.fund_id = :fid AND h.as_of_date = :dt
            GROUP BY s.sector
            ORDER BY market_value DESC
        """
        df = self.db.execute_query(query, {"fid": fund_id, "dt": as_of_date.isoformat()})
        if not df.empty:
            total = df["market_value"].sum()
            df["weight_pct"] = df["market_value"] / total * 100
        return df

    def get_asset_allocation(self, fund_id: int, as_of_date: date) -> pd.DataFrame:
        query = """
            SELECT s.security_type, SUM(h.market_value) as market_value
            FROM holdings h
            JOIN securities s ON h.security_id = s.security_id
            WHERE h.fund_id = :fid AND h.as_of_date = :dt
            GROUP BY s.security_type
            ORDER BY market_value DESC
        """
        df = self.db.execute_query(query, {"fid": fund_id, "dt": as_of_date.isoformat()})
        if not df.empty:
            total = df["market_value"].sum()
            df["weight_pct"] = df["market_value"] / total * 100
        return df

    def get_largest_holdings(self, fund_id: int, as_of_date: date, top_n: int = 10) -> pd.DataFrame:
        query = """
            SELECT s.ticker, s.security_name, s.sector,
                   h.quantity, h.market_value, pw.weight_pct
            FROM holdings h
            JOIN securities s ON h.security_id = s.security_id
            LEFT JOIN portfolio_weights pw ON h.fund_id = pw.fund_id
                AND h.security_id = pw.security_id AND h.as_of_date = pw.as_of_date
            WHERE h.fund_id = :fid AND h.as_of_date = :dt
            ORDER BY h.market_value DESC
            LIMIT :top_n
        """
        return self.db.execute_query(
            query, {"fid": fund_id, "dt": as_of_date.isoformat(), "top_n": top_n}
        )

    def calculate_concentration_risk(self, fund_id: int, as_of_date: date) -> dict[str, float]:
        query = """
            SELECT weight_pct FROM portfolio_weights
            WHERE fund_id = :fid AND as_of_date = :dt
            ORDER BY weight_pct DESC
        """
        weights = self.db.execute_query(query, {"fid": fund_id, "dt": as_of_date.isoformat()})
        if weights.empty:
            return {"top5_concentration": 0, "top10_concentration": 0, "herfindahl_index": 0}

        w = weights["weight_pct"] / 100
        return {
            "top5_concentration": float(w.head(5).sum() * 100),
            "top10_concentration": float(w.head(10).sum() * 100),
            "herfindahl_index": float((w ** 2).sum()),
        }

    def get_cash_exposure(self, fund_id: int, as_of_date: date) -> dict[str, float]:
        query = """
            SELECT cp.cash_balance, cp.available_cash, n.total_nav
            FROM cash_positions cp
            JOIN nav_history n ON cp.fund_id = n.fund_id AND cp.as_of_date = n.nav_date
            WHERE cp.fund_id = :fid AND cp.as_of_date = :dt
        """
        result = self.db.execute_query(query, {"fid": fund_id, "dt": as_of_date.isoformat()})
        if result.empty:
            return {"cash_balance": 0, "cash_pct": 0, "available_cash": 0}
        row = result.iloc[0]
        total_nav = float(row["total_nav"])
        cash = float(row["cash_balance"])
        return {
            "cash_balance": cash,
            "available_cash": float(row["available_cash"]),
            "cash_pct": cash / total_nav * 100 if total_nav else 0,
        }

    def calculate_turnover(self, fund_id: int, start_date: date, end_date: date) -> float:
        query = """
            SELECT SUM(net_amount) as total_traded FROM trades
            WHERE fund_id = :fid AND trade_date BETWEEN :start AND :end
        """
        trades = self.db.execute_query(
            query,
            {"fid": fund_id, "start": start_date.isoformat(), "end": end_date.isoformat()},
        )
        nav_query = """
            SELECT AVG(total_nav) as avg_nav FROM nav_history
            WHERE fund_id = :fid AND nav_date BETWEEN :start AND :end
        """
        nav = self.db.execute_query(
            nav_query,
            {"fid": fund_id, "start": start_date.isoformat(), "end": end_date.isoformat()},
        )
        if trades.empty or nav.empty or not nav["avg_nav"].iloc[0]:
            return 0.0
        return float(trades["total_traded"].iloc[0] / nav["avg_nav"].iloc[0] / 2 * 100)

    def performance_attribution(self, fund_id: int, as_of_date: date) -> pd.DataFrame:
        query = """
            SELECT s.sector, s.ticker, pw.weight_pct,
                   mp_t.close_price, mp_y.close_price,
                   (mp_t.close_price - mp_y.close_price) / mp_y.close_price as security_return
            FROM portfolio_weights pw
            JOIN securities s ON pw.security_id = s.security_id
            JOIN market_prices mp_t ON s.security_id = mp_t.security_id AND mp_t.price_date = :dt
            LEFT JOIN market_prices mp_y ON s.security_id = mp_y.security_id
                AND mp_y.price_date = (
                    SELECT MAX(price_date) FROM market_prices
                    WHERE security_id = s.security_id AND price_date < :dt
                )
            WHERE pw.fund_id = :fid AND pw.as_of_date = :dt
        """
        df = self.db.execute_query(query, {"fid": fund_id, "dt": as_of_date.isoformat()})
        if df.empty:
            return df
        df["contribution"] = df["weight_pct"] / 100 * df["security_return"].fillna(0)
        sector_attr = df.groupby("sector").agg(
            weight=("weight_pct", "sum"),
            contribution=("contribution", "sum"),
        ).reset_index()
        return sector_attr.sort_values("contribution", ascending=False)

    def get_fund_metrics_summary(self, fund_id: int, as_of_date: date) -> dict[str, float]:
        start = date(as_of_date.year, 1, 1)
        return {
            "portfolio_return_ytd": self.calculate_portfolio_return(fund_id, start, as_of_date),
            "volatility": self.calculate_volatility(fund_id, start, as_of_date),
            "sharpe_ratio": self.calculate_sharpe_ratio(fund_id, start, as_of_date),
            "tracking_error": self.calculate_tracking_error(fund_id, start, as_of_date),
            "turnover": self.calculate_turnover(fund_id, start, as_of_date),
            **self.calculate_concentration_risk(fund_id, as_of_date),
            **self.get_cash_exposure(fund_id, as_of_date),
        }
