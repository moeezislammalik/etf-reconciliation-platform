"""ETF Portfolio Monitoring & Trade Reconciliation Platform - Streamlit Dashboard."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="ETF Operations Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #e94560;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #a0a0a0;
        margin-bottom: 2rem;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #0f3460;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #16213e;
        border-radius: 4px;
        padding: 8px 16px;
    }
</style>
""", unsafe_allow_html=True)

PAGES = {
    "Home": "pages/home.py",
    "Portfolio Overview": "pages/portfolio_overview.py",
    "Trades": "pages/trades.py",
    "Exceptions": "pages/exceptions.py",
    "Reconciliation": "pages/reconciliation.py",
    "Market Prices": "pages/market_prices.py",
    "Reports": "pages/reports.py",
    "Settings": "pages/settings.py",
}

with st.sidebar:
    st.markdown("## 📊 ETF Operations")
    st.markdown("---")
    selection = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
    st.markdown("---")
    st.caption("ETF Portfolio Monitoring & Trade Reconciliation Platform")
    st.caption("v1.0.0 · Moeez Malik")

page_path = Path(__file__).parent / PAGES[selection]
exec(open(page_path).read())
