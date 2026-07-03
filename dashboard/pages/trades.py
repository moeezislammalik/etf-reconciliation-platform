"""Trades page."""

import streamlit as st
from dashboard.components.charts import bar_chart, kpi_card, pie_chart
from dashboard.utils.data_access import format_currency, get_funds, get_latest_date, query_df

st.markdown('<p class="main-header">Trade Activity</p>', unsafe_allow_html=True)

funds = get_funds()
as_of = get_latest_date()

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
with filter_col1:
    fund_filter = st.multiselect("Fund", funds["ticker"].tolist(), default=funds["ticker"].tolist(), key="trade_fund")
with filter_col2:
    side_filter = st.multiselect("Side", ["BUY", "SELL"], default=["BUY", "SELL"])
with filter_col3:
    status_filter = st.multiselect("Status", ["PENDING", "CONFIRMED", "SETTLED", "FAILED", "CANCELLED"],
                                   default=["PENDING", "CONFIRMED", "SETTLED", "FAILED"])
with filter_col4:
    search = st.text_input("Search (ticker/ref)", "")

date_col1, date_col2 = st.columns(2)
with date_col1:
    start_date = st.date_input("From", value=as_of.replace(day=1))
with date_col2:
    end_date = st.date_input("To", value=as_of)

trades = query_df("""
    SELECT t.trade_id, t.trade_date, t.settlement_date, f.ticker as fund,
           s.ticker as security, t.side, t.quantity, t.price,
           t.gross_amount, t.commission, t.net_amount, t.broker,
           t.trade_status, t.external_ref
    FROM trades t
    JOIN funds f ON t.fund_id = f.fund_id
    JOIN securities s ON t.security_id = s.security_id
    WHERE t.trade_date BETWEEN :start AND :end
    ORDER BY t.trade_date DESC, t.trade_id DESC
""", {"start": start_date.isoformat(), "end": end_date.isoformat()})

if fund_filter:
    trades = trades[trades["fund"].isin(fund_filter)]
if side_filter:
    trades = trades[trades["side"].isin(side_filter)]
if status_filter:
    trades = trades[trades["trade_status"].isin(status_filter)]
if search:
    mask = trades["security"].str.contains(search, case=False, na=False) | \
           trades["external_ref"].str.contains(search, case=False, na=False)
    trades = trades[mask]

kpi_cols = st.columns(4)
with kpi_cols[0]:
    kpi_card("Total Trades", str(len(trades)))
with kpi_cols[1]:
    kpi_card("Buy Volume", format_currency(trades[trades["side"] == "BUY"]["net_amount"].sum()))
with kpi_cols[2]:
    kpi_card("Sell Volume", format_currency(trades[trades["side"] == "SELL"]["net_amount"].sum()))
with kpi_cols[3]:
    failed = len(trades[trades["trade_status"] == "FAILED"])
    kpi_card("Failed Trades", str(failed))

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    daily_vol = trades.groupby("trade_date").agg(count=("trade_id", "count"), volume=("net_amount", "sum")).reset_index()
    bar_chart(daily_vol, "trade_date", "count", "Daily Trade Count")
with chart_col2:
    status_counts = trades.groupby("trade_status").size().reset_index(name="count")
    pie_chart(status_counts, "trade_status", "count", "Trade Status Distribution")

st.markdown(f"### Trade Blotter ({len(trades)} records)")
st.dataframe(trades, use_container_width=True, hide_index=True)

csv = trades.to_csv(index=False)
st.download_button("Download Trades CSV", csv, f"trades_{start_date}_{end_date}.csv", "text/csv")
