"""Home page - Executive overview dashboard."""

import streamlit as st
from dashboard.components.charts import bar_chart, kpi_card, line_chart, pie_chart
from dashboard.utils.data_access import format_currency, format_pct, get_funds, get_latest_date, query_df

st.markdown('<p class="main-header">ETF Operations Command Center</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Daily portfolio monitoring, trade reconciliation & exception management</p>', unsafe_allow_html=True)

as_of = get_latest_date()
funds = get_funds()

col1, col2 = st.columns([3, 1])
with col2:
    selected_date = st.date_input("As-of Date", value=as_of, key="home_date")
    fund_filter = st.multiselect("Funds", funds["ticker"].tolist(), default=funds["ticker"].tolist())

date_str = selected_date.isoformat()

# KPI Row
kpi_cols = st.columns(6)
nav_summary = query_df("""
    SELECT COUNT(DISTINCT f.fund_id) as fund_count,
           SUM(n.total_nav) as total_aum,
           AVG(n.daily_return) as avg_return,
           AVG(n.tracking_error) as avg_te
    FROM nav_history n JOIN funds f ON n.fund_id = f.fund_id
    WHERE n.nav_date = :dt
""", {"dt": date_str})

exc_summary = query_df("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN severity IN ('CRITICAL','HIGH') THEN 1 ELSE 0 END) as critical_high,
           SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_count
    FROM exceptions WHERE as_of_date = :dt
""", {"dt": date_str})

trade_summary = query_df("""
    SELECT COUNT(*) as trade_count, SUM(net_amount) as total_volume
    FROM trades WHERE trade_date = :dt
""", {"dt": date_str})

with kpi_cols[0]:
    aum = nav_summary["total_aum"].iloc[0] if not nav_summary.empty else 0
    kpi_card("Total AUM", format_currency(aum or 0))
with kpi_cols[1]:
    ret = nav_summary["avg_return"].iloc[0] if not nav_summary.empty else 0
    kpi_card("Avg Daily Return", format_pct(ret or 0, 4))
with kpi_cols[2]:
    te = nav_summary["avg_te"].iloc[0] if not nav_summary.empty else 0
    kpi_card("Avg Tracking Error", format_pct(te or 0, 4))
with kpi_cols[3]:
    exc = exc_summary["total"].iloc[0] if not exc_summary.empty else 0
    kpi_card("Exceptions", str(int(exc or 0)), delta=f"{int(exc_summary['open_count'].iloc[0] or 0)} open" if not exc_summary.empty else None, delta_color="inverse")
with kpi_cols[4]:
    tc = trade_summary["trade_count"].iloc[0] if not trade_summary.empty else 0
    kpi_card("Trades Today", str(int(tc or 0)))
with kpi_cols[5]:
    tv = trade_summary["total_volume"].iloc[0] if not trade_summary.empty else 0
    kpi_card("Trade Volume", format_currency(tv or 0))

st.markdown("---")

left, right = st.columns(2)

with left:
    nav_trend = query_df("""
        SELECT n.nav_date, f.ticker, n.nav_per_share, n.daily_return
        FROM nav_history n JOIN funds f ON n.fund_id = f.fund_id
        WHERE n.nav_date >= date(:dt, '-30 days')
        ORDER BY n.nav_date
    """, {"dt": date_str})
    if fund_filter:
        nav_trend = nav_trend[nav_trend["ticker"].isin(fund_filter)]
    line_chart(nav_trend, "nav_date", "nav_per_share", "NAV per Share (30-Day Trend)", color="ticker")

with right:
    exc_by_type = query_df("""
        SELECT exception_type, COUNT(*) as count
        FROM exceptions WHERE as_of_date = :dt
        GROUP BY exception_type ORDER BY count DESC LIMIT 8
    """, {"dt": date_str})
    bar_chart(exc_by_type, "exception_type", "count", "Exceptions by Type")

bottom_left, bottom_right = st.columns(2)

with bottom_left:
    sector_alloc = query_df("""
        SELECT s.sector, SUM(h.market_value) as value
        FROM holdings h
        JOIN securities s ON h.security_id = s.security_id
        JOIN funds f ON h.fund_id = f.fund_id
        WHERE h.as_of_date = :dt AND f.ticker IN ({placeholders})
        GROUP BY s.sector ORDER BY value DESC
    """.format(placeholders=",".join(f"'{t}'" for t in fund_filter) if fund_filter else "'IVV'"),
    {"dt": date_str})
    pie_chart(sector_alloc, "sector", "value", "Sector Allocation")

with bottom_right:
    settlement_status = query_df("""
        SELECT st.settlement_status, COUNT(*) as count
        FROM settlements st
        WHERE st.settlement_date = :dt
        GROUP BY st.settlement_status
    """, {"dt": date_str})
    pie_chart(settlement_status, "settlement_status", "count", "Settlement Status")

# Recent exceptions table
st.markdown("### Recent Open Exceptions")
open_exc = query_df("""
    SELECT f.ticker, e.exception_type, e.severity, e.description, e.status, e.detected_at
    FROM exceptions e
    LEFT JOIN funds f ON e.fund_id = f.fund_id
    WHERE e.status IN ('OPEN', 'INVESTIGATING')
    ORDER BY CASE e.severity
        WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
        e.detected_at DESC
    LIMIT 15
""")
st.dataframe(open_exc, use_container_width=True, hide_index=True)
