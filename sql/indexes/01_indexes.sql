-- Performance indexes for ETF operations queries

CREATE INDEX IF NOT EXISTS idx_holdings_fund_date ON holdings(fund_id, as_of_date);
CREATE INDEX IF NOT EXISTS idx_holdings_security_date ON holdings(security_id, as_of_date);
CREATE INDEX IF NOT EXISTS idx_trades_fund_date ON trades(fund_id, trade_date);
CREATE INDEX IF NOT EXISTS idx_trades_settlement ON trades(settlement_date, trade_status);
CREATE INDEX IF NOT EXISTS idx_trades_security ON trades(security_id);
CREATE INDEX IF NOT EXISTS idx_market_prices_security_date ON market_prices(security_id, price_date);
CREATE INDEX IF NOT EXISTS idx_nav_history_fund_date ON nav_history(fund_id, nav_date);
CREATE INDEX IF NOT EXISTS idx_settlements_status ON settlements(settlement_status, settlement_date);
CREATE INDEX IF NOT EXISTS idx_settlements_trade ON settlements(trade_id);
CREATE INDEX IF NOT EXISTS idx_cash_positions_fund_date ON cash_positions(fund_id, as_of_date);
CREATE INDEX IF NOT EXISTS idx_portfolio_weights_fund_date ON portfolio_weights(fund_id, as_of_date);
CREATE INDEX IF NOT EXISTS idx_exceptions_status ON exceptions(status, severity);
CREATE INDEX IF NOT EXISTS idx_exceptions_fund_date ON exceptions(fund_id, as_of_date);
CREATE INDEX IF NOT EXISTS idx_exceptions_type ON exceptions(exception_type);
CREATE INDEX IF NOT EXISTS idx_daily_pricing_fund_date ON daily_pricing(fund_id, pricing_date);
CREATE INDEX IF NOT EXISTS idx_securities_sector ON securities(sector);
CREATE INDEX IF NOT EXISTS idx_securities_type ON securities(security_type);
CREATE INDEX IF NOT EXISTS idx_corporate_actions_security ON corporate_actions(security_id, ex_date);
