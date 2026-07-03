"""Daily ETL pipeline orchestrator."""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime
from pathlib import Path

from etl.analytics import PortfolioAnalytics
from etl.config import AppConfig, PROJECT_ROOT, load_config
from etl.database import DatabaseManager
from etl.market_data_loader import MarketDataLoader
from etl.nav_calculator import NAVCalculator
from etl.reconciliation import ReconciliationEngine
from etl.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


def setup_logging(config: AppConfig) -> None:
    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


class DailyPipeline:
    """Orchestrates the daily ETF operations ETL and reconciliation workflow."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()
        setup_logging(self.config)
        self.db = DatabaseManager(self.config)
        self.market_loader = MarketDataLoader(self.config, self.db)
        self.nav_calculator = NAVCalculator(self.config, self.db)
        self.reconciliation = ReconciliationEngine(self.config, self.db)
        self.analytics = PortfolioAnalytics(self.config, self.db)
        self.reports = ReportGenerator(self.config, self.db)

    def run(self, as_of_date: date | None = None) -> dict:
        """Execute the full daily pipeline."""
        as_of_date = as_of_date or date.today()
        pipeline_name = "daily_etf_operations"
        logger.info("=" * 60)
        logger.info("Starting daily pipeline for %s", as_of_date)
        logger.info("=" * 60)

        results = {"date": as_of_date.isoformat(), "steps": {}, "status": "SUCCESS"}
        total_records = 0
        total_exceptions = 0

        try:
            # Step 1: Load market data
            logger.info("Step 1: Loading market data...")
            price_count = self.market_loader.load_daily_prices(as_of_date)
            results["steps"]["market_data"] = {"records": price_count}
            total_records += price_count

            # Step 2: Calculate NAV
            logger.info("Step 2: Calculating NAV...")
            pricing = self.nav_calculator.update_daily_pricing(as_of_date)
            results["steps"]["nav_calculation"] = {"funds_processed": len(pricing)}
            total_records += len(pricing)

            # Step 3: Run reconciliation
            logger.info("Step 3: Running reconciliation...")
            exceptions = self.reconciliation.run_full_reconciliation(as_of_date)
            exc_count = len(exceptions)
            total_exceptions = exc_count
            results["steps"]["reconciliation"] = {
                "exceptions_found": exc_count,
                "by_type": exceptions.groupby("exception_type").size().to_dict() if not exceptions.empty else {},
            }

            # Step 4: Analytics
            logger.info("Step 4: Running analytics...")
            funds = self.db.execute_query("SELECT fund_id, ticker FROM funds")
            analytics_results = {}
            for _, fund in funds.iterrows():
                metrics = self.analytics.get_fund_metrics_summary(
                    int(fund["fund_id"]), as_of_date
                )
                analytics_results[fund["ticker"]] = metrics
            results["steps"]["analytics"] = analytics_results

            # Step 5: Generate reports
            logger.info("Step 5: Generating reports...")
            report_paths = self.reports.generate_all_reports(as_of_date)
            results["steps"]["reports"] = {k: str(v) for k, v in report_paths.items()}

            self.db.log_pipeline_run(
                as_of_date.isoformat(),
                pipeline_name,
                "SUCCESS",
                records_processed=total_records,
                exceptions_found=total_exceptions,
            )

        except Exception as e:
            logger.error("Pipeline failed: %s", e, exc_info=True)
            results["status"] = "FAILED"
            results["error"] = str(e)
            self.db.log_pipeline_run(
                as_of_date.isoformat(),
                pipeline_name,
                "FAILED",
                error_message=str(e),
            )

        logger.info("Pipeline completed with status: %s", results["status"])
        return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run daily ETF operations pipeline")
    parser.add_argument("--date", type=str, help="As-of date (YYYY-MM-DD)")
    args = parser.parse_args()

    as_of = date.fromisoformat(args.date) if args.date else date(2024, 12, 31)
    pipeline = DailyPipeline()
    results = pipeline.run(as_of)
    print(f"\nPipeline Status: {results['status']}")
    if "steps" in results:
        for step, data in results["steps"].items():
            print(f"  {step}: {data}")
