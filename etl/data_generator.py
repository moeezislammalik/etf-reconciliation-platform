"""Historical data loader for ETF operations seed data."""

from __future__ import annotations

import logging
import random
import string
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from etl.config import AppConfig
from etl.database import DatabaseManager

logger = logging.getLogger(__name__)

# S&P 500-style securities reference data
SP500_SECURITIES = [
    ("AAPL", "Apple Inc.", "Technology", "Common Stock"),
    ("MSFT", "Microsoft Corporation", "Technology", "Common Stock"),
    ("AMZN", "Amazon.com Inc.", "Consumer Discretionary", "Common Stock"),
    ("NVDA", "NVIDIA Corporation", "Technology", "Common Stock"),
    ("GOOGL", "Alphabet Inc. Class A", "Communication Services", "Common Stock"),
    ("META", "Meta Platforms Inc.", "Communication Services", "Common Stock"),
    ("BRK.B", "Berkshire Hathaway Inc.", "Financials", "Common Stock"),
    ("JPM", "JPMorgan Chase & Co.", "Financials", "Common Stock"),
    ("V", "Visa Inc.", "Financials", "Common Stock"),
    ("UNH", "UnitedHealth Group Inc.", "Healthcare", "Common Stock"),
    ("JNJ", "Johnson & Johnson", "Healthcare", "Common Stock"),
    ("XOM", "Exxon Mobil Corporation", "Energy", "Common Stock"),
    ("PG", "Procter & Gamble Co.", "Consumer Staples", "Common Stock"),
    ("MA", "Mastercard Inc.", "Financials", "Common Stock"),
    ("HD", "Home Depot Inc.", "Consumer Discretionary", "Common Stock"),
    ("CVX", "Chevron Corporation", "Energy", "Common Stock"),
    ("MRK", "Merck & Co. Inc.", "Healthcare", "Common Stock"),
    ("ABBV", "AbbVie Inc.", "Healthcare", "Common Stock"),
    ("PEP", "PepsiCo Inc.", "Consumer Staples", "Common Stock"),
    ("KO", "Coca-Cola Company", "Consumer Staples", "Common Stock"),
    ("COST", "Costco Wholesale Corp.", "Consumer Staples", "Common Stock"),
    ("AVGO", "Broadcom Inc.", "Technology", "Common Stock"),
    ("WMT", "Walmart Inc.", "Consumer Staples", "Common Stock"),
    ("MCD", "McDonald's Corporation", "Consumer Discretionary", "Common Stock"),
    ("CSCO", "Cisco Systems Inc.", "Technology", "Common Stock"),
    ("TMO", "Thermo Fisher Scientific", "Healthcare", "Common Stock"),
    ("ACN", "Accenture plc", "Technology", "Common Stock"),
    ("ABT", "Abbott Laboratories", "Healthcare", "Common Stock"),
    ("DHR", "Danaher Corporation", "Healthcare", "Common Stock"),
    ("NEE", "NextEra Energy Inc.", "Utilities", "Common Stock"),
    ("LIN", "Linde plc", "Materials", "Common Stock"),
    ("TXN", "Texas Instruments Inc.", "Technology", "Common Stock"),
    ("PM", "Philip Morris International", "Consumer Staples", "Common Stock"),
    ("UNP", "Union Pacific Corporation", "Industrials", "Common Stock"),
    ("RTX", "RTX Corporation", "Industrials", "Common Stock"),
    ("HON", "Honeywell International", "Industrials", "Common Stock"),
    ("QCOM", "QUALCOMM Inc.", "Technology", "Common Stock"),
    ("LOW", "Lowe's Companies Inc.", "Consumer Discretionary", "Common Stock"),
    ("INTU", "Intuit Inc.", "Technology", "Common Stock"),
    ("SPGI", "S&P Global Inc.", "Financials", "Common Stock"),
    ("BA", "Boeing Company", "Industrials", "Common Stock"),
    ("CAT", "Caterpillar Inc.", "Industrials", "Common Stock"),
    ("GE", "General Electric Company", "Industrials", "Common Stock"),
    ("IBM", "International Business Machines", "Technology", "Common Stock"),
    ("GS", "Goldman Sachs Group", "Financials", "Common Stock"),
    ("MS", "Morgan Stanley", "Financials", "Common Stock"),
    ("BLK", "BlackRock Inc.", "Financials", "Common Stock"),
    ("SCHW", "Charles Schwab Corp.", "Financials", "Common Stock"),
    ("AXP", "American Express Co.", "Financials", "Common Stock"),
    ("DE", "Deere & Company", "Industrials", "Common Stock"),
]

BOND_SECURITIES = [
    ("US912828Z", "US Treasury 2Y Note", "Government Bond"),
    ("US912810SW", "US Treasury 5Y Note", "Government Bond"),
    ("US912810TU", "US Treasury 10Y Note", "Government Bond"),
    ("US912810TN", "US Treasury 30Y Bond", "Government Bond"),
    ("AAPL 3.45 2029", "Apple Inc. 3.45% 2029", "Corporate Bond"),
    ("MSFT 2.675 2030", "Microsoft 2.675% 2030", "Corporate Bond"),
    ("JPM 4.452 2034", "JPMorgan 4.452% 2034", "Corporate Bond"),
    ("AMZN 3.8 2028", "Amazon 3.8% 2028", "Corporate Bond"),
]

EM_SECURITIES = [
    ("TSM", "Taiwan Semiconductor", "Technology", "ADR"),
    ("BABA", "Alibaba Group", "Consumer Discretionary", "ADR"),
    ("PDD", "PDD Holdings", "Consumer Discretionary", "ADR"),
    ("VALE", "Vale S.A.", "Materials", "ADR"),
    ("ITUB", "Itau Unibanco", "Financials", "ADR"),
    ("NU", "Nu Holdings Ltd.", "Financials", "ADR"),
    ("INFY", "Infosys Limited", "Technology", "ADR"),
    ("SHEL", "Shell plc", "Energy", "ADR"),
]

SMALL_CAP_SECURITIES = [
    ("SMCI", "Super Micro Computer", "Technology", "Common Stock"),
    ("CELH", "Celsius Holdings", "Consumer Staples", "Common Stock"),
    ("DUOL", "Duolingo Inc.", "Technology", "Common Stock"),
    ("CAVA", "CAVA Group Inc.", "Consumer Discretionary", "Common Stock"),
    ("TOST", "Toast Inc.", "Technology", "Common Stock"),
    ("ONON", "On Holding AG", "Consumer Discretionary", "Common Stock"),
    ("ARMK", "Aramark", "Consumer Discretionary", "Common Stock"),
    ("WING", "Wingstop Inc.", "Consumer Discretionary", "Common Stock"),
]

BROKERS = ["Goldman Sachs", "Morgan Stanley", "JP Morgan", "Citadel Securities", "Virtu Financial"]


def _generate_cusip() -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=9))


def _business_days(start: date, end: date) -> list[date]:
    days = pd.bdate_range(start, end)
    return [d.date() for d in days]


class SyntheticDataGenerator:
    """Loads historical ETF operations data for one year."""

    def __init__(self, config: AppConfig, db: DatabaseManager) -> None:
        self.config = config
        self.db = db
        self.rng = np.random.default_rng(config.random_seed)
        random.seed(config.random_seed)
        self.start_date = date.fromisoformat(config.data_start_date)
        self.end_date = date.fromisoformat(config.data_end_date)
        self.trading_days = _business_days(self.start_date, self.end_date)
        self.fund_ids: dict[str, int] = {}
        self.security_ids: dict[str, int] = {}
        self.base_prices: dict[str, float] = {}

    def generate_all(self) -> dict[str, int]:
        """Run full data generation pipeline."""
        logger.info("Starting data load: %s to %s", self.start_date, self.end_date)
        counts = {}
        counts["funds"] = self._generate_funds()
        counts["securities"] = self._generate_securities()
        counts["market_prices"] = self._generate_market_prices()
        counts["holdings"] = self._generate_holdings()
        counts["portfolio_weights"] = self._generate_portfolio_weights()
        counts["trades"] = self._generate_trades()
        counts["settlements"] = self._generate_settlements()
        counts["nav_history"] = self._generate_nav_history()
        counts["cash_positions"] = self._generate_cash_positions()
        counts["corporate_actions"] = self._generate_corporate_actions()
        counts["daily_pricing"] = self._generate_daily_pricing()
        logger.info("Data generation complete: %s", counts)
        return counts

    def _generate_funds(self) -> int:
        records = []
        for fund in self.config.funds:
            records.append({
                "ticker": fund["ticker"],
                "fund_name": fund["name"],
                "benchmark": fund["benchmark"],
                "asset_class": fund["asset_class"],
                "inception_date": fund["inception_date"],
                "expense_ratio": fund["expense_ratio"],
                "aum_billions": fund["aum_billions"],
                "currency": "USD",
                "is_active": True,
            })
        df = pd.DataFrame(records)
        self.db.insert_dataframe(df, "funds", if_exists="append")
        result = self.db.execute_query("SELECT fund_id, ticker FROM funds")
        self.fund_ids = dict(zip(result["ticker"], result["fund_id"]))
        return len(records)

    def _get_securities_for_fund(self, ticker: str) -> list[tuple]:
        if ticker in ("IVV",):
            return SP500_SECURITIES[:40]
        if ticker in ("AGG", "TLT"):
            return [(s[0], s[1], "Fixed Income", s[2]) for s in BOND_SECURITIES]
        if ticker == "EEM":
            return EM_SECURITIES + SP500_SECURITIES[:10]
        if ticker == "IWM":
            return SMALL_CAP_SECURITIES + SP500_SECURITIES[:15]
        return SP500_SECURITIES[:30]

    def _generate_securities(self) -> int:
        all_secs: dict[str, tuple] = {}
        for ticker in self.fund_ids:
            for sec in self._get_securities_for_fund(ticker):
                if sec[0] not in all_secs:
                    all_secs[sec[0]] = sec

        records = []
        for ticker, (sym, name, sector, sec_type) in all_secs.items():
            base_price = self.rng.uniform(20, 500) if sec_type == "Common Stock" else self.rng.uniform(90, 110)
            self.base_prices[sym] = base_price
            records.append({
                "cusip": _generate_cusip(),
                "ticker": sym,
                "security_name": name,
                "security_type": sec_type,
                "sector": sector,
                "country": "USA" if sec_type != "ADR" else random.choice(["TWN", "CHN", "BRA", "IND"]),
                "currency": "USD",
                "is_active": True,
            })

        df = pd.DataFrame(records)
        self.db.insert_dataframe(df, "securities", if_exists="append")
        result = self.db.execute_query("SELECT security_id, ticker FROM securities")
        self.security_ids = dict(zip(result["ticker"], result["security_id"]))
        return len(records)

    def _generate_market_prices(self) -> int:
        records = []
        for sym, sec_id in self.security_ids.items():
            price = self.base_prices.get(sym, 100.0)
            for day in self.trading_days:
                daily_return = self.rng.normal(0.0003, 0.015)
                price = max(price * (1 + daily_return), 1.0)
                spread = price * self.rng.uniform(0.005, 0.02)
                records.append({
                    "security_id": sec_id,
                    "price_date": day.isoformat(),
                    "open_price": round(price - spread / 2, 4),
                    "high_price": round(price + spread, 4),
                    "low_price": round(price - spread, 4),
                    "close_price": round(price, 4),
                    "volume": int(self.rng.integers(100_000, 50_000_000)),
                    "source": random.choice(["BLOOMBERG", "REFINITIV", "ICE"]),
                })
        batch_size = 5000
        for i in range(0, len(records), batch_size):
            self.db.bulk_insert(records[i : i + batch_size], "market_prices")
        return len(records)

    def _generate_holdings(self) -> int:
        """Generate holdings with quantity continuity — market values float with prices."""
        records = []
        for fund_ticker, fund_id in self.fund_ids.items():
            fund_secs = self._get_securities_for_fund(fund_ticker)
            aum = next(f["aum_billions"] for f in self.config.funds if f["ticker"] == fund_ticker) * 1e9
            cash_pct = self.rng.uniform(0.01, 0.05)
            investable = aum * (1 - cash_pct)

            # Establish initial quantities on day 1; carry forward and reprice thereafter
            weights = self.rng.dirichlet(np.ones(len(fund_secs)))
            fund_quantities: dict[int, tuple[float, float]] = {}  # sec_id -> (qty, cost_basis)

            for day_idx, day in enumerate(self.trading_days):
                for idx, (sym, _, _, _) in enumerate(fund_secs):
                    if sym not in self.security_ids:
                        continue
                    sec_id = self.security_ids[sym]
                    price_row = self.db.execute_query(
                        "SELECT close_price FROM market_prices WHERE security_id = :sid AND price_date = :dt",
                        {"sid": sec_id, "dt": day.isoformat()},
                    )
                    if price_row.empty:
                        continue
                    price = float(price_row["close_price"].iloc[0])

                    if day_idx == 0:
                        target_mv = investable * weights[idx]
                        qty = round(target_mv / price, 2)
                        cost = round(target_mv * self.rng.uniform(0.92, 1.02), 2)
                        fund_quantities[sec_id] = (qty, cost)
                    else:
                        qty, cost = fund_quantities[sec_id]

                    mv = round(qty * price, 2)
                    records.append({
                        "fund_id": fund_id,
                        "security_id": sec_id,
                        "as_of_date": day.isoformat(),
                        "quantity": qty,
                        "market_value": mv,
                        "cost_basis": cost,
                        "accrued_income": round(self.rng.uniform(0, 1000), 2),
                    })

        batch_size = 5000
        for i in range(0, len(records), batch_size):
            self.db.bulk_insert(records[i : i + batch_size], "holdings")
        return len(records)

    def _generate_portfolio_weights(self) -> int:
        records = []
        for fund_ticker, fund_id in self.fund_ids.items():
            for day in self.trading_days:
                holdings = self.db.execute_query(
                    "SELECT security_id, market_value FROM holdings "
                    "WHERE fund_id = :fid AND as_of_date = :dt",
                    {"fid": fund_id, "dt": day.isoformat()},
                )
                if holdings.empty:
                    continue
                total_mv = holdings["market_value"].sum()
                n = len(holdings)
                equal_weight = 100.0 / n
                for _, row in holdings.iterrows():
                    weight = row["market_value"] / total_mv * 100
                    target = equal_weight + self.rng.normal(0, 0.5)
                    drift = (weight - target) * 100
                    records.append({
                        "fund_id": fund_id,
                        "security_id": int(row["security_id"]),
                        "as_of_date": day.isoformat(),
                        "weight_pct": round(weight, 6),
                        "target_weight": round(target, 6),
                        "drift_bps": round(drift, 4),
                    })

        batch_size = 5000
        for i in range(0, len(records), batch_size):
            self.db.bulk_insert(records[i : i + batch_size], "portfolio_weights")
        return len(records)

    def _generate_trades(self) -> int:
        records = []
        trade_id_counter = 1
        for fund_ticker, fund_id in self.fund_ids.items():
            fund_secs = self._get_securities_for_fund(fund_ticker)
            n_trades = self.rng.integers(200, 600)
            trade_days = self.rng.choice(self.trading_days, size=n_trades, replace=True)

            for day in trade_days:
                sym, _, _, _ = fund_secs[self.rng.integers(0, len(fund_secs))]
                if sym not in self.security_ids:
                    continue
                sec_id = self.security_ids[sym]
                price_row = self.db.execute_query(
                    "SELECT close_price FROM market_prices WHERE security_id = :sid AND price_date = :dt",
                    {"sid": sec_id, "dt": day.isoformat() if hasattr(day, "isoformat") else str(day)},
                )
                if price_row.empty:
                    continue
                price = float(price_row["close_price"].iloc[0])
                side = random.choice(["BUY", "SELL"])
                qty = round(self.rng.uniform(100, 50000), 2)
                gross = round(qty * price, 2)
                commission = round(self.rng.uniform(5, 500), 2)
                net = gross + commission if side == "BUY" else gross - commission
                settlement = day + timedelta(days=2) if hasattr(day, "__add__") else pd.Timestamp(day) + pd.Timedelta(days=2)
                if hasattr(settlement, "date"):
                    settlement = settlement.date()

                status = random.choices(
                    ["PENDING", "CONFIRMED", "SETTLED", "FAILED", "CANCELLED"],
                    weights=[5, 10, 75, 5, 5],
                )[0]

                records.append({
                    "fund_id": fund_id,
                    "security_id": sec_id,
                    "trade_date": day.isoformat() if hasattr(day, "isoformat") else str(day),
                    "settlement_date": settlement.isoformat() if hasattr(settlement, "isoformat") else str(settlement),
                    "side": side,
                    "quantity": qty,
                    "price": round(price, 6),
                    "gross_amount": gross,
                    "commission": commission,
                    "net_amount": net,
                    "broker": random.choice(BROKERS),
                    "trade_status": status,
                    "external_ref": f"TRD-{trade_id_counter:08d}",
                })
                trade_id_counter += 1

        batch_size = 2000
        for i in range(0, len(records), batch_size):
            self.db.bulk_insert(records[i : i + batch_size], "trades")
        return len(records)

    def _generate_settlements(self) -> int:
        trades = self.db.execute_query(
            "SELECT trade_id, fund_id, settlement_date, net_amount, trade_status FROM trades"
        )
        records = []
        for _, trade in trades.iterrows():
            if trade["trade_status"] == "CANCELLED":
                continue
            expected = float(trade["net_amount"])
            if trade["trade_status"] == "FAILED":
                status = "FAILED"
                actual = round(expected * self.rng.uniform(0.5, 0.95), 2)
                fail_reason = random.choice([
                    "Insufficient counterparty funds",
                    "Securities not delivered",
                    "Trade confirmation mismatch",
                    "Settlement system timeout",
                ])
            elif trade["trade_status"] == "SETTLED":
                status = "SETTLED"
                actual = expected
                fail_reason = None
            else:
                status = random.choice(["PENDING", "SETTLED", "PARTIAL"])
                actual = expected if status == "SETTLED" else round(expected * self.rng.uniform(0.8, 1.0), 2)
                fail_reason = None

            records.append({
                "trade_id": int(trade["trade_id"]),
                "fund_id": int(trade["fund_id"]),
                "settlement_date": trade["settlement_date"],
                "expected_amount": expected,
                "actual_amount": actual,
                "settlement_status": status,
                "fail_reason": fail_reason,
            })

        batch_size = 2000
        for i in range(0, len(records), batch_size):
            self.db.bulk_insert(records[i : i + batch_size], "settlements")
        return len(records)

    def _generate_nav_history(self) -> int:
        records = []
        for fund_ticker, fund_id in self.fund_ids.items():
            aum = next(f["aum_billions"] for f in self.config.funds if f["ticker"] == fund_ticker) * 1e9
            nav_per_share = 100.0
            shares = int(aum / nav_per_share)
            prev_nav = nav_per_share
            te_window: list[float] = []

            for day in self.trading_days:
                holdings = self.db.execute_query(
                    "SELECT SUM(market_value) as total_mv FROM holdings "
                    "WHERE fund_id = :fid AND as_of_date = :dt",
                    {"fid": fund_id, "dt": day.isoformat()},
                )
                total_mv = float(holdings["total_mv"].iloc[0]) if not holdings.empty and holdings["total_mv"].iloc[0] else aum
                nav_per_share = total_mv / shares
                daily_return = (nav_per_share - prev_nav) / prev_nav if prev_nav else 0
                benchmark_return = daily_return + self.rng.normal(0, 0.001)
                excess = daily_return - benchmark_return
                te_window.append(excess)
                if len(te_window) > 20:
                    te_window.pop(0)
                tracking_error = float(np.std(te_window)) if len(te_window) > 1 else 0

                records.append({
                    "fund_id": fund_id,
                    "nav_date": day.isoformat(),
                    "nav_per_share": round(nav_per_share, 6),
                    "total_nav": round(total_mv, 2),
                    "shares_outstanding": shares,
                    "daily_return": round(daily_return, 8),
                    "benchmark_return": round(benchmark_return, 8),
                    "tracking_error": round(tracking_error, 8),
                })
                prev_nav = nav_per_share

        batch_size = 2000
        for i in range(0, len(records), batch_size):
            self.db.bulk_insert(records[i : i + batch_size], "nav_history")
        return len(records)

    def _generate_cash_positions(self) -> int:
        records = []
        for fund_ticker, fund_id in self.fund_ids.items():
            aum = next(f["aum_billions"] for f in self.config.funds if f["ticker"] == fund_ticker) * 1e9
            cash_pct = self.rng.uniform(0.01, 0.05)

            for day in self.trading_days:
                nav_row = self.db.execute_query(
                    "SELECT total_nav FROM nav_history WHERE fund_id = :fid AND nav_date = :dt",
                    {"fid": fund_id, "dt": day.isoformat()},
                )
                total_nav = float(nav_row["total_nav"].iloc[0]) if not nav_row.empty else aum
                cash_balance = round(total_nav * cash_pct, 2)
                pending = round(self.rng.uniform(0, cash_balance * 0.3), 2)
                expenses = round(self.rng.uniform(1000, 50000), 2)
                available = round(cash_balance - pending - expenses, 2)

                # Inject occasional cash breaks for reconciliation testing
                if self.rng.random() < 0.02:
                    available += self.rng.uniform(-5000, 5000)

                records.append({
                    "fund_id": fund_id,
                    "as_of_date": day.isoformat(),
                    "cash_balance": cash_balance,
                    "accrued_expenses": expenses,
                    "pending_settlements": pending,
                    "available_cash": available,
                    "currency": "USD",
                })

        batch_size = 2000
        for i in range(0, len(records), batch_size):
            self.db.bulk_insert(records[i : i + batch_size], "cash_positions")
        return len(records)

    def _generate_corporate_actions(self) -> int:
        records = []
        sec_list = list(self.security_ids.items())
        selected = random.sample(sec_list, min(20, len(sec_list)))

        for sym, sec_id in selected:
            n_actions = self.rng.integers(1, 4)
            for _ in range(n_actions):
                action_day = random.choice(self.trading_days)
                action_type = random.choice(["DIVIDEND", "SPLIT", "MERGER", "SPINOFF"])
                records.append({
                    "security_id": sec_id,
                    "action_type": action_type,
                    "ex_date": action_day.isoformat(),
                    "record_date": (action_day - timedelta(days=2)).isoformat(),
                    "pay_date": (action_day + timedelta(days=14)).isoformat(),
                    "ratio": round(self.rng.uniform(1.5, 4.0), 4) if action_type == "SPLIT" else None,
                    "cash_amount": round(self.rng.uniform(0.1, 2.5), 4) if action_type == "DIVIDEND" else None,
                    "description": f"{action_type} for {sym}",
                })

        self.db.bulk_insert(records, "corporate_actions")
        return len(records)

    def _generate_daily_pricing(self) -> int:
        records = []
        for fund_ticker, fund_id in self.fund_ids.items():
            for day in self.trading_days:
                nav_row = self.db.execute_query(
                    "SELECT nav_per_share FROM nav_history WHERE fund_id = :fid AND nav_date = :dt",
                    {"fid": fund_id, "dt": day.isoformat()},
                )
                if nav_row.empty:
                    continue
                calculated = float(nav_row["nav_per_share"].iloc[0])
                # Inject occasional NAV discrepancies
                if self.rng.random() < 0.03:
                    official = calculated * (1 + self.rng.uniform(-0.001, 0.001))
                else:
                    official = calculated
                variance_bps = (official - calculated) / calculated * 10000 if calculated else 0
                status = "EXCEPTION" if abs(variance_bps) > 5 else random.choice(["APPROVED", "APPROVED", "PENDING"])

                records.append({
                    "fund_id": fund_id,
                    "pricing_date": day.isoformat(),
                    "official_nav": round(official, 6),
                    "calculated_nav": round(calculated, 6),
                    "nav_variance_bps": round(variance_bps, 4),
                    "pricing_status": status,
                    "approved_by": "Pricing Team" if status == "APPROVED" else None,
                })

        batch_size = 2000
        for i in range(0, len(records), batch_size):
            self.db.bulk_insert(records[i : i + batch_size], "daily_pricing")
        return len(records)
