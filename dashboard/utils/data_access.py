"""Shared dashboard utilities and data access."""

from __future__ import annotations

from datetime import date
from functools import lru_cache

import pandas as pd
import streamlit as st

from etl.analytics import PortfolioAnalytics
from etl.config import load_config
from etl.database import DatabaseManager
from etl.reconciliation import ReconciliationEngine


@lru_cache(maxsize=1)
def get_config():
    return load_config()


@lru_cache(maxsize=1)
def get_db() -> DatabaseManager:
    return DatabaseManager(get_config())


def get_analytics() -> PortfolioAnalytics:
    return PortfolioAnalytics(get_config(), get_db())


def get_reconciliation() -> ReconciliationEngine:
    return ReconciliationEngine(get_config(), get_db())


@st.cache_data(ttl=300)
def query_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    return get_db().execute_query(sql, params or {})


def get_funds() -> pd.DataFrame:
    return query_df("SELECT fund_id, ticker, fund_name, asset_class FROM funds WHERE is_active = 1")


def get_latest_date() -> date:
    result = query_df("SELECT MAX(nav_date) as max_date FROM nav_history")
    if result.empty or result["max_date"].iloc[0] is None:
        return date(2024, 12, 31)
    return date.fromisoformat(str(result["max_date"].iloc[0]))


def get_date_range() -> tuple[date, date]:
    result = query_df("SELECT MIN(nav_date) as min_date, MAX(nav_date) as max_date FROM nav_history")
    if result.empty:
        return date(2024, 1, 1), date(2024, 12, 31)
    return (
        date.fromisoformat(str(result["min_date"].iloc[0])),
        date.fromisoformat(str(result["max_date"].iloc[0])),
    )


def format_currency(value: float) -> str:
    if abs(value) >= 1e9:
        return f"${value/1e9:.2f}B"
    if abs(value) >= 1e6:
        return f"${value/1e6:.2f}M"
    return f"${value:,.2f}"


def format_pct(value: float, decimals: int = 2) -> str:
    return f"{value * 100:.{decimals}f}%"


COLORS = {
    "primary": "#1a1a2e",
    "secondary": "#16213e",
    "accent": "#0f3460",
    "highlight": "#e94560",
    "success": "#00b894",
    "warning": "#fdcb6e",
    "danger": "#d63031",
    "text": "#dfe6e9",
    "chart_palette": [
        "#e94560", "#0f3460", "#00b894", "#fdcb6e",
        "#6c5ce7", "#0984e3", "#00cec9", "#fab1a0",
    ],
}

PLOTLY_TEMPLATE = "plotly_dark"
