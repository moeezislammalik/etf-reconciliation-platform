"""Settings page."""

import streamlit as st
from dashboard.utils.data_access import get_config, get_db, query_df

st.markdown('<p class="main-header">Settings</p>', unsafe_allow_html=True)

config = get_config()
db = get_db()

tab1, tab2, tab3 = st.tabs(["Configuration", "Database", "About"])

with tab1:
    st.markdown("### Reconciliation Thresholds")
    st.json({
        "price_variance_threshold": config.reconciliation.price_variance_threshold,
        "nav_tolerance_bps": config.reconciliation.nav_tolerance_bps,
        "cash_break_threshold": config.reconciliation.cash_break_threshold,
        "tracking_error_threshold": config.reconciliation.tracking_error_threshold,
        "settlement_lag_days": config.reconciliation.settlement_lag_days,
    })

    st.markdown("### Analytics Settings")
    st.json({
        "risk_free_rate": config.analytics.risk_free_rate,
        "trading_days_per_year": config.analytics.trading_days_per_year,
    })

    st.markdown("### Data Generation")
    st.json({
        "start_date": config.data_start_date,
        "end_date": config.data_end_date,
        "random_seed": config.random_seed,
    })

with tab2:
    st.markdown("### Database Status")
    st.code(config.database.connection_string, language="text")

    tables = [
        "funds", "securities", "holdings", "trades", "market_prices",
        "nav_history", "settlements", "exceptions", "cash_positions",
        "portfolio_weights", "corporate_actions", "daily_pricing", "pipeline_runs",
    ]

    table_data = []
    for table in tables:
        try:
            count = db.get_table_count(table)
            table_data.append({"Table": table, "Row Count": f"{count:,}"})
        except Exception:
            table_data.append({"Table": table, "Row Count": "N/A"})

    st.table(table_data)

    if st.button("Refresh Database Stats"):
        st.rerun()

with tab3:
    st.markdown("""
    ### ETF Portfolio Monitoring & Trade Reconciliation Platform

    **Version:** 1.0.0

    Operations platform for ETF portfolio monitoring, trade reconciliation,
    NAV calculation, and exception management.

    **Capabilities:**
    - Daily ETL pipeline and market data ingestion
    - Automated reconciliation and exception detection
    - Portfolio analytics and performance attribution
    - Streamlit operations dashboard
    - Power BI reporting integration
    - CSV, Excel, and PDF report generation

    **Tech Stack:** Python 3.11+, SQLAlchemy, PostgreSQL/SQLite, Streamlit,
    Plotly, Pandas, ReportLab

    **Developer:** [Moeez Malik](https://github.com/moeezislammalik)
    """)
