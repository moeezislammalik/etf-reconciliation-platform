"""Market data ETL loader."""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from etl.config import AppConfig
from etl.database import DatabaseManager

logger = logging.getLogger(__name__)


class MarketDataLoader:
    """Loads and validates daily market price data."""

    def __init__(self, config: AppConfig, db: DatabaseManager) -> None:
        self.config = config
        self.db = db

    def load_daily_prices(self, as_of_date: date, source_file: str | None = None) -> int:
        """Import daily market prices from CSV or database."""
        if source_file:
            df = pd.read_csv(source_file)
            df["price_date"] = as_of_date.isoformat()
            count = self.db.insert_dataframe(df, "market_prices", if_exists="append")
            logger.info("Loaded %d prices from %s", count, source_file)
            return count

        query = """
            SELECT mp.*, s.ticker
            FROM market_prices mp
            JOIN securities s ON mp.security_id = s.security_id
            WHERE mp.price_date = :as_of_date
        """
        result = self.db.execute_query(query, {"as_of_date": as_of_date.isoformat()})
        logger.info("Retrieved %d prices for %s", len(result), as_of_date)
        return len(result)

    def get_price(self, security_id: int, as_of_date: date) -> float | None:
        """Get closing price for a security on a given date."""
        query = """
            SELECT close_price FROM market_prices
            WHERE security_id = :sid AND price_date = :dt
        """
        result = self.db.execute_query(query, {"sid": security_id, "dt": as_of_date.isoformat()})
        if result.empty:
            return None
        return float(result["close_price"].iloc[0])

    def detect_missing_prices(self, as_of_date: date) -> pd.DataFrame:
        """Find holdings without corresponding market prices."""
        query = """
            SELECT DISTINCT s.security_id, s.ticker, s.security_name, h.fund_id
            FROM holdings h
            JOIN securities s ON h.security_id = s.security_id
            LEFT JOIN market_prices mp ON s.security_id = mp.security_id
                AND mp.price_date = :as_of_date
            WHERE h.as_of_date = :as_of_date AND mp.price_id IS NULL
        """
        return self.db.execute_query(query, {"as_of_date": as_of_date.isoformat()})

    def detect_price_anomalies(self, as_of_date: date, threshold: float = 0.05) -> pd.DataFrame:
        """Detect securities with abnormal price movements."""
        query = """
            SELECT
                s.ticker,
                s.security_name,
                mp_t.close_price AS today_price,
                mp_y.close_price AS yesterday_price,
                (mp_t.close_price - mp_y.close_price) / mp_y.close_price AS price_change
            FROM market_prices mp_t
            JOIN securities s ON mp_t.security_id = s.security_id
            JOIN market_prices mp_y ON mp_t.security_id = mp_y.security_id
            WHERE mp_t.price_date = :as_of_date
              AND mp_y.price_date = (
                  SELECT MAX(price_date) FROM market_prices
                  WHERE security_id = mp_t.security_id AND price_date < :as_of_date
              )
        """
        df = self.db.execute_query(query, {"as_of_date": as_of_date.isoformat()})
        if df.empty:
            return df
        return df[df["price_change"].abs() > threshold]
