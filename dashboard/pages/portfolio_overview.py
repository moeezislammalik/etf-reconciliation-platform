"""Portfolio Overview page."""

import streamlit as st
from dashboard.components.charts import bar_chart, kpi_card, pie_chart, treemap_chart
from dashboard.utils.data_access import format_currency, format_pct, get_analytics, get_funds, get_latest_date, query_df

st.markdown('<p class="main-header">Portfolio Overview</p>', unsafe_allow_html=True)

funds = get_funds()
as_of = get_latest_date()

col1, col2 = st.columns([2, 1])
with col1:
    selected_fund = st.selectbox("Select Fund", funds["ticker"].tolist(), index=0)
with col2:
    selected_date = st.date_input("As-of Date", value=as_of)

fund_id = int(funds[funds["ticker"] == selected_fund]["fund_id"].iloc[0])
date_str = selected_date.isoformat()
analytics = get_analytics()

metrics = analytics.get_fund_metrics_summary(fund_id, selected_date)

kpi_cols = st.columns(5)
with kpi_cols[0]:
    kpi_card("YTD Return", format_pct(metrics.get("portfolio_return_ytd", 0)))
with kpi_cols[1]:
    kpi_card("Volatility", format_pct(metrics.get("volatility", 0)))
with kpi_cols[2]:
    kpi_card("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")
with kpi_cols[3]:
    kpi_card("Tracking Error", format_pct(metrics.get("tracking_error", 0), 4))
with kpi_cols[4]:
    kpi_card("Cash Exposure", format_pct(metrics.get("cash_pct", 0) / 100 if metrics.get("cash_pct") else 0))

st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs(["Holdings", "Sector Allocation", "Asset Allocation", "Concentration Risk"])

with tab1:
    holdings = analytics.get_largest_holdings(fund_id, selected_date, top_n=20)
    if not holdings.empty:
        holdings["market_value_fmt"] = holdings["market_value"].apply(format_currency)
        st.dataframe(
            holdings[["ticker", "security_name", "sector", "quantity", "market_value_fmt", "weight_pct"]].rename(columns={
                "ticker": "Ticker", "security_name": "Name", "sector": "Sector",
                "quantity": "Quantity", "market_value_fmt": "Market Value", "weight_pct": "Weight %",
            }),
            use_container_width=True, hide_index=True,
        )
        treemap_chart(
            holdings, path=["sector", "ticker"], values="market_value",
            title=f"{selected_fund} - Holdings Treemap",
        )

with tab2:
    sectors = analytics.get_sector_allocation(fund_id, selected_date)
    col_a, col_b = st.columns(2)
    with col_a:
        pie_chart(sectors, "sector", "market_value", "Sector Allocation")
    with col_b:
        bar_chart(sectors, "sector", "weight_pct", "Sector Weights (%)")

with tab3:
    assets = analytics.get_asset_allocation(fund_id, selected_date)
    pie_chart(assets, "security_type", "market_value", "Asset Type Allocation")

with tab4:
    conc_cols = st.columns(3)
    with conc_cols[0]:
        kpi_card("Top 5 Concentration", f"{metrics.get('top5_concentration', 0):.1f}%")
    with conc_cols[1]:
        kpi_card("Top 10 Concentration", f"{metrics.get('top10_concentration', 0):.1f}%")
    with conc_cols[2]:
        kpi_card("Herfindahl Index", f"{metrics.get('herfindahl_index', 0):.4f}")

    weights = query_df("""
        SELECT s.ticker, pw.weight_pct FROM portfolio_weights pw
        JOIN securities s ON pw.security_id = s.security_id
        WHERE pw.fund_id = :fid AND pw.as_of_date = :dt
        ORDER BY pw.weight_pct DESC LIMIT 15
    """, {"fid": fund_id, "dt": date_str})
    bar_chart(weights, "ticker", "weight_pct", "Top 15 Holdings by Weight")

# Performance Attribution
st.markdown("### Performance Attribution (Sector)")
attribution = analytics.performance_attribution(fund_id, selected_date)
if not attribution.empty:
    attribution["contribution_pct"] = attribution["contribution"] * 100
    bar_chart(attribution, "sector", "contribution_pct", "Sector Return Contribution (%)")
