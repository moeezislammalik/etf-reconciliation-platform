"""Reports page."""

import streamlit as st
from pathlib import Path

from dashboard.utils.data_access import get_config, get_latest_date, query_df
from etl.report_generator import ReportGenerator
from etl.database import DatabaseManager

st.markdown('<p class="main-header">Reports & Exports</p>', unsafe_allow_html=True)

as_of = get_latest_date()
selected_date = st.date_input("Report Date", value=as_of, key="report_date")
date_str = selected_date.isoformat()

config = get_config()
db = DatabaseManager(config)
reports = ReportGenerator(config, db)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Generate Reports")
    if st.button("Generate All Reports", type="primary"):
        with st.spinner("Generating reports..."):
            paths = reports.generate_all_reports(selected_date)
            st.session_state["report_paths"] = paths
            st.success("Reports generated successfully!")

    if "report_paths" in st.session_state:
        st.markdown("**Generated Files:**")
        for name, path in st.session_state["report_paths"].items():
            p = Path(path)
            if p.exists():
                with open(p, "rb") as f:
                    st.download_button(
                        f"Download {name}",
                        f.read(),
                        file_name=p.name,
                        key=f"dl_{name}",
                    )

with col2:
    st.markdown("### Pipeline History")
    pipeline_runs = query_df("""
        SELECT run_date, pipeline_name, status, records_processed,
               exceptions_found, started_at, completed_at
        FROM pipeline_runs ORDER BY started_at DESC LIMIT 20
    """)
    st.dataframe(pipeline_runs, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("### Report Previews")

tab1, tab2, tab3 = st.tabs(["NAV Report", "Exception Report", "Settlement Report"])

with tab1:
    nav = query_df("""
        SELECT f.ticker, f.fund_name, n.nav_per_share, n.total_nav,
               n.daily_return, n.benchmark_return, n.tracking_error
        FROM nav_history n JOIN funds f ON n.fund_id = f.fund_id
        WHERE n.nav_date = :dt
    """, {"dt": date_str})
    st.dataframe(nav, use_container_width=True, hide_index=True)

with tab2:
    exc = query_df("""
        SELECT f.ticker, e.exception_type, e.severity, e.description, e.status
        FROM exceptions e LEFT JOIN funds f ON e.fund_id = f.fund_id
        WHERE e.as_of_date = :dt ORDER BY e.severity
    """, {"dt": date_str})
    st.dataframe(exc, use_container_width=True, hide_index=True)

with tab3:
    settlements = query_df("""
        SELECT f.ticker, s.ticker as security, st.settlement_status,
               st.expected_amount, st.actual_amount, st.fail_reason
        FROM settlements st
        JOIN trades t ON st.trade_id = t.trade_id
        JOIN funds f ON st.fund_id = f.fund_id
        JOIN securities s ON t.security_id = s.security_id
        WHERE st.settlement_date = :dt
    """, {"dt": date_str})
    st.dataframe(settlements, use_container_width=True, hide_index=True)
