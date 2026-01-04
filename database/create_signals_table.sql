-- ============================================
-- CREATE SIGNALS TABLE
-- ============================================
-- Purpose: Store generated trading signals with complete scoring breakdown
-- Used for: Signal history, backtesting, dashboard display

CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    candle_id INTEGER REFERENCES candles(id) UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    datetime TIMESTAMP NOT NULL,
    
    -- Timeframe classification
    tf_type VARCHAR(10),  -- 'Intraday' or 'Swing'
    max_score DECIMAL(5, 2),  -- 36.0 (Intraday) or 41.0 (Swing)
    
    -- Score components (for transparency and debugging)
    score_total DECIMAL(5, 2),
    score_rsi DECIMAL(5, 2),
    score_macd DECIMAL(5, 2),
    score_bb DECIMAL(5, 2),
    score_ema_stack DECIMAL(5, 2),
    score_supertrend DECIMAL(5, 2),
    score_vwap DECIMAL(5, 2),
    score_volume DECIMAL(5, 2),
    score_adx DECIMAL(5, 2),
    score_di DECIMAL(5, 2),
    score_obv DECIMAL(5, 2),
    score_price_action_bonus DECIMAL(5, 2),  -- Bonus from S/R + Magic Line
    
    -- Signal classification
    signal VARCHAR(20),  -- 'A-BUY', 'BUY', 'EARLY-BUY', 'WATCH', 'CAUTION', 'SELL'
    
    -- Entry levels (if BUY signal)
    entry_price DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    target_price DECIMAL(20, 8),
    
    -- Price context (for signal generation)
    current_price DECIMAL(20, 8),
    support_level DECIMAL(20, 8),
    resistance_level DECIMAL(20, 8),
    magic_line_level DECIMAL(20, 8),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_signals_symbol_tf ON signals(symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_signals_datetime ON signals(datetime DESC);
CREATE INDEX IF NOT EXISTS idx_signals_signal ON signals(signal);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_tf_datetime ON signals(symbol, timeframe, datetime DESC);

-- Comments
COMMENT ON TABLE signals IS 'Generated trading signals with complete scoring breakdown';
COMMENT ON COLUMN signals.tf_type IS 'Intraday (<=4H) or Swing (>4H)';
COMMENT ON COLUMN signals.score_total IS 'Total score used for signal classification';
COMMENT ON COLUMN signals.score_price_action_bonus IS 'Bonus from S/R breakout or Magic Line proximity';
COMMENT ON COLUMN signals.signal IS 'Signal: A-BUY, BUY, EARLY-BUY, WATCH, CAUTION, SELL';

SELECT 'Signals table created successfully!' AS status;