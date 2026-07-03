"""Reconciliation page."""

import streamlit as st
from dashboard.components.charts import bar_chart, heatmap_chart, kpi_card
from dashboard.utils.data_access import get_funds, get_latest_date, get_reconciliation, query_df

st.markdown('<p class="main-header">Reconciliation Engine</p>', unsafe_allow_html=True)

as_of = get_latest_date()
selected_date = st.date_input("Reconciliation Date", value=as_of, key="recon_date")
date_str = selected_date.isoformat()

if st.button("Run Reconciliation", type="primary"):
    with st.spinner("Running reconciliation checks..."):
        recon = get_reconciliation()
        results = recon.run_full_reconciliation(selected_date)
        st.success(f"Reconciliation complete: {len(results)} exceptions detected")
        st.session_state["recon_results"] = results

# Current exception summary
summary = query_df("""
    SELECT exception_type, severity, status, COUNT(*) as count
    FROM exceptions WHERE as_of_date = :dt
    GROUP BY exception_type, severity, status
    ORDER BY count DESC
""", {"dt": date_str})

kpi_cols = st.columns(4)
total = summary["count"].sum() if not summary.empty else 0
with kpi_cols[0]:
    kpi_card("Total Issues", str(int(total)))
with kpi_cols[1]:
    critical = summary[summary["severity"] == "CRITICAL"]["count"].sum() if not summary.empty else 0
    kpi_card("Critical", str(int(critical)))
with kpi_cols[2]:
    open_count = summary[summary["status"] == "OPEN"]["count"].sum() if not summary.empty else 0
    kpi_card("Open", str(int(open_count)))
with kpi_cols[3]:
    resolved = summary[summary["status"] == "RESOLVED"]["count"].sum() if not summary.empty else 0
    kpi_card("Resolved", str(int(resolved)))

tab1, tab2, tab3, tab4 = st.tabs([
    "NAV Reconciliation", "Settlement Recon", "Cash Reconciliation", "Weight Drift",
])

with tab1:
    nav_recon = query_df("""
        SELECT f.ticker, dp.official_nav, dp.calculated_nav, dp.nav_variance_bps, dp.pricing_status
        FROM daily_pricing dp JOIN funds f ON dp.fund_id = f.fund_id
        WHERE dp.pricing_date = :dt ORDER BY ABS(dp.nav_variance_bps) DESC
    """, {"dt": date_str})
    st.dataframe(nav_recon, use_container_width=True, hide_index=True)
    if not nav_recon.empty:
        bar_chart(nav_recon, "ticker", "nav_variance_bps", "NAV Variance (bps)")

with tab2:
    settlement_recon = query_df("""
        SELECT f.ticker, s.ticker as security, t.side, t.net_amount,
               st.expected_amount, st.actual_amount, st.settlement_status, st.fail_reason
        FROM settlements st
        JOIN trades t ON st.trade_id = t.trade_id
        JOIN funds f ON st.fund_id = f.fund_id
        JOIN securities s ON t.security_id = s.security_id
        WHERE st.settlement_date = :dt
    """, {"dt": date_str})
    st.dataframe(settlement_recon, use_container_width=True, hide_index=True)

with tab3:
    cash_recon = query_df("""
        SELECT f.ticker, cp.cash_balance, cp.pending_settlements,
               cp.accrued_expenses, cp.available_cash,
               cp.cash_balance - cp.pending_settlements - cp.accrued_expenses - cp.available_cash as break_amount
        FROM cash_positions cp JOIN funds f ON cp.fund_id = f.fund_id
        WHERE cp.as_of_date = :dt
    """, {"dt": date_str})
    st.dataframe(cash_recon, use_container_width=True, hide_index=True)
    if not cash_recon.empty:
        bar_chart(cash_recon, "ticker", "break_amount", "Cash Breaks by Fund")

with tab4:
    weight_drift = query_df("""
        SELECT f.ticker, s.ticker as security, pw.weight_pct, pw.target_weight, pw.drift_bps
        FROM portfolio_weights pw
        JOIN funds f ON pw.fund_id = f.fund_id
        JOIN securities s ON pw.security_id = s.security_id
        WHERE pw.as_of_date = :dt AND ABS(pw.drift_bps) > 25
        ORDER BY ABS(pw.drift_bps) DESC LIMIT 50
    """, {"dt": date_str})
    st.dataframe(weight_drift, use_container_width=True, hide_index=True)

# Heatmap of exceptions by fund and type
exc_heatmap = query_df("""
    SELECT f.ticker, e.exception_type, COUNT(*) as count
    FROM exceptions e JOIN funds f ON e.fund_id = f.fund_id
    WHERE e.as_of_date = :dt
    GROUP BY f.ticker, e.exception_type
""", {"dt": date_str})
if not exc_heatmap.empty:
    heatmap_chart(exc_heatmap, "exception_type", "ticker", "count", "Exception Heatmap by Fund")
