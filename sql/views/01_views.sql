-- Analytical views for reporting and dashboards

-- Latest NAV per fund
CREATE VIEW IF NOT EXISTS vw_latest_nav AS
SELECT
    f.fund_id,
    f.ticker,
    f.fund_name,
    n.nav_date,
    n.nav_per_share,
    n.total_nav,
    n.shares_outstanding,
    n.daily_return,
    n.benchmark_return,
    n.tracking_error
FROM funds f
INNER JOIN nav_history n ON f.fund_id = n.fund_id
WHERE n.nav_date = (
    SELECT MAX(nav_date) FROM nav_history n2 WHERE n2.fund_id = f.fund_id
);

-- Holdings with security details
CREATE VIEW IF NOT EXISTS vw_holdings_detail AS
SELECT
    h.holding_id,
    h.as_of_date,
    f.ticker AS fund_ticker,
    f.fund_name,
    s.ticker AS security_ticker,
    s.security_name,
    s.sector,
    s.security_type,
    h.quantity,
    h.market_value,
    h.cost_basis,
    mp.close_price AS latest_price
FROM holdings h
JOIN funds f ON h.fund_id = f.fund_id
JOIN securities s ON h.security_id = s.security_id
LEFT JOIN market_prices mp ON s.security_id = mp.security_id
    AND mp.price_date = h.as_of_date;

-- Open exceptions summary
CREATE VIEW IF NOT EXISTS vw_open_exceptions AS
SELECT
    e.exception_id,
    e.as_of_date,
    f.ticker AS fund_ticker,
    e.exception_type,
    e.severity,
    e.description,
    e.status,
    e.detected_at,
    e.assigned_to
FROM exceptions e
LEFT JOIN funds f ON e.fund_id = f.fund_id
WHERE e.status IN ('OPEN', 'INVESTIGATING');

-- Trade settlement status
CREATE VIEW IF NOT EXISTS vw_trade_settlement_status AS
SELECT
    t.trade_id,
    t.trade_date,
    t.settlement_date,
    f.ticker AS fund_ticker,
    s.ticker AS security_ticker,
    t.side,
    t.quantity,
    t.price,
    t.net_amount,
    t.trade_status,
    st.settlement_status,
    st.expected_amount,
    st.actual_amount,
    st.fail_reason
FROM trades t
JOIN funds f ON t.fund_id = f.fund_id
JOIN securities s ON t.security_id = s.security_id
LEFT JOIN settlements st ON t.trade_id = st.trade_id;

-- Portfolio allocation by sector
CREATE VIEW IF NOT EXISTS vw_sector_allocation AS
SELECT
    h.as_of_date,
    f.ticker AS fund_ticker,
    s.sector,
    SUM(h.market_value) AS sector_market_value,
    SUM(h.market_value) * 100.0 / SUM(SUM(h.market_value)) OVER (
        PARTITION BY h.fund_id, h.as_of_date
    ) AS sector_weight_pct
FROM holdings h
JOIN funds f ON h.fund_id = f.fund_id
JOIN securities s ON h.security_id = s.security_id
GROUP BY h.as_of_date, f.ticker, h.fund_id, s.sector;

-- Cash position summary
CREATE VIEW IF NOT EXISTS vw_cash_summary AS
SELECT
    cp.as_of_date,
    f.ticker AS fund_ticker,
    f.fund_name,
    cp.cash_balance,
    cp.accrued_expenses,
    cp.pending_settlements,
    cp.available_cash,
    cp.cash_balance * 100.0 / NULLIF(n.total_nav, 0) AS cash_pct_of_nav
FROM cash_positions cp
JOIN funds f ON cp.fund_id = f.fund_id
LEFT JOIN nav_history n ON f.fund_id = n.fund_id AND n.nav_date = cp.as_of_date;

-- Reconciliation KPIs
CREATE VIEW IF NOT EXISTS vw_operational_kpis AS
SELECT
    e.as_of_date,
    COUNT(*) AS total_exceptions,
    SUM(CASE WHEN e.severity = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_count,
    SUM(CASE WHEN e.severity = 'HIGH' THEN 1 ELSE 0 END) AS high_count,
    SUM(CASE WHEN e.status = 'OPEN' THEN 1 ELSE 0 END) AS open_count,
    SUM(CASE WHEN e.status = 'RESOLVED' THEN 1 ELSE 0 END) AS resolved_count
FROM exceptions e
GROUP BY e.as_of_date;

-- Fund performance metrics
CREATE VIEW IF NOT EXISTS vw_fund_performance AS
SELECT
    f.ticker,
    f.fund_name,
    f.benchmark,
    n.nav_date,
    n.nav_per_share,
    n.daily_return,
    n.benchmark_return,
    n.daily_return - n.benchmark_return AS excess_return,
    n.tracking_error
FROM nav_history n
JOIN funds f ON n.fund_id = f.fund_id;

-- Weight drift analysis
CREATE VIEW IF NOT EXISTS vw_weight_drift AS
SELECT
    pw.as_of_date,
    f.ticker AS fund_ticker,
    s.ticker AS security_ticker,
    s.security_name,
    pw.weight_pct,
    pw.target_weight,
    pw.drift_bps,
    CASE
        WHEN ABS(pw.drift_bps) > 50 THEN 'HIGH'
        WHEN ABS(pw.drift_bps) > 25 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS drift_severity
FROM portfolio_weights pw
JOIN funds f ON pw.fund_id = f.fund_id
JOIN securities s ON pw.security_id = s.security_id;
