-- ============================================
-- TRADING DASHBOARD - DATABASE SCHEMA
-- ============================================

-- Drop existing tables (if any) - CAREFUL! This deletes all data
DROP TABLE IF EXISTS entry_tracking CASCADE;
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS indicators CASCADE;
DROP TABLE IF EXISTS candles CASCADE;
DROP TABLE IF EXISTS settings CASCADE;

-- ============================================
-- TABLE 1: CANDLES (Price Data)
-- ============================================
CREATE TABLE candles (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,                    -- BTC/USDT, POL, SNGP
    timeframe VARCHAR(10) NOT NULL,                 -- 1h, 15m, 1D
    timestamp BIGINT NOT NULL,                      -- Unix timestamp (milliseconds)
    datetime TIMESTAMP NOT NULL,                    -- Human-readable datetime
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure no duplicate candles
    UNIQUE(symbol, timeframe, timestamp)
);

-- Index for fast queries
CREATE INDEX idx_candles_symbol_time ON candles(symbol, timeframe, timestamp DESC);
CREATE INDEX idx_candles_datetime ON candles(datetime DESC);

-- ============================================
-- TABLE 2: INDICATORS (Calculated Values)
-- ============================================
CREATE TABLE indicators (
    id SERIAL PRIMARY KEY,
    candle_id INTEGER NOT NULL REFERENCES candles(id) ON DELETE CASCADE,
    
    -- RSI
    rsi DECIMAL(10, 4),
    rsi_ema DECIMAL(10, 4),
    
    -- MACD
    macd_line DECIMAL(20, 8),
    macd_signal DECIMAL(20, 8),
    macd_histogram DECIMAL(20, 8),
    
    -- ADX & DI
    adx DECIMAL(10, 4),
    di_plus DECIMAL(10, 4),
    di_minus DECIMAL(10, 4),
    
    -- OBV
    obv DECIMAL(20, 2),
    obv_ma DECIMAL(20, 2),
    
    -- EMAs
    ema_44 DECIMAL(20, 8),
    ema_100 DECIMAL(20, 8),
    ema_200 DECIMAL(20, 8),
    
    -- SuperTrend
    supertrend_1 DECIMAL(20, 8),
    supertrend_1_direction VARCHAR(10),  -- UP or DN
    supertrend_2 DECIMAL(20, 8),
    supertrend_2_direction VARCHAR(10),
    
    -- Bollinger Bands
    bb_basis DECIMAL(20, 8),
    bb_upper_1 DECIMAL(20, 8),
    bb_lower_1 DECIMAL(20, 8),
    bb_upper_2 DECIMAL(20, 8),
    bb_lower_2 DECIMAL(20, 8),
    bb_upper_3 DECIMAL(20, 8),
    bb_lower_3 DECIMAL(20, 8),
    bb_squeeze BOOLEAN,
    bb_position VARCHAR(10),  -- BB3↓, BB2↓, BB1↓, BB~, BB1↑, BB2↑, BB3↑
    
    -- VWAP
    vwap DECIMAL(20, 8),
    
    -- ATR
    atr DECIMAL(20, 8),
    
    -- Volume Analysis
    volume_avg DECIMAL(20, 8),
    volume_signal VARCHAR(5),  -- H, N, L
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(candle_id)
);

CREATE INDEX idx_indicators_candle ON indicators(candle_id);

-- ============================================
-- TABLE 3: SIGNALS (BUY/SELL Signals)
-- ============================================
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    candle_id INTEGER NOT NULL REFERENCES candles(id) ON DELETE CASCADE,
    
    -- Signal Info
    signal VARCHAR(20) NOT NULL,  -- A-BUY, BUY, EARLY-BUY, WATCH, CAUTION, SELL
    score DECIMAL(10, 2) NOT NULL,
    max_score DECIMAL(10, 2) NOT NULL,
    timeframe_type VARCHAR(20),  -- Intraday, Swing
    
    -- Entry Details (if BUY signal)
    entry_price DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    target DECIMAL(20, 8),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(candle_id)
);

CREATE INDEX idx_signals_candle ON signals(candle_id);
CREATE INDEX idx_signals_signal ON signals(signal);
CREATE INDEX idx_signals_created ON signals(created_at DESC);

-- ============================================
-- TABLE 4: ENTRY TRACKING (Position Management)
-- ============================================
CREATE TABLE entry_tracking (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    
    -- Entry State
    state VARCHAR(20) NOT NULL,  -- NONE, VALIDATING, TRACKING, EXITED
    entry_price DECIMAL(20, 8),
    entry_time TIMESTAMP,
    entry_signal VARCHAR(20),  -- A-BUY, BUY, EARLY-BUY
    
    -- Price Tracking
    peak_price DECIMAL(20, 8),
    lowest_price DECIMAL(20, 8),
    
    -- Exit System
    exit_stage INTEGER DEFAULT 0,  -- 0=VALID, 1=EXIT-1, 2=EXIT-2, 3=EXIT-3
    exit_1_level DECIMAL(20, 8),
    exit_2_level DECIMAL(20, 8),
    exit_3_level DECIMAL(20, 8),
    
    -- Exit Info
    exit_reason VARCHAR(50),
    exit_time TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(symbol, timeframe)
);

CREATE INDEX idx_entry_symbol_tf ON entry_tracking(symbol, timeframe);
CREATE INDEX idx_entry_state ON entry_tracking(state);

-- ============================================
-- TABLE 5: SETTINGS (Configuration)
-- ============================================
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_settings_key ON settings(setting_key);

-- ============================================
-- INSERT DEFAULT SETTINGS
-- ============================================
INSERT INTO settings (setting_key, setting_value, description) VALUES
('stocks', '["BTC/USDT", "ETH/USDT", "POL", "SNGP", "OGDC"]', 'List of stocks to track'),
('timeframes', '["15m", "1h", "1D"]', 'List of timeframes to analyze'),
('rsi_length', '14', 'RSI period'),
('rsi_ema_length', '21', 'RSI EMA period'),
('macd_fast', '9', 'MACD fast period'),
('macd_slow', '21', 'MACD slow period'),
('macd_signal', '5', 'MACD signal period'),
('bb_length', '20', 'Bollinger Bands period'),
('bb_mult_1', '1.0', 'BB first band multiplier'),
('bb_mult_2', '2.0', 'BB second band multiplier'),
('bb_mult_3', '3.0', 'BB third band multiplier'),
('intraday_max_score', '36', 'Maximum score for intraday timeframes'),
('swing_max_score', '41', 'Maximum score for swing timeframes');

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
SELECT 'Database schema created successfully!' AS status;