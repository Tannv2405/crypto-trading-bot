-- Trading Bot Database Schema
-- PostgreSQL database schema for the trading bot

-- Create database (run this manually if needed)
-- CREATE DATABASE trading_bot;

-- Market data table to store OHLCV data
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open_price DECIMAL(20, 8) NOT NULL,
    high_price DECIMAL(20, 8) NOT NULL,
    low_price DECIMAL(20, 8) NOT NULL,
    close_price DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);

-- Trade orders table to store all trading activity
CREATE TABLE IF NOT EXISTS trade_orders (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    order_type VARCHAR(10) NOT NULL CHECK (order_type IN ('BUY', 'SELL')),
    strategy VARCHAR(50) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    amount DECIMAL(20, 8) NOT NULL,
    total_value DECIMAL(20, 8) NOT NULL,
    balance_usd DECIMAL(20, 8) NOT NULL,
    balance_crypto DECIMAL(20, 8) NOT NULL,
    short_sma DECIMAL(20, 8),
    long_sma DECIMAL(20, 8),
    rsi DECIMAL(10, 4),
    reason TEXT,
    is_paper_trade BOOLEAN DEFAULT TRUE,
    exchange_order_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Portfolio snapshots table to track portfolio value over time
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    total_value_usd DECIMAL(20, 8) NOT NULL,
    cash_balance DECIMAL(20, 8) NOT NULL,
    crypto_balance DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8) NOT NULL,
    profit_loss DECIMAL(20, 8) NOT NULL,
    profit_loss_percent DECIMAL(10, 4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Strategy performance table to track strategy metrics
CREATE TABLE IF NOT EXISTS strategy_performance (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_profit_loss DECIMAL(20, 8) DEFAULT 0,
    win_rate DECIMAL(10, 4) DEFAULT 0,
    avg_profit DECIMAL(20, 8) DEFAULT 0,
    avg_loss DECIMAL(20, 8) DEFAULT 0,
    max_drawdown DECIMAL(10, 4) DEFAULT 0,
    sharpe_ratio DECIMAL(10, 4) DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(strategy_name, symbol)
);

-- Bot status table to track bot state
CREATE TABLE IF NOT EXISTS bot_status (
    id SERIAL PRIMARY KEY,
    bot_name VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'STOPPED',
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    current_position VARCHAR(10),
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Event log table to track all order history and errors
CREATE TABLE IF NOT EXISTS event_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL, -- ORDER_ATTEMPT, ORDER_SUCCESS, ORDER_FAILED, SIGNAL_GENERATED, ERROR, SYSTEM_EVENT
    event_category VARCHAR(30) NOT NULL, -- TRADING, SYSTEM, ERROR, NOTIFICATION, STRATEGY
    symbol VARCHAR(20), -- Trading pair (nullable for system events)
    strategy VARCHAR(50), -- Strategy name (nullable for system events)
    severity VARCHAR(20) DEFAULT 'INFO', -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    message TEXT NOT NULL, -- Human-readable event description
    details JSONB DEFAULT '{}', -- Structured event data (order details, error info, etc.)
    
    -- Order-specific fields (nullable for non-order events)
    order_type VARCHAR(10), -- BUY, SELL (nullable)
    order_status VARCHAR(20), -- PENDING, COMPLETED, FAILED, CANCELLED (nullable)
    price DECIMAL(20, 8), -- Order price (nullable)
    amount DECIMAL(20, 8), -- Order amount (nullable)
    total_value DECIMAL(20, 8), -- Order total value (nullable)
    
    -- Error-specific fields (nullable for non-error events)
    error_code VARCHAR(50), -- Error classification code (nullable)
    error_message TEXT, -- Detailed error message (nullable)
    stack_trace TEXT, -- Full stack trace for debugging (nullable)
    
    -- Context fields
    bot_name VARCHAR(50) DEFAULT 'trading_bot',
    session_id VARCHAR(100), -- Bot session identifier (nullable)
    correlation_id VARCHAR(100), -- For tracking related events (nullable)
    user_id VARCHAR(50), -- User who triggered the event (nullable)
    
    -- Metadata
    source_file VARCHAR(100), -- Source code file where event occurred (nullable)
    source_function VARCHAR(100), -- Function name where event occurred (nullable)
    execution_time_ms INTEGER, -- Event processing time in milliseconds (nullable)
    
    -- Timestamps
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Global system configuration table
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) NOT NULL DEFAULT 'string', -- string, integer, float, boolean, json
    description TEXT,
    category VARCHAR(50) DEFAULT 'general', -- general, system, notification, risk
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT 'system'
);

-- Trading pairs configuration table
CREATE TABLE IF NOT EXISTS trading_pairs (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE, -- e.g., 'BTC/USDT', 'ETH/USDT'
    base_currency VARCHAR(10) NOT NULL, -- e.g., 'BTC', 'ETH'
    quote_currency VARCHAR(10) NOT NULL, -- e.g., 'USDT', 'USD'
    is_active BOOLEAN DEFAULT TRUE,
    initial_balance DECIMAL(20, 8) DEFAULT 1000.00,
    trade_size_usd DECIMAL(20, 8) DEFAULT 100.00,
    max_position_percent DECIMAL(10, 4) DEFAULT 20.00, -- Max % of total portfolio
    min_trade_amount DECIMAL(20, 8) DEFAULT 0.001,
    max_trade_amount DECIMAL(20, 8) DEFAULT 10000.00,
    price_precision INTEGER DEFAULT 2,
    amount_precision INTEGER DEFAULT 6,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Available trading strategies table
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(50) NOT NULL UNIQUE, -- e.g., 'sma_crossover', 'rsi', 'macd'
    display_name VARCHAR(100) NOT NULL, -- e.g., 'SMA Crossover', 'RSI Strategy'
    description TEXT,
    strategy_type VARCHAR(20) DEFAULT 'technical', -- technical, fundamental, hybrid
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Strategy configuration per trading pair
CREATE TABLE IF NOT EXISTS pair_strategy_config (
    id SERIAL PRIMARY KEY,
    pair_id INTEGER NOT NULL REFERENCES trading_pairs(id) ON DELETE CASCADE,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    is_enabled BOOLEAN DEFAULT TRUE,
    weight DECIMAL(5, 4) DEFAULT 1.0000, -- Strategy weight in combined signals (0.0 to 1.0)
    parameters JSONB NOT NULL DEFAULT '{}', -- Strategy-specific parameters
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pair_id, strategy_id)
);

-- Risk management configuration per trading pair
CREATE TABLE IF NOT EXISTS pair_risk_config (
    id SERIAL PRIMARY KEY,
    pair_id INTEGER NOT NULL REFERENCES trading_pairs(id) ON DELETE CASCADE,
    stop_loss_percent DECIMAL(10, 4) DEFAULT 5.0000,
    take_profit_percent DECIMAL(10, 4) DEFAULT 10.0000,
    max_daily_trades INTEGER DEFAULT 10,
    max_daily_loss_percent DECIMAL(10, 4) DEFAULT 5.0000,
    trailing_stop_enabled BOOLEAN DEFAULT FALSE,
    trailing_stop_percent DECIMAL(10, 4) DEFAULT 2.0000,
    max_drawdown_percent DECIMAL(10, 4) DEFAULT 15.0000,
    position_sizing_method VARCHAR(20) DEFAULT 'fixed', -- fixed, percent, kelly, volatility
    volatility_lookback_days INTEGER DEFAULT 30,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pair_id)
);

-- Insert default system configuration
INSERT INTO system_config (config_key, config_value, config_type, description, category) VALUES
-- System Settings
('paper_trading', 'true', 'boolean', 'Enable paper trading mode globally', 'system'),
('check_interval', '60', 'integer', 'Seconds between market checks', 'system'),
('max_concurrent_positions', '3', 'integer', 'Maximum concurrent positions across all pairs', 'system'),
('total_portfolio_balance', '10000', 'float', 'Total portfolio balance in USD', 'system'),
('rebalance_interval_hours', '24', 'integer', 'Hours between portfolio rebalancing', 'system'),

-- Notification Settings
('telegram_enabled', 'true', 'boolean', 'Enable Telegram notifications', 'notification'),
('notify_on_trades', 'true', 'boolean', 'Send notifications for trades', 'notification'),
('notify_on_signals', 'false', 'boolean', 'Send notifications for trading signals', 'notification'),
('notify_on_errors', 'true', 'boolean', 'Send notifications for errors', 'notification'),
('daily_summary_enabled', 'true', 'boolean', 'Send daily trading summary', 'notification'),

-- Global Risk Settings
('global_max_daily_loss_percent', '10.0', 'float', 'Maximum daily loss across all pairs', 'risk'),
('correlation_check_enabled', 'true', 'boolean', 'Check correlation between pairs', 'risk'),
('emergency_stop_enabled', 'true', 'boolean', 'Enable emergency stop on major losses', 'risk'),
('emergency_stop_loss_percent', '20.0', 'float', 'Emergency stop loss percentage', 'risk'),

-- Advanced Settings
('min_price_history', '50', 'integer', 'Minimum price history before trading', 'general'),
('log_level', 'INFO', 'string', 'Logging level', 'general'),
('enable_backtesting', 'false', 'boolean', 'Enable backtesting mode', 'general'),
('data_retention_days', '365', 'integer', 'Days to retain market data', 'general')

ON CONFLICT (config_key) DO NOTHING;

-- Insert default trading pairs
INSERT INTO trading_pairs (symbol, base_currency, quote_currency, is_active, initial_balance, trade_size_usd, max_position_percent) VALUES
('BTC/USDT', 'BTC', 'USDT', true, 3000.00, 200.00, 30.00),
('ETH/USDT', 'ETH', 'USDT', true, 2500.00, 150.00, 25.00),
('DOT/USDT', 'DOT', 'USDT', true, 1000.00, 70.00, 10.00)
ON CONFLICT (symbol) DO NOTHING;

-- Insert available strategies
INSERT INTO strategies (strategy_name, display_name, description, strategy_type) VALUES
('sma_crossover', 'SMA Crossover', 'Simple Moving Average crossover strategy', 'technical'),
('rsi', 'RSI Strategy', 'Relative Strength Index overbought/oversold strategy', 'technical'),
('macd', 'MACD Strategy', 'Moving Average Convergence Divergence strategy', 'technical'),
('bollinger_bands', 'Bollinger Bands', 'Bollinger Bands mean reversion strategy', 'technical'),
('stochastic', 'Stochastic Oscillator', 'Stochastic momentum strategy', 'technical')
ON CONFLICT (strategy_name) DO NOTHING;

-- Configure strategies for each trading pair
INSERT INTO pair_strategy_config (pair_id, strategy_id, is_enabled, weight, parameters) 
SELECT 
    tp.id as pair_id,
    s.id as strategy_id,
    true as is_enabled,
    CASE 
        WHEN s.strategy_name = 'sma_crossover' THEN 0.6
        WHEN s.strategy_name = 'rsi' THEN 0.4
        ELSE 0.3
    END as weight,
    CASE 
        WHEN s.strategy_name = 'sma_crossover' THEN 
            CASE tp.symbol
                WHEN 'BTC/USDT' THEN '{"short_period": 10, "long_period": 30}'::jsonb
                WHEN 'ETH/USDT' THEN '{"short_period": 12, "long_period": 26}'::jsonb
                WHEN 'SOL/USDT' THEN '{"short_period": 8, "long_period": 21}'::jsonb
                WHEN 'ADA/USDT' THEN '{"short_period": 10, "long_period": 30}'::jsonb
                WHEN 'DOT/USDT' THEN '{"short_period": 9, "long_period": 25}'::jsonb
                ELSE '{"short_period": 10, "long_period": 30}'::jsonb
            END
        WHEN s.strategy_name = 'rsi' THEN 
            CASE tp.symbol
                WHEN 'BTC/USDT' THEN '{"rsi_period": 14, "overbought_threshold": 70, "oversold_threshold": 30}'::jsonb
                WHEN 'ETH/USDT' THEN '{"rsi_period": 14, "overbought_threshold": 75, "oversold_threshold": 25}'::jsonb
                ELSE '{"rsi_period": 14, "overbought_threshold": 70, "oversold_threshold": 30}'::jsonb
            END
        ELSE '{}'::jsonb
    END as parameters
FROM trading_pairs tp
CROSS JOIN strategies s
WHERE s.strategy_name IN ('sma_crossover', 'rsi')
ON CONFLICT (pair_id, strategy_id) DO NOTHING;

-- Configure risk management for each trading pair
INSERT INTO pair_risk_config (pair_id, stop_loss_percent, take_profit_percent, max_daily_trades, max_daily_loss_percent)
SELECT 
    tp.id as pair_id,
    CASE tp.symbol
        WHEN 'BTC/USDT' THEN 5.0
        WHEN 'ETH/USDT' THEN 6.0
        WHEN 'SOL/USDT' THEN 7.0
        WHEN 'ADA/USDT' THEN 8.0
        WHEN 'DOT/USDT' THEN 8.0
        ELSE 5.0
    END as stop_loss_percent,
    CASE tp.symbol
        WHEN 'BTC/USDT' THEN 10.0
        WHEN 'ETH/USDT' THEN 12.0
        WHEN 'SOL/USDT' THEN 15.0
        WHEN 'ADA/USDT' THEN 16.0
        WHEN 'DOT/USDT' THEN 18.0
        ELSE 10.0
    END as take_profit_percent,
    CASE tp.symbol
        WHEN 'BTC/USDT' THEN 8
        WHEN 'ETH/USDT' THEN 6
        ELSE 5
    END as max_daily_trades,
    CASE tp.symbol
        WHEN 'BTC/USDT' THEN 3.0
        WHEN 'ETH/USDT' THEN 4.0
        ELSE 5.0
    END as max_daily_loss_percent
FROM trading_pairs tp
ON CONFLICT (pair_id) DO NOTHING;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trade_orders_symbol_created ON trade_orders(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trade_orders_strategy ON trade_orders(strategy);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_timestamp ON portfolio_snapshots(timestamp DESC);

-- Event log indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_event_log_event_type ON event_log(event_type);
CREATE INDEX IF NOT EXISTS idx_event_log_category ON event_log(event_category);
CREATE INDEX IF NOT EXISTS idx_event_log_symbol ON event_log(symbol);
CREATE INDEX IF NOT EXISTS idx_event_log_strategy ON event_log(strategy);
CREATE INDEX IF NOT EXISTS idx_event_log_severity ON event_log(severity);
CREATE INDEX IF NOT EXISTS idx_event_log_timestamp ON event_log(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_event_log_bot_session ON event_log(bot_name, session_id);
CREATE INDEX IF NOT EXISTS idx_event_log_correlation ON event_log(correlation_id);
CREATE INDEX IF NOT EXISTS idx_event_log_order_status ON event_log(order_status);

-- New indexes for multi-pair configuration
CREATE INDEX IF NOT EXISTS idx_system_config_category ON system_config(category);
CREATE INDEX IF NOT EXISTS idx_system_config_active ON system_config(is_active);
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key);
CREATE INDEX IF NOT EXISTS idx_trading_pairs_active ON trading_pairs(is_active);
CREATE INDEX IF NOT EXISTS idx_trading_pairs_symbol ON trading_pairs(symbol);
CREATE INDEX IF NOT EXISTS idx_strategies_active ON strategies(is_active);
CREATE INDEX IF NOT EXISTS idx_pair_strategy_config_enabled ON pair_strategy_config(is_enabled);
CREATE INDEX IF NOT EXISTS idx_pair_strategy_config_pair ON pair_strategy_config(pair_id);
CREATE INDEX IF NOT EXISTS idx_pair_risk_config_pair ON pair_risk_config(pair_id);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at columns
CREATE TRIGGER update_trade_orders_updated_at 
    BEFORE UPDATE ON trade_orders 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at 
    BEFORE UPDATE ON system_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trading_pairs_updated_at 
    BEFORE UPDATE ON trading_pairs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pair_strategy_config_updated_at 
    BEFORE UPDATE ON pair_strategy_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pair_risk_config_updated_at 
    BEFORE UPDATE ON pair_risk_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();