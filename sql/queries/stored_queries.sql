-- Stored analytical queries for ETF operations

-- Query: Daily NAV reconciliation
-- name: q_daily_nav_reconciliation
SELECT
    dp.pricing_date,
    f.ticker,
    dp.official_nav,
    dp.calculated_nav,
    dp.nav_variance_bps,
    dp.pricing_status
FROM daily_pricing dp
JOIN funds f ON dp.fund_id = f.fund_id
WHERE dp.pricing_date = :as_of_date
ORDER BY ABS(dp.nav_variance_bps) DESC;

-- Query: Failed settlements report
-- name: q_failed_settlements
SELECT
    st.settlement_id,
    t.trade_id,
    f.ticker AS fund_ticker,
    s.ticker AS security_ticker,
    st.settlement_date,
    st.expected_amount,
    st.actual_amount,
    st.expected_amount - COALESCE(st.actual_amount, 0) AS variance,
    st.fail_reason
FROM settlements st
JOIN trades t ON st.trade_id = t.trade_id
JOIN funds f ON st.fund_id = f.fund_id
JOIN securities s ON t.security_id = s.security_id
WHERE st.settlement_status = 'FAILED'
  AND st.settlement_date >= :start_date
ORDER BY st.settlement_date DESC;

-- Query: Missing market prices
-- name: q_missing_prices
SELECT DISTINCT
    s.security_id,
    s.ticker,
    s.security_name,
    h.as_of_date AS missing_date
FROM holdings h
JOIN securities s ON h.security_id = s.security_id
LEFT JOIN market_prices mp ON s.security_id = mp.security_id
    AND mp.price_date = h.as_of_date
WHERE mp.price_id IS NULL
  AND h.as_of_date = :as_of_date;

-- Query: Cash break detection
-- name: q_cash_breaks
SELECT
    cp.as_of_date,
    f.ticker,
    cp.cash_balance,
    cp.pending_settlements,
    cp.available_cash,
    cp.cash_balance - cp.available_cash - cp.pending_settlements AS cash_break
FROM cash_positions cp
JOIN funds f ON cp.fund_id = f.fund_id
WHERE cp.as_of_date = :as_of_date
  AND ABS(cp.cash_balance - cp.available_cash - cp.pending_settlements) > :threshold;

-- Query: Top holdings concentration
-- name: q_concentration_risk
SELECT
    f.ticker AS fund_ticker,
    s.ticker AS security_ticker,
    s.security_name,
    pw.weight_pct,
    RANK() OVER (PARTITION BY pw.fund_id ORDER BY pw.weight_pct DESC) AS rank
FROM portfolio_weights pw
JOIN funds f ON pw.fund_id = f.fund_id
JOIN securities s ON pw.security_id = s.security_id
WHERE pw.as_of_date = :as_of_date
  AND pw.weight_pct > :threshold_pct;

-- Query: Trade volume by fund
-- name: q_trade_volume
SELECT
    f.ticker,
    DATE(t.trade_date) AS trade_date,
    COUNT(*) AS trade_count,
    SUM(CASE WHEN t.side = 'BUY' THEN t.net_amount ELSE 0 END) AS buy_volume,
    SUM(CASE WHEN t.side = 'SELL' THEN t.net_amount ELSE 0 END) AS sell_volume,
    SUM(t.net_amount) AS total_volume
FROM trades t
JOIN funds f ON t.fund_id = f.fund_id
WHERE t.trade_date BETWEEN :start_date AND :end_date
GROUP BY f.ticker, DATE(t.trade_date)
ORDER BY trade_date DESC, f.ticker;

-- Query: Exception aging report
-- name: q_exception_aging
SELECT
    e.exception_id,
    f.ticker AS fund_ticker,
    e.exception_type,
    e.severity,
    e.status,
    e.as_of_date,
    JULIANDAY('now') - JULIANDAY(e.detected_at) AS days_open,
    e.assigned_to
FROM exceptions e
LEFT JOIN funds f ON e.fund_id = f.fund_id
WHERE e.status IN ('OPEN', 'INVESTIGATING')
ORDER BY e.severity DESC, days_open DESC;

-- Query: Tracking error history
-- name: q_tracking_error
SELECT
    f.ticker,
    n.nav_date,
    n.tracking_error,
    n.daily_return,
    n.benchmark_return,
    n.daily_return - n.benchmark_return AS excess_return
FROM nav_history n
JOIN funds f ON n.fund_id = f.fund_id
WHERE n.nav_date BETWEEN :start_date AND :end_date
ORDER BY f.ticker, n.nav_date;

-- Query: Duplicate trade detection
-- name: q_duplicate_trades
SELECT
    t1.trade_id AS trade_id_1,
    t2.trade_id AS trade_id_2,
    f.ticker,
    s.ticker AS security_ticker,
    t1.trade_date,
    t1.quantity,
    t1.price
FROM trades t1
JOIN trades t2 ON t1.fund_id = t2.fund_id
    AND t1.security_id = t2.security_id
    AND t1.trade_date = t2.trade_date
    AND t1.side = t2.side
    AND t1.quantity = t2.quantity
    AND t1.trade_id < t2.trade_id
JOIN funds f ON t1.fund_id = f.fund_id
JOIN securities s ON t1.security_id = s.security_id
WHERE t1.trade_date >= :start_date;

-- Query: Portfolio turnover
-- name: q_portfolio_turnover
SELECT
    f.ticker,
    SUM(CASE WHEN t.side = 'BUY' THEN t.net_amount ELSE 0 END) AS total_buys,
    SUM(CASE WHEN t.side = 'SELL' THEN t.net_amount ELSE 0 END) AS total_sells,
    (SUM(CASE WHEN t.side = 'BUY' THEN t.net_amount ELSE 0 END) +
     SUM(CASE WHEN t.side = 'SELL' THEN t.net_amount ELSE 0 END)) / 2.0 AS avg_traded,
    n.total_nav,
    ((SUM(CASE WHEN t.side = 'BUY' THEN t.net_amount ELSE 0 END) +
      SUM(CASE WHEN t.side = 'SELL' THEN t.net_amount ELSE 0 END)) / 2.0)
     / NULLIF(n.total_nav, 0) * 100 AS turnover_pct
FROM trades t
JOIN funds f ON t.fund_id = f.fund_id
JOIN nav_history n ON f.fund_id = n.fund_id
WHERE t.trade_date BETWEEN :start_date AND :end_date
  AND n.nav_date = :end_date
GROUP BY f.ticker, n.total_nav;
