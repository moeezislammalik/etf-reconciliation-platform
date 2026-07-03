# ETF Portfolio Monitoring & Trade Reconciliation Platform

> A production operations platform for daily ETF portfolio monitoring, trade reconciliation, and exception management.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/dashboard-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![SQL](https://img.shields.io/badge/database-PostgreSQL%20%7C%20SQLite-336791.svg)](https://www.postgresql.org/)
[![Power BI](https://img.shields.io/badge/reporting-Power%20BI-F2C811.svg)](https://powerbi.microsoft.com/)

---

## Business Problem

ETF operations teams at asset managers process thousands of trades, price updates, and NAV calculations daily. A single missed settlement failure, pricing anomaly, or cash break can delay fund pricing, trigger regulatory issues, and erode investor confidence.

This platform automates the end-to-end daily workflow:

1. **Ingest** market data and portfolio positions
2. **Calculate** NAV, returns, and tracking error
3. **Reconcile** trades, settlements, cash, and weights against expected values
4. **Detect** exceptions automatically with severity classification
5. **Report** findings via dashboards, CSV exports, Excel summaries, and PDF reports

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Streamlit Dashboard                          │
│  Home │ Portfolio │ Trades │ Exceptions │ Recon │ Prices │ Reports  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     Daily ETL Pipeline (Python)                      │
│  Market Data → NAV Calc → Reconciliation → Analytics → Reports      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│              PostgreSQL / SQLite  (Normalized Schema)                │
│  Funds │ Securities │ Holdings │ Trades │ NAV │ Settlements │ ...   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     Power BI (Star Schema + DAX)                       │
│  Executive │ NAV │ Performance │ Allocation │ Exceptions │ KPIs     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Database | PostgreSQL (prod) / SQLite (dev) |
| ORM | SQLAlchemy 2.0 |
| Dashboard | Streamlit + Plotly |
| Reporting | ReportLab (PDF), openpyxl (Excel) |
| Analytics | Pandas, NumPy, SciPy |
| BI | Power BI (star schema + DAX) |
| Testing | pytest |

---

## Project Structure

```
etf-reconciliation-platform/
├── config/
│   └── settings.yaml          # Fund definitions, thresholds, analytics config
├── data/
│   ├── raw/                   # Raw input files
│   ├── processed/             # Intermediate data
│   └── exports/               # CSV exports for Power BI
├── sql/
│   ├── schema/                # Table definitions (13 tables)
│   ├── indexes/               # Performance indexes
│   ├── views/                 # Analytical views (8 views)
│   └── queries/               # Stored reconciliation queries
├── etl/
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connection & operations
│   ├── data_generator.py      # Historical data loader
│   ├── market_data_loader.py  # Market data ETL
│   ├── nav_calculator.py      # NAV calculation engine
│   ├── reconciliation.py      # Automated reconciliation engine
│   ├── analytics.py           # Portfolio analytics & attribution
│   ├── report_generator.py    # CSV, Excel, PDF reports
│   └── pipeline.py            # Daily pipeline orchestrator
├── dashboard/
│   ├── app.py                 # Streamlit main app
│   ├── pages/                 # 8 dashboard pages
│   ├── components/            # Reusable chart components
│   └── utils/                 # Data access utilities
├── scripts/
│   ├── setup_db.py            # Initialize database schema
│   ├── generate_data.py       # Seed database with historical data
│   ├── run_daily_pipeline.py  # Execute daily ETL + reconciliation
│   └── export_for_powerbi.py  # Export star schema for Power BI
├── docs/
│   └── powerbi/               # DAX measures, star schema design
├── tests/                     # pytest test suite
├── reports/                   # Generated PDF/Excel reports
└── logs/                      # Pipeline execution logs
```

---

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/moeezislammalik/etf-reconciliation-platform.git
cd etf-reconciliation-platform

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

### 2. Initialize Database

```bash
python scripts/setup_db.py
```

### 3. Seed Database

```bash
python scripts/generate_data.py
```

This loads historical records across 13 tables including:
- 5 ETF funds (IVV, AGG, EEM, IWM, TLT)
- 70+ securities
- 252 trading days of market prices, holdings, NAV, trades, and settlements

### 4. Run Daily Pipeline

```bash
python scripts/run_daily_pipeline.py --date 2024-12-31
```

### 5. Launch Dashboard

```bash
streamlit run dashboard/app.py
```

Open `http://localhost:8501` in your browser.

### 6. Export for Power BI

```bash
python scripts/export_for_powerbi.py
```

Import CSV files from `data/exports/powerbi/` into Power BI Desktop. See `docs/powerbi/DAX_MEASURES.md` for star schema and DAX measure definitions.

---

## Database Schema

### Core Tables

| Table | Records (approx) | Description |
|-------|-------------------|-------------|
| `funds` | 5 | ETF fund master data |
| `securities` | 70+ | Security reference (CUSIP, sector, type) |
| `holdings` | 50K+ | Daily portfolio positions |
| `trades` | 2K+ | Trade blotter with execution details |
| `market_prices` | 100K+ | OHLCV daily pricing |
| `nav_history` | 1.2K+ | Daily NAV, returns, tracking error |
| `settlements` | 2K+ | Trade settlement records |
| `exceptions` | Variable | Reconciliation exceptions |
| `cash_positions` | 1.2K+ | Daily cash balances |
| `portfolio_weights` | 50K+ | Weight vs target allocation |
| `corporate_actions` | 40+ | Dividends, splits, mergers |
| `daily_pricing` | 1.2K+ | Official vs calculated NAV |
| `pipeline_runs` | Variable | ETL execution audit log |

### Key Views

- `vw_latest_nav` — Current NAV per fund
- `vw_holdings_detail` — Holdings with security metadata
- `vw_open_exceptions` — Active exceptions requiring action
- `vw_trade_settlement_status` — Trade-to-settlement join
- `vw_sector_allocation` — Sector weights by fund
- `vw_operational_kpis` — Daily exception KPIs

---

## Reconciliation Engine

The automated reconciliation engine runs 10 checks daily:

| Check | Exception Type | Severity Logic |
|-------|---------------|----------------|
| Failed settlements | `FAILED_SETTLEMENT` | HIGH |
| Missing market prices | `MISSING_PRICE` | MEDIUM |
| Price anomalies (>5%) | `PRICE_VARIANCE` | MEDIUM → CRITICAL |
| Cash breaks (>$1K) | `CASH_IMBALANCE` | MEDIUM → HIGH |
| NAV discrepancies (>5 bps) | `INCORRECT_NAV` | HIGH → CRITICAL |
| Weight drift (>50 bps) | `INCORRECT_WEIGHT_ALLOCATION` | MEDIUM → HIGH |
| Duplicate trades | `DUPLICATE_TRADE` | HIGH |
| Settlement amount mismatch | `SETTLEMENT_MISMATCH` | HIGH |
| Market value mismatch | `MARKET_VALUE_MISMATCH` | MEDIUM |
| Tracking error breach | `TRACKING_ERROR_BREACH` | MEDIUM |

Each detected issue creates an `exceptions` record with severity, status, and reference linkage for investigation.

---

## Analytics Capabilities

| Metric | Method |
|--------|--------|
| Portfolio Return | Compound daily returns |
| Daily Return | NAV day-over-day change |
| Sharpe Ratio | Excess return / volatility (annualized) |
| Tracking Error | Std dev of excess returns vs benchmark |
| Volatility | Annualized daily return std dev |
| Sector Allocation | Holdings grouped by GICS sector |
| Asset Allocation | Holdings grouped by security type |
| Largest Holdings | Top N by market value |
| Concentration Risk | Top 5/10 weights, Herfindahl index |
| Cash Exposure | Cash as % of total NAV |
| Turnover | Traded volume / average NAV |
| Performance Attribution | Sector-level return contribution |

---

## Dashboard Pages

| Page | Features |
|------|----------|
| **Home** | Executive KPIs, NAV trend, exception summary, sector allocation |
| **Portfolio Overview** | Holdings treemap, sector/asset allocation, concentration risk, attribution |
| **Trades** | Trade blotter with search/filter, volume charts, CSV download |
| **Exceptions** | Severity filtering, type breakdown, 30-day trend, export |
| **Reconciliation** | NAV/settlement/cash/weight recon tabs, on-demand engine run |
| **Market Prices** | Candlestick charts, volume analysis, missing price detection |
| **Reports** | Generate PDF/Excel/CSV, pipeline history, report previews |
| **Settings** | Thresholds, database stats, platform info |

---

## Power BI Dashboards

11 dashboard pages designed with star schema and 30+ DAX measures:

1. Executive Overview
2. Daily NAV
3. Fund Performance
4. Portfolio Allocation
5. Trade Status
6. Settlement Status
7. Exception Dashboard
8. Operational KPIs
9. Cash Position
10. Tracking Error
11. Performance Attribution

Full DAX measure library and schema design: [`docs/powerbi/DAX_MEASURES.md`](docs/powerbi/DAX_MEASURES.md)

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Configuration

Key settings in `.env`:

```env
DB_TYPE=sqlite                    # or postgresql
PRICE_VARIANCE_THRESHOLD=0.05     # 5% price move threshold
NAV_TOLERANCE_BPS=5               # NAV variance tolerance
CASH_BREAK_THRESHOLD=1000.00      # Cash break detection threshold
TRACKING_ERROR_THRESHOLD=0.005    # Tracking error alert level
```

Fund definitions and sectors in `config/settings.yaml`.

---

## Roadmap

- [ ] Real-time trade feed integration (FIX protocol / Bloomberg B-PIPE)
- [ ] Machine learning for anomaly detection (Isolation Forest on price/volume)
- [ ] Automated exception resolution workflows with approval chains
- [ ] REST API layer (FastAPI) for external system integration
- [ ] Docker Compose for PostgreSQL + app containerization
- [ ] CI/CD pipeline with GitHub Actions
- [ ] Role-based access control for dashboard users
- [ ] Email/Slack alerting for CRITICAL exceptions
- [ ] Historical backtesting of reconciliation rule changes

---

## License

MIT License. See [LICENSE](LICENSE) for details.

## Author

**Moeez Malik** — [github.com/moeezislammalik](https://github.com/moeezislammalik)
