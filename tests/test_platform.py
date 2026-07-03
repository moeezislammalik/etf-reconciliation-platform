"""Test suite for ETF reconciliation platform."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.config import load_config
from etl.database import DatabaseManager
from etl.analytics import PortfolioAnalytics
from etl.nav_calculator import NAVCalculator
from etl.reconciliation import ReconciliationEngine


@pytest.fixture(scope="module")
def config():
    return load_config()


@pytest.fixture(scope="module")
def db(config):
    return DatabaseManager(config)


class TestDatabase:
    def test_connection(self, db):
        result = db.execute_query("SELECT 1 as val")
        assert result["val"].iloc[0] == 1

    def test_funds_exist(self, db):
        count = db.get_table_count("funds")
        assert count >= 5

    def test_securities_exist(self, db):
        count = db.get_table_count("securities")
        assert count >= 50

    def test_market_prices_exist(self, db):
        count = db.get_table_count("market_prices")
        assert count > 1000


class TestNAVCalculator:
    def test_calculate_nav(self, config, db):
        calc = NAVCalculator(config, db)
        funds = db.execute_query("SELECT fund_id FROM funds LIMIT 1")
        fund_id = int(funds["fund_id"].iloc[0])
        nav = calc.calculate_nav(fund_id, date(2024, 12, 31))
        assert nav["total_nav"] > 0
        assert nav["nav_per_share"] > 0

    def test_daily_return(self, config, db):
        calc = NAVCalculator(config, db)
        funds = db.execute_query("SELECT fund_id FROM funds LIMIT 1")
        fund_id = int(funds["fund_id"].iloc[0])
        ret = calc.calculate_daily_return(fund_id, date(2024, 12, 31))
        assert ret is not None


class TestAnalytics:
    def test_portfolio_return(self, config, db):
        analytics = PortfolioAnalytics(config, db)
        funds = db.execute_query("SELECT fund_id FROM funds LIMIT 1")
        fund_id = int(funds["fund_id"].iloc[0])
        ret = analytics.calculate_portfolio_return(fund_id, date(2024, 1, 1), date(2024, 12, 31))
        assert isinstance(ret, float)

    def test_sharpe_ratio(self, config, db):
        analytics = PortfolioAnalytics(config, db)
        funds = db.execute_query("SELECT fund_id FROM funds LIMIT 1")
        fund_id = int(funds["fund_id"].iloc[0])
        sharpe = analytics.calculate_sharpe_ratio(fund_id, date(2024, 1, 1), date(2024, 12, 31))
        assert isinstance(sharpe, float)

    def test_sector_allocation(self, config, db):
        analytics = PortfolioAnalytics(config, db)
        funds = db.execute_query("SELECT fund_id FROM funds LIMIT 1")
        fund_id = int(funds["fund_id"].iloc[0])
        sectors = analytics.get_sector_allocation(fund_id, date(2024, 12, 31))
        assert not sectors.empty
        assert "weight_pct" in sectors.columns


class TestReconciliation:
    def test_run_reconciliation(self, config, db):
        engine = ReconciliationEngine(config, db)
        results = engine.run_full_reconciliation(date(2024, 12, 31))
        assert isinstance(results, type(db.execute_query("SELECT 1")))

    def test_exception_types_defined(self, config, db):
        engine = ReconciliationEngine(config, db)
        assert len(engine.EXCEPTION_TYPES) >= 10


class TestViews:
    def test_latest_nav_view(self, db):
        result = db.execute_query("SELECT * FROM vw_latest_nav")
        assert len(result) >= 5

    def test_sector_allocation_view(self, db):
        result = db.execute_query("SELECT * FROM vw_sector_allocation LIMIT 10")
        assert not result.empty
