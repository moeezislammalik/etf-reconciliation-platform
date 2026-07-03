"""Configuration management for ETF operations platform."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class DatabaseConfig:
    db_type: str = "sqlite"
    host: str = "localhost"
    port: int = 5432
    name: str = "etf_operations"
    user: str = "etf_admin"
    password: str = "changeme"
    path: str = "data/etf_operations.db"

    @property
    def connection_string(self) -> str:
        if self.db_type == "postgresql":
            return (
                f"postgresql+psycopg2://{self.user}:{self.password}"
                f"@{self.host}:{self.port}/{self.name}"
            )
        db_path = PROJECT_ROOT / self.path
        return f"sqlite:///{db_path}"


@dataclass
class ReconciliationConfig:
    price_variance_threshold: float = 0.05
    nav_tolerance_bps: float = 5.0
    cash_break_threshold: float = 1000.0
    tracking_error_threshold: float = 0.005
    settlement_lag_days: int = 2


@dataclass
class AnalyticsConfig:
    risk_free_rate: float = 0.045
    trading_days_per_year: int = 252


@dataclass
class AppConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    reconciliation: ReconciliationConfig = field(default_factory=ReconciliationConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    funds: list[dict[str, Any]] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    security_types: list[str] = field(default_factory=list)
    report_output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "reports")
    export_output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "exports")
    log_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "logs")
    log_level: str = "INFO"
    random_seed: int = 42
    data_start_date: str = "2024-01-01"
    data_end_date: str = "2024-12-31"


def load_config(env_file: str | None = None) -> AppConfig:
    """Load configuration from environment variables and YAML settings."""
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv(PROJECT_ROOT / ".env")

    settings_path = PROJECT_ROOT / "config" / "settings.yaml"
    settings: dict[str, Any] = {}
    if settings_path.exists():
        with open(settings_path) as f:
            settings = yaml.safe_load(f) or {}

    recon = settings.get("reconciliation", {})
    analytics = settings.get("analytics", {})

    db = DatabaseConfig(
        db_type=os.getenv("DB_TYPE", "sqlite"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", "etf_operations"),
        user=os.getenv("DB_USER", "etf_admin"),
        password=os.getenv("DB_PASSWORD", "changeme"),
        path=os.getenv("DB_PATH", "data/etf_operations.db"),
    )

    return AppConfig(
        database=db,
        reconciliation=ReconciliationConfig(
            price_variance_threshold=float(
                os.getenv("PRICE_VARIANCE_THRESHOLD", recon.get("price_variance_threshold", 0.05))
            ),
            nav_tolerance_bps=float(
                os.getenv("NAV_TOLERANCE_BPS", recon.get("nav_tolerance_bps", 5))
            ),
            cash_break_threshold=float(
                os.getenv("CASH_BREAK_THRESHOLD", recon.get("cash_break_threshold", 1000))
            ),
            tracking_error_threshold=float(
                os.getenv("TRACKING_ERROR_THRESHOLD", recon.get("tracking_error_threshold", 0.005))
            ),
            settlement_lag_days=recon.get("settlement_lag_days", 2),
        ),
        analytics=AnalyticsConfig(
            risk_free_rate=analytics.get("risk_free_rate", 0.045),
            trading_days_per_year=analytics.get("trading_days_per_year", 252),
        ),
        funds=settings.get("funds", []),
        sectors=settings.get("sectors", []),
        security_types=settings.get("security_types", []),
        report_output_dir=Path(os.getenv("REPORT_OUTPUT_DIR", PROJECT_ROOT / "reports")),
        export_output_dir=Path(os.getenv("EXPORT_OUTPUT_DIR", PROJECT_ROOT / "data" / "exports")),
        log_dir=Path(os.getenv("LOG_DIR", PROJECT_ROOT / "logs")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        random_seed=int(os.getenv("RANDOM_SEED", "42")),
        data_start_date=os.getenv("DATA_START_DATE", "2024-01-01"),
        data_end_date=os.getenv("DATA_END_DATE", "2024-12-31"),
    )
