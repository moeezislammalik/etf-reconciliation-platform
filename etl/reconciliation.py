"""Automated reconciliation engine for ETF operations."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pandas as pd

from etl.config import AppConfig
from etl.database import DatabaseManager
from etl.market_data_loader import MarketDataLoader
from etl.nav_calculator import NAVCalculator

logger = logging.getLogger(__name__)


class ReconciliationEngine:
    """Detects and records reconciliation exceptions across ETF operations."""

    EXCEPTION_TYPES = [
        "TRADE_QUANTITY_MISMATCH",
        "SETTLEMENT_MISMATCH",
        "MARKET_VALUE_MISMATCH",
        "MISSING_SECURITY",
        "DUPLICATE_TRADE",
        "INCORRECT_NAV",
        "INCORRECT_WEIGHT_ALLOCATION",
        "PRICE_VARIANCE",
        "CASH_IMBALANCE",
        "MISSING_PRICE",
        "FAILED_SETTLEMENT",
        "TRACKING_ERROR_BREACH",
    ]

    def __init__(self, config: AppConfig, db: DatabaseManager) -> None:
        self.config = config
        self.db = db
        self.market_loader = MarketDataLoader(config, db)
        self.nav_calculator = NAVCalculator(config, db)
        self.exceptions: list[dict[str, Any]] = []

    def run_full_reconciliation(self, as_of_date: date) -> pd.DataFrame:
        """Execute all reconciliation checks for a given date."""
        logger.info("Running full reconciliation for %s", as_of_date)
        self.exceptions = []

        checks = [
            self.check_failed_settlements,
            self.check_missing_prices,
            self.check_price_anomalies,
            self.check_cash_breaks,
            self.check_nav_discrepancies,
            self.check_weight_drift,
            self.check_duplicate_trades,
            self.check_trade_settlement_mismatch,
            self.check_market_value_mismatch,
            self.check_tracking_error,
        ]

        for check in checks:
            try:
                check(as_of_date)
            except Exception as e:
                logger.error("Check %s failed: %s", check.__name__, e)

        if self.exceptions:
            self._persist_exceptions()

        logger.info("Reconciliation complete: %d exceptions found", len(self.exceptions))
        return pd.DataFrame(self.exceptions)

    def _create_exception(
        self,
        exception_type: str,
        description: str,
        severity: str,
        as_of_date: date,
        fund_id: int | None = None,
        reference_id: str | None = None,
        reference_table: str | None = None,
    ) -> None:
        self.exceptions.append({
            "fund_id": fund_id,
            "exception_type": exception_type,
            "severity": severity,
            "description": description,
            "reference_id": reference_id,
            "reference_table": reference_table,
            "as_of_date": as_of_date.isoformat(),
            "status": "OPEN",
            "detected_at": datetime.now().isoformat(),
        })

    def _persist_exceptions(self) -> None:
        self.db.bulk_insert(self.exceptions, "exceptions")

    def check_failed_settlements(self, as_of_date: date) -> None:
        query = """
            SELECT st.*, f.ticker, t.trade_id
            FROM settlements st
            JOIN trades t ON st.trade_id = t.trade_id
            JOIN funds f ON st.fund_id = f.fund_id
            WHERE st.settlement_status = 'FAILED'
              AND st.settlement_date = :dt
        """
        failed = self.db.execute_query(query, {"dt": as_of_date.isoformat()})
        for _, row in failed.iterrows():
            self._create_exception(
                "FAILED_SETTLEMENT",
                f"Settlement failed for trade {row['trade_id']} ({row['ticker']}): {row.get('fail_reason', 'Unknown')}",
                "HIGH",
                as_of_date,
                fund_id=int(row["fund_id"]),
                reference_id=str(row["trade_id"]),
                reference_table="settlements",
            )

    def check_missing_prices(self, as_of_date: date) -> None:
        missing = self.market_loader.detect_missing_prices(as_of_date)
        for _, row in missing.iterrows():
            self._create_exception(
                "MISSING_PRICE",
                f"Missing market price for {row['ticker']} ({row['security_name']}) on {as_of_date}",
                "MEDIUM",
                as_of_date,
                fund_id=int(row["fund_id"]) if pd.notna(row.get("fund_id")) else None,
                reference_id=str(row["security_id"]),
                reference_table="market_prices",
            )

    def check_price_anomalies(self, as_of_date: date) -> None:
        threshold = self.config.reconciliation.price_variance_threshold
        anomalies = self.market_loader.detect_price_anomalies(as_of_date, threshold)
        for _, row in anomalies.iterrows():
            pct = float(row["price_change"]) * 100
            severity = "CRITICAL" if abs(pct) > 10 else "HIGH" if abs(pct) > 7 else "MEDIUM"
            self._create_exception(
                "PRICE_VARIANCE",
                f"Price anomaly for {row['ticker']}: {pct:.2f}% change (${row['yesterday_price']:.2f} -> ${row['today_price']:.2f})",
                severity,
                as_of_date,
                reference_id=row["ticker"],
                reference_table="market_prices",
            )

    def check_cash_breaks(self, as_of_date: date) -> None:
        threshold = self.config.reconciliation.cash_break_threshold
        query = """
            SELECT cp.*, f.ticker
            FROM cash_positions cp
            JOIN funds f ON cp.fund_id = f.fund_id
            WHERE cp.as_of_date = :dt
        """
        cash = self.db.execute_query(query, {"dt": as_of_date.isoformat()})
        for _, row in cash.iterrows():
            expected = float(row["cash_balance"]) - float(row["pending_settlements"]) - float(row["accrued_expenses"])
            actual = float(row["available_cash"])
            break_amount = actual - expected
            if abs(break_amount) > threshold:
                self._create_exception(
                    "CASH_IMBALANCE",
                    f"Cash break of ${break_amount:,.2f} for {row['ticker']} (Expected: ${expected:,.2f}, Actual: ${actual:,.2f})",
                    "HIGH" if abs(break_amount) > threshold * 5 else "MEDIUM",
                    as_of_date,
                    fund_id=int(row["fund_id"]),
                    reference_table="cash_positions",
                )

    def check_nav_discrepancies(self, as_of_date: date) -> None:
        tolerance = self.config.reconciliation.nav_tolerance_bps
        pricing = self.nav_calculator.update_daily_pricing(as_of_date)
        for _, row in pricing.iterrows():
            if abs(row["nav_variance_bps"]) > tolerance:
                self._create_exception(
                    "INCORRECT_NAV",
                    f"NAV variance of {row['nav_variance_bps']:.2f} bps for {row['ticker']} "
                    f"(Official: ${row['official_nav']:.4f}, Calculated: ${row['calculated_nav']:.4f})",
                    "CRITICAL" if abs(row["nav_variance_bps"]) > tolerance * 3 else "HIGH",
                    as_of_date,
                    fund_id=int(row["fund_id"]),
                    reference_table="daily_pricing",
                )

    def check_weight_drift(self, as_of_date: date) -> None:
        query = """
            SELECT pw.*, f.ticker, s.ticker as sec_ticker
            FROM portfolio_weights pw
            JOIN funds f ON pw.fund_id = f.fund_id
            JOIN securities s ON pw.security_id = s.security_id
            WHERE pw.as_of_date = :dt AND ABS(pw.drift_bps) > 50
        """
        drifts = self.db.execute_query(query, {"dt": as_of_date.isoformat()})
        for _, row in drifts.iterrows():
            self._create_exception(
                "INCORRECT_WEIGHT_ALLOCATION",
                f"Weight drift of {row['drift_bps']:.1f} bps for {row['sec_ticker']} in {row['ticker']} "
                f"(Actual: {row['weight_pct']:.2f}%, Target: {row['target_weight']:.2f}%)",
                "MEDIUM" if abs(row["drift_bps"]) < 100 else "HIGH",
                as_of_date,
                fund_id=int(row["fund_id"]),
                reference_id=row["sec_ticker"],
                reference_table="portfolio_weights",
            )

    def check_duplicate_trades(self, as_of_date: date) -> None:
        query = """
            SELECT t1.trade_id as id1, t2.trade_id as id2, f.ticker, s.ticker as sec_ticker,
                   t1.quantity, t1.price
            FROM trades t1
            JOIN trades t2 ON t1.fund_id = t2.fund_id
                AND t1.security_id = t2.security_id
                AND t1.trade_date = t2.trade_date
                AND t1.side = t2.side
                AND t1.quantity = t2.quantity
                AND t1.trade_id < t2.trade_id
            JOIN funds f ON t1.fund_id = f.fund_id
            JOIN securities s ON t1.security_id = s.security_id
            WHERE t1.trade_date = :dt
        """
        dupes = self.db.execute_query(query, {"dt": as_of_date.isoformat()})
        for _, row in dupes.iterrows():
            self._create_exception(
                "DUPLICATE_TRADE",
                f"Duplicate trade detected: {row['id1']} and {row['id2']} for {row['sec_ticker']} in {row['ticker']}",
                "HIGH",
                as_of_date,
                reference_id=f"{row['id1']},{row['id2']}",
                reference_table="trades",
            )

    def check_trade_settlement_mismatch(self, as_of_date: date) -> None:
        query = """
            SELECT t.trade_id, t.net_amount, st.expected_amount, st.actual_amount,
                   f.ticker, s.ticker as sec_ticker, t.fund_id
            FROM trades t
            JOIN settlements st ON t.trade_id = st.trade_id
            JOIN funds f ON t.fund_id = f.fund_id
            JOIN securities s ON t.security_id = s.security_id
            WHERE st.settlement_date = :dt
              AND ABS(t.net_amount - st.expected_amount) > 0.01
        """
        mismatches = self.db.execute_query(query, {"dt": as_of_date.isoformat()})
        for _, row in mismatches.iterrows():
            self._create_exception(
                "SETTLEMENT_MISMATCH",
                f"Settlement amount mismatch for trade {row['trade_id']} ({row['sec_ticker']}): "
                f"Trade ${row['net_amount']:,.2f} vs Expected ${row['expected_amount']:,.2f}",
                "HIGH",
                as_of_date,
                fund_id=int(row["fund_id"]),
                reference_id=str(row["trade_id"]),
                reference_table="settlements",
            )

    def check_market_value_mismatch(self, as_of_date: date) -> None:
        query = """
            SELECT h.holding_id, h.market_value, h.quantity, mp.close_price,
                   h.quantity * mp.close_price as calc_mv,
                   f.ticker, s.ticker as sec_ticker, h.fund_id
            FROM holdings h
            JOIN funds f ON h.fund_id = f.fund_id
            JOIN securities s ON h.security_id = s.security_id
            JOIN market_prices mp ON h.security_id = mp.security_id AND h.as_of_date = mp.price_date
            WHERE h.as_of_date = :dt
              AND ABS(h.market_value - h.quantity * mp.close_price) > 1.0
        """
        mismatches = self.db.execute_query(query, {"dt": as_of_date.isoformat()})
        for _, row in mismatches.iterrows():
            variance = float(row["market_value"]) - float(row["calc_mv"])
            self._create_exception(
                "MARKET_VALUE_MISMATCH",
                f"Market value mismatch for {row['sec_ticker']} in {row['ticker']}: "
                f"Recorded ${row['market_value']:,.2f} vs Calculated ${row['calc_mv']:,.2f} (variance: ${variance:,.2f})",
                "MEDIUM",
                as_of_date,
                fund_id=int(row["fund_id"]),
                reference_id=str(row["holding_id"]),
                reference_table="holdings",
            )

    def check_tracking_error(self, as_of_date: date) -> None:
        threshold = self.config.reconciliation.tracking_error_threshold
        funds = self.db.execute_query("SELECT fund_id, ticker FROM funds")
        start = date(as_of_date.year, as_of_date.month, 1)

        for _, fund in funds.iterrows():
            te = self.nav_calculator.calculate_tracking_error(
                int(fund["fund_id"]), start, as_of_date
            )
            if te > threshold:
                self._create_exception(
                    "TRACKING_ERROR_BREACH",
                    f"Tracking error of {te:.4f} exceeds threshold {threshold} for {fund['ticker']}",
                    "MEDIUM",
                    as_of_date,
                    fund_id=int(fund["fund_id"]),
                    reference_table="nav_history",
                )

    def get_exception_summary(self, as_of_date: date) -> pd.DataFrame:
        """Get summary of exceptions by type and severity."""
        query = """
            SELECT exception_type, severity, status, COUNT(*) as count
            FROM exceptions
            WHERE as_of_date = :dt
            GROUP BY exception_type, severity, status
            ORDER BY count DESC
        """
        return self.db.execute_query(query, {"dt": as_of_date.isoformat()})
