# Power BI Dashboard Design
# ETF Portfolio Monitoring & Trade Reconciliation Platform

## Star Schema Design

### Dimension Tables

| Table | Key | Description |
|-------|-----|-------------|
| Dim_Fund | fund_id | ETF fund master (ticker, name, benchmark, asset class) |
| Dim_Security | security_id | Security master (CUSIP, ticker, sector, type) |
| Dim_Date | date_key | Date dimension (trading days, month, quarter, year) |
| Dim_Broker | broker | Trade execution brokers |
| Dim_ExceptionType | exception_type | Exception classification |

### Fact Tables

| Table | Grain | Measures |
|-------|-------|----------|
| Fact_NAV | fund_id × nav_date | nav_per_share, total_nav, daily_return, tracking_error |
| Fact_Holdings | fund_id × security_id × as_of_date | quantity, market_value, cost_basis |
| Fact_Trades | trade_id | quantity, price, gross_amount, net_amount |
| Fact_Settlements | settlement_id | expected_amount, actual_amount |
| Fact_Exceptions | exception_id | count (implicit) |
| Fact_Cash | fund_id × as_of_date | cash_balance, available_cash |
| Fact_PortfolioWeights | fund_id × security_id × as_of_date | weight_pct, target_weight, drift_bps |
| Fact_MarketPrices | security_id × price_date | open, high, low, close, volume |

### Relationships

```
Dim_Fund[ fund_id ] ──1:N──> Fact_NAV[ fund_id ]
Dim_Fund[ fund_id ] ──1:N──> Fact_Holdings[ fund_id ]
Dim_Fund[ fund_id ] ──1:N──> Fact_Trades[ fund_id ]
Dim_Security[ security_id ] ──1:N──> Fact_Holdings[ security_id ]
Dim_Security[ security_id ] ──1:N──> Fact_MarketPrices[ security_id ]
Dim_Date[ date_key ] ──1:N──> Fact_NAV[ nav_date ]
Fact_Trades[ trade_id ] ──1:1──> Fact_Settlements[ trade_id ]
```

## DAX Measures

### Executive Overview

```dax
Total AUM =
SUM(Fact_NAV[total_nav])

Fund Count =
DISTINCTCOUNT(Fact_NAV[fund_id])

Avg Daily Return =
AVERAGE(Fact_NAV[daily_return])

Avg Tracking Error =
AVERAGE(Fact_NAV[tracking_error])

Total Exceptions =
COUNTROWS(Fact_Exceptions)

Open Exceptions =
CALCULATE(
    COUNTROWS(Fact_Exceptions),
    Fact_Exceptions[status] = "OPEN"
)

Critical Exceptions =
CALCULATE(
    COUNTROWS(Fact_Exceptions),
    Fact_Exceptions[severity] = "CRITICAL"
)
```

### NAV & Performance

```dax
Latest NAV =
CALCULATE(
    SUM(Fact_NAV[nav_per_share]),
    LASTDATE(Dim_Date[date_key])
)

NAV Change =
VAR CurrentNAV = [Latest NAV]
VAR PreviousNAV =
    CALCULATE(
        SUM(Fact_NAV[nav_per_share]),
        PREVIOUSDAY(Dim_Date[date_key])
    )
RETURN CurrentNAV - PreviousNAV

YTD Return =
VAR StartOfYear = DATE(YEAR(MAX(Dim_Date[date_key])), 1, 1)
VAR StartNAV =
    CALCULATE(
        SUM(Fact_NAV[nav_per_share]),
        Dim_Date[date_key] = StartOfYear
    )
VAR EndNAV = [Latest NAV]
RETURN DIVIDE(EndNAV - StartNAV, StartNAV)

Sharpe Ratio =
VAR AvgReturn = AVERAGE(Fact_NAV[daily_return])
VAR StdDev = STDEV.P(Fact_NAV[daily_return])
VAR RiskFree = 0.045 / 252
RETURN DIVIDE(AvgReturn - RiskFree, StdDev) * SQRT(252)

Volatility =
STDEV.P(Fact_Nav[daily_return]) * SQRT(252)

Excess Return =
AVERAGE(Fact_NAV[daily_return]) - AVERAGE(Fact_NAV[benchmark_return])
```

### Portfolio Allocation

```dax
Total Market Value =
SUM(Fact_Holdings[market_value])

Sector Weight =
DIVIDE(
    SUM(Fact_Holdings[market_value]),
    CALCULATE(SUM(Fact_Holdings[market_value]), ALL(Dim_Security))
)

Top Holding Weight =
MAXX(
    TOPN(1, Fact_PortfolioWeights, Fact_PortfolioWeights[weight_pct]),
    Fact_PortfolioWeights[weight_pct]
)

Concentration Top 5 =
SUMX(
    TOPN(5, Fact_PortfolioWeights, Fact_PortfolioWeights[weight_pct]),
    Fact_PortfolioWeights[weight_pct]
)

Cash Exposure =
DIVIDE(
    SUM(Fact_Cash[cash_balance]),
    [Total AUM]
)
```

### Trade & Settlement

```dax
Trade Count =
COUNTROWS(Fact_Trades)

Trade Volume =
SUM(Fact_Trades[net_amount])

Buy Volume =
CALCULATE(SUM(Fact_Trades[net_amount]), Fact_Trades[side] = "BUY")

Sell Volume =
CALCULATE(SUM(Fact_Trades[net_amount]), Fact_Trades[side] = "SELL")

Failed Settlements =
CALCULATE(
    COUNTROWS(Fact_Settlements),
    Fact_Settlements[settlement_status] = "FAILED"
)

Settlement Rate =
DIVIDE(
    CALCULATE(COUNTROWS(Fact_Settlements),
        Fact_Settlements[settlement_status] = "SETTLED"),
    COUNTROWS(Fact_Settlements)
)

Settlement Variance =
SUM(Fact_Settlements[expected_amount]) - SUM(Fact_Settlements[actual_amount])
```

### Reconciliation & Exceptions

```dax
Exception Rate =
DIVIDE([Total Exceptions], [Fund Count])

Resolution Rate =
DIVIDE(
    CALCULATE(COUNTROWS(Fact_Exceptions),
        Fact_Exceptions[status] IN {"RESOLVED", "CLOSED"}),
    [Total Exceptions]
)

Avg Resolution Days =
AVERAGE(Fact_Exceptions[days_open])

NAV Variance BPS =
AVERAGE(Fact_DailyPricing[nav_variance_bps])

Cash Break Amount =
SUM(Fact_Cash[cash_balance]) - SUM(Fact_Cash[available_cash])
    - SUM(Fact_Cash[pending_settlements])
```

### Tracking Error & Attribution

```dax
Tracking Error Annualized =
STDEV.P(Fact_NAV[daily_return] - Fact_NAV[benchmark_return]) * SQRT(252)

Information Ratio =
DIVIDE(
    AVERAGE(Fact_NAV[daily_return] - Fact_NAV[benchmark_return]),
    [Tracking Error Annualized]
)

Portfolio Turnover =
VAR TotalTraded = SUM(Fact_Trades[net_amount])
VAR AvgNAV = AVERAGE(Fact_NAV[total_nav])
RETURN DIVIDE(TotalTraded / 2, AvgNAV)
```

## Dashboard Pages

### 1. Executive Overview
- KPI cards: Total AUM, Fund Count, Open Exceptions, Settlement Rate
- Line chart: AUM trend (30-day)
- Bar chart: Exceptions by severity
- Slicers: Date, Fund, Asset Class

### 2. Daily NAV
- Table: Fund NAV details with variance
- Line chart: NAV per share trend
- KPI: NAV variance bps, pricing status
- Slicer: Fund, Date range

### 3. Fund Performance
- Line chart: Daily return vs benchmark
- KPI cards: YTD Return, Sharpe, Volatility, Tracking Error
- Scatter: Return vs volatility by fund
- Slicer: Fund, Period

### 4. Portfolio Allocation
- Treemap: Sector allocation
- Donut: Asset type breakdown
- Bar: Top 10 holdings
- Table: Weight drift analysis

### 5. Trade Status
- Table: Trade blotter with filters
- Bar: Daily trade volume
- Pie: Trade status distribution
- Slicer: Fund, Side, Status, Date

### 6. Settlement Status
- KPI: Failed settlements, settlement rate
- Table: Failed settlement details
- Bar: Settlement status by fund
- Slicer: Date, Fund

### 7. Exception Dashboard
- Matrix: Exception type × severity
- Bar: Exception trend (30-day)
- Table: Open exceptions with aging
- Slicer: Severity, Status, Fund

### 8. Operational KPIs
- Card visuals: Resolution rate, exception rate, pipeline success
- Gauge: Settlement rate target (99%)
- Line: Daily exception count trend

### 9. Cash Position
- Bar: Cash balance by fund
- KPI: Cash exposure %, total cash
- Table: Cash break details

### 10. Tracking Error
- Line: Rolling 20-day tracking error
- Bar: Tracking error by fund
- KPI: Information ratio

### 11. Performance Attribution
- Waterfall: Sector contribution to return
- Bar: Sector weight vs contribution
- Table: Security-level attribution

## Theme Configuration

```
Background:       #1a1a2e (dark) / #ffffff (light)
Primary:          #0f3460
Accent:           #e94560
Positive:         #00b894
Negative:         #d63031
Warning:          #fdcb6e
Font:             Segoe UI
Visual border:    #16213e
```

## Data Connection

1. Export CSV files from `data/exports/` or connect directly to PostgreSQL
2. Use `scripts/export_for_powerbi.py` to generate star schema CSVs
3. Import into Power BI Desktop
4. Create relationships per star schema diagram
5. Add DAX measures from this document
6. Apply dark theme template
