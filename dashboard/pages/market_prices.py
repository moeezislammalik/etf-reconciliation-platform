"""Market Prices page."""

import streamlit as st
from dashboard.components.charts import candlestick_chart, kpi_card, line_chart, scatter_chart
from dashboard.utils.data_access import get_latest_date, query_df

st.markdown('<p class="main-header">Market Prices</p>', unsafe_allow_html=True)

securities = query_df("SELECT security_id, ticker, security_name, sector FROM securities WHERE is_active = 1 ORDER BY ticker")
as_of = get_latest_date()

col1, col2, col3 = st.columns(3)
with col1:
    selected_sec = st.selectbox("Security", securities["ticker"].tolist())
with col2:
    end_date = st.date_input("End Date", value=as_of)
with col3:
    lookback = st.selectbox("Lookback", [30, 60, 90, 180, 365], index=2)

sec_id = int(securities[securities["ticker"] == selected_sec]["security_id"].iloc[0])
sec_name = securities[securities["ticker"] == selected_sec]["security_name"].iloc[0]

prices = query_df("""
    SELECT price_date, open_price, high_price, low_price, close_price, volume
    FROM market_prices
    WHERE security_id = :sid AND price_date >= date(:end, :lb)
    ORDER BY price_date
""", {"sid": sec_id, "end": end_date.isoformat(), "lb": f"-{lookback} days"})

if not prices.empty:
    latest = prices.iloc[-1]
    prev = prices.iloc[-2] if len(prices) > 1 else latest
    change = (latest["close_price"] - prev["close_price"]) / prev["close_price"] if prev["close_price"] else 0

    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        kpi_card("Last Price", f"${latest['close_price']:.2f}")
    with kpi_cols[1]:
        kpi_card("Change", f"{change*100:.2f}%", delta=f"${latest['close_price']-prev['close_price']:.2f}")
    with kpi_cols[2]:
        kpi_card("Day High", f"${latest['high_price']:.2f}")
    with kpi_cols[3]:
        kpi_card("Day Low", f"${latest['low_price']:.2f}")
    with kpi_cols[4]:
        kpi_card("Volume", f"{latest['volume']:,.0f}")

    tab1, tab2, tab3 = st.tabs(["Candlestick", "Price History", "Volume Analysis"])

    with tab1:
        candlestick_chart(prices.tail(60), f"{selected_sec} - {sec_name}")

    with tab2:
        line_chart(prices, "price_date", "close_price", f"{selected_sec} Close Price")

    with tab3:
        scatter_chart(prices, "price_date", "volume", f"{selected_sec} Volume", size="close_price")

    st.dataframe(prices.tail(20).sort_values("price_date", ascending=False), use_container_width=True, hide_index=True)
else:
    st.warning("No price data available for selected security.")

# Missing prices report
st.markdown("### Missing Prices Report")
missing = query_df("""
    SELECT s.ticker, s.security_name, h.as_of_date
    FROM holdings h
    JOIN securities s ON h.security_id = s.security_id
    LEFT JOIN market_prices mp ON s.security_id = mp.security_id AND mp.price_date = h.as_of_date
    WHERE h.as_of_date = :dt AND mp.price_id IS NULL
    LIMIT 50
""", {"dt": end_date.isoformat()})
if missing.empty:
    st.success("No missing prices detected.")
else:
    st.warning(f"{len(missing)} missing prices found")
    st.dataframe(missing, use_container_width=True, hide_index=True)
