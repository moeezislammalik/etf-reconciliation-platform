"""Exceptions dashboard page."""

import streamlit as st
from dashboard.components.charts import bar_chart, kpi_card, pie_chart
from dashboard.utils.data_access import get_funds, get_latest_date, query_df

st.markdown('<p class="main-header">Exception Management</p>', unsafe_allow_html=True)

funds = get_funds()
as_of = get_latest_date()

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    selected_date = st.date_input("As-of Date", value=as_of, key="exc_date")
with filter_col2:
    severity_filter = st.multiselect("Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                                     default=["CRITICAL", "HIGH", "MEDIUM", "LOW"])
with filter_col3:
    status_filter = st.multiselect("Status", ["OPEN", "INVESTIGATING", "RESOLVED", "CLOSED"],
                                   default=["OPEN", "INVESTIGATING"])

date_str = selected_date.isoformat()

exceptions = query_df("""
    SELECT e.exception_id, f.ticker as fund, e.exception_type, e.severity,
           e.description, e.status, e.reference_id, e.reference_table,
           e.as_of_date, e.detected_at, e.assigned_to
    FROM exceptions e
    LEFT JOIN funds f ON e.fund_id = f.fund_id
    WHERE e.as_of_date = :dt
    ORDER BY CASE e.severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
           WHEN 'MEDIUM' THEN 3 ELSE 4 END, e.detected_at DESC
""", {"dt": date_str})

if severity_filter:
    exceptions = exceptions[exceptions["severity"].isin(severity_filter)]
if status_filter:
    exceptions = exceptions[exceptions["status"].isin(status_filter)]

kpi_cols = st.columns(5)
with kpi_cols[0]:
    kpi_card("Total", str(len(exceptions)))
with kpi_cols[1]:
    kpi_card("Critical", str(len(exceptions[exceptions["severity"] == "CRITICAL"])))
with kpi_cols[2]:
    kpi_card("High", str(len(exceptions[exceptions["severity"] == "HIGH"])))
with kpi_cols[3]:
    kpi_card("Open", str(len(exceptions[exceptions["status"] == "OPEN"])))
with kpi_cols[4]:
    kpi_card("Investigating", str(len(exceptions[exceptions["status"] == "INVESTIGATING"])))

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    by_type = exceptions.groupby("exception_type").size().reset_index(name="count")
    bar_chart(by_type, "exception_type", "count", "Exceptions by Type")
with chart_col2:
    by_sev = exceptions.groupby("severity").size().reset_index(name="count")
    pie_chart(by_sev, "severity", "count", "Severity Distribution")

# Trend over time
trend = query_df("""
    SELECT as_of_date, severity, COUNT(*) as count
    FROM exceptions
    WHERE as_of_date >= date(:dt, '-30 days')
    GROUP BY as_of_date, severity ORDER BY as_of_date
""", {"dt": date_str})
if not trend.empty:
    import plotly.express as px
    fig = px.bar(trend, x="as_of_date", y="count", color="severity", barmode="stack",
                 title="30-Day Exception Trend", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

st.markdown(f"### Exception Details ({len(exceptions)} records)")
st.dataframe(exceptions, use_container_width=True, hide_index=True)

csv = exceptions.to_csv(index=False)
st.download_button("Download Exceptions CSV", csv, f"exceptions_{date_str}.csv", "text/csv")
