-- ETF Portfolio Monitoring & Trade Reconciliation Platform
-- Normalized schema for ETF operations

-- ============================================================
-- DIMENSION / REFERENCE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS funds (
    fund_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          VARCHAR(10) NOT NULL UNIQUE,
    fund_name       VARCHAR(255) NOT NULL,
    benchmark       VARCHAR(20) NOT NULL,
    asset_class     VARCHAR(50) NOT NULL,
    inception_date  DATE NOT NULL,
    expense_ratio   DECIMAL(8, 6) NOT NULL,
    aum_billions    DECIMAL(14, 2),
    currency        VARCHAR(3) DEFAULT 'USD',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS securities (
    security_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    cusip           VARCHAR(12) NOT NULL UNIQUE,
    ticker          VARCHAR(20),
    security_name   VARCHAR(255) NOT NULL,
    security_type   VARCHAR(50) NOT NULL,
    sector          VARCHAR(100),
    country         VARCHAR(3) DEFAULT 'USA',
    currency        VARCHAR(3) DEFAULT 'USD',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS corporate_actions (
    action_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    security_id     INTEGER NOT NULL,
    action_type     VARCHAR(50) NOT NULL,  -- DIVIDEND, SPLIT, MERGER, SPINOFF
    ex_date         DATE NOT NULL,
    record_date     DATE,
    pay_date        DATE,
    ratio           DECIMAL(12, 6),
    cash_amount     DECIMAL(14, 4),
    description     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (security_id) REFERENCES securities(security_id)
);

-- ============================================================
-- FACT / TRANSACTIONAL TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS holdings (
    holding_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id         INTEGER NOT NULL,
    security_id     INTEGER NOT NULL,
    as_of_date      DATE NOT NULL,
    quantity        DECIMAL(18, 4) NOT NULL,
    market_value    DECIMAL(18, 2) NOT NULL,
    cost_basis      DECIMAL(18, 2),
    accrued_income  DECIMAL(14, 4) DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_id) REFERENCES funds(fund_id),
    FOREIGN KEY (security_id) REFERENCES securities(security_id),
    UNIQUE (fund_id, security_id, as_of_date)
);

CREATE TABLE IF NOT EXISTS trades (
    trade_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id         INTEGER NOT NULL,
    security_id     INTEGER NOT NULL,
    trade_date      DATE NOT NULL,
    settlement_date DATE NOT NULL,
    side            VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity        DECIMAL(18, 4) NOT NULL,
    price           DECIMAL(14, 6) NOT NULL,
    gross_amount    DECIMAL(18, 2) NOT NULL,
    commission      DECIMAL(10, 2) DEFAULT 0,
    net_amount      DECIMAL(18, 2) NOT NULL,
    broker          VARCHAR(100),
    trade_status    VARCHAR(20) DEFAULT 'PENDING'
                    CHECK (trade_status IN ('PENDING', 'CONFIRMED', 'SETTLED', 'FAILED', 'CANCELLED')),
    external_ref    VARCHAR(50),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_id) REFERENCES funds(fund_id),
    FOREIGN KEY (security_id) REFERENCES securities(security_id)
);

CREATE TABLE IF NOT EXISTS market_prices (
    price_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    security_id     INTEGER NOT NULL,
    price_date      DATE NOT NULL,
    open_price      DECIMAL(14, 6),
    high_price      DECIMAL(14, 6),
    low_price       DECIMAL(14, 6),
    close_price     DECIMAL(14, 6) NOT NULL,
    volume          BIGINT,
    source          VARCHAR(50) DEFAULT 'BLOOMBERG',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (security_id) REFERENCES securities(security_id),
    UNIQUE (security_id, price_date)
);

CREATE TABLE IF NOT EXISTS nav_history (
    nav_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id         INTEGER NOT NULL,
    nav_date        DATE NOT NULL,
    nav_per_share   DECIMAL(14, 6) NOT NULL,
    total_nav       DECIMAL(18, 2) NOT NULL,
    shares_outstanding BIGINT NOT NULL,
    daily_return    DECIMAL(10, 8),
    benchmark_return DECIMAL(10, 8),
    tracking_error  DECIMAL(10, 8),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_id) REFERENCES funds(fund_id),
    UNIQUE (fund_id, nav_date)
);

CREATE TABLE IF NOT EXISTS settlements (
    settlement_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id        INTEGER NOT NULL,
    fund_id         INTEGER NOT NULL,
    settlement_date DATE NOT NULL,
    expected_amount DECIMAL(18, 2) NOT NULL,
    actual_amount   DECIMAL(18, 2),
    settlement_status VARCHAR(20) DEFAULT 'PENDING'
                    CHECK (settlement_status IN ('PENDING', 'SETTLED', 'FAILED', 'PARTIAL')),
    fail_reason     VARCHAR(255),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trade_id) REFERENCES trades(trade_id),
    FOREIGN KEY (fund_id) REFERENCES funds(fund_id)
);

CREATE TABLE IF NOT EXISTS cash_positions (
    cash_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id         INTEGER NOT NULL,
    as_of_date      DATE NOT NULL,
    cash_balance    DECIMAL(18, 2) NOT NULL,
    accrued_expenses DECIMAL(14, 2) DEFAULT 0,
    pending_settlements DECIMAL(18, 2) DEFAULT 0,
    available_cash  DECIMAL(18, 2) NOT NULL,
    currency        VARCHAR(3) DEFAULT 'USD',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_id) REFERENCES funds(fund_id),
    UNIQUE (fund_id, as_of_date)
);

CREATE TABLE IF NOT EXISTS portfolio_weights (
    weight_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id         INTEGER NOT NULL,
    security_id     INTEGER NOT NULL,
    as_of_date      DATE NOT NULL,
    weight_pct      DECIMAL(10, 6) NOT NULL,
    target_weight   DECIMAL(10, 6),
    drift_bps       DECIMAL(10, 4),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_id) REFERENCES funds(fund_id),
    FOREIGN KEY (security_id) REFERENCES securities(security_id),
    UNIQUE (fund_id, security_id, as_of_date)
);

CREATE TABLE IF NOT EXISTS exceptions (
    exception_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id         INTEGER,
    exception_type  VARCHAR(100) NOT NULL,
    severity        VARCHAR(10) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    description     TEXT NOT NULL,
    reference_id    VARCHAR(50),
    reference_table VARCHAR(50),
    as_of_date      DATE NOT NULL,
    status          VARCHAR(20) DEFAULT 'OPEN'
                    CHECK (status IN ('OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED')),
    assigned_to     VARCHAR(100),
    resolution_notes TEXT,
    detected_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at     TIMESTAMP,
    FOREIGN KEY (fund_id) REFERENCES funds(fund_id)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date        DATE NOT NULL,
    pipeline_name   VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL,
    records_processed INTEGER DEFAULT 0,
    exceptions_found INTEGER DEFAULT 0,
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS daily_pricing (
    pricing_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id         INTEGER NOT NULL,
    pricing_date    DATE NOT NULL,
    official_nav    DECIMAL(14, 6) NOT NULL,
    calculated_nav  DECIMAL(14, 6) NOT NULL,
    nav_variance_bps DECIMAL(10, 4),
    pricing_status  VARCHAR(20) DEFAULT 'PENDING'
                    CHECK (pricing_status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXCEPTION')),
    approved_by     VARCHAR(100),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_id) REFERENCES funds(fund_id),
    UNIQUE (fund_id, pricing_date)
);
