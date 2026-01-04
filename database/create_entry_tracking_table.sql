-- ============================================
-- CREATE ENTRY_TRACKING TABLE
-- ============================================
-- Purpose: Track BUY/A-BUY signal entries and exits
-- Matches TradingView Pine Script entry tracking logic

CREATE TABLE IF NOT EXISTS entry_tracking (
    id SERIAL PRIMARY KEY,
    
    -- Signal reference
    signal_id INTEGER REFERENCES signals(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    
    -- Entry details
    entry_signal VARCHAR(20) NOT NULL,  -- 'BUY' or 'A-BUY'
    entry_datetime TIMESTAMP NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    entry_score DECIMAL(5, 2) NOT NULL,
    
    -- Risk management
    stop_loss DECIMAL(20, 8) NOT NULL,
    target_price DECIMAL(20, 8) NOT NULL,
    atr_at_entry DECIMAL(20, 8),
    
    -- Entry validation
    validation_status VARCHAR(20) DEFAULT 'VALIDATING',  -- 'VALIDATING', 'VALID', 'INVALIDATED'
    validation_datetime TIMESTAMP,
    validation_candles_count INTEGER DEFAULT 0,
    max_validation_candles INTEGER DEFAULT 3,  -- Validate within 3 candles
    
    -- Exit tracking
    exit_status VARCHAR(20) DEFAULT 'ACTIVE',  -- 'ACTIVE', 'EXIT-1', 'EXIT-2', 'EXIT-3', 'STOP-LOSS', 'RECOVERY'
    exit_datetime TIMESTAMP,
    exit_price DECIMAL(20, 8),
    exit_reason VARCHAR(50),
    
    -- Performance tracking
    peak_price DECIMAL(20, 8),  -- Highest price reached
    peak_datetime TIMESTAMP,
    current_price DECIMAL(20, 8),  -- Latest price
    current_profit_pct DECIMAL(10, 4),  -- Current P&L %
    max_profit_pct DECIMAL(10, 4),  -- Peak P&L %
    final_profit_pct DECIMAL(10, 4),  -- Final P&L % at exit
    
    -- Exit stage tracking
    exit_1_hit BOOLEAN DEFAULT false,
    exit_1_datetime TIMESTAMP,
    exit_1_price DECIMAL(20, 8),
    
    exit_2_hit BOOLEAN DEFAULT false,
    exit_2_datetime TIMESTAMP,
    exit_2_price DECIMAL(20, 8),
    
    exit_3_hit BOOLEAN DEFAULT false,
    exit_3_datetime TIMESTAMP,
    exit_3_price DECIMAL(20, 8),
    
    -- Trailing stop
    trailing_stop_price DECIMAL(20, 8),
    trailing_stop_active BOOLEAN DEFAULT false,
    
    -- Recovery tracking
    recovery_attempt BOOLEAN DEFAULT false,
    recovery_low_price DECIMAL(20, 8),
    recovery_datetime TIMESTAMP,
    
    -- Metadata
    active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(signal_id)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_entry_tracking_symbol_tf ON entry_tracking(symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_entry_tracking_status ON entry_tracking(exit_status);
CREATE INDEX IF NOT EXISTS idx_entry_tracking_active ON entry_tracking(active);
CREATE INDEX IF NOT EXISTS idx_entry_tracking_validation ON entry_tracking(validation_status);
CREATE INDEX IF NOT EXISTS idx_entry_tracking_entry_datetime ON entry_tracking(entry_datetime DESC);

-- Comments
COMMENT ON TABLE entry_tracking IS 'Track BUY/A-BUY entries with validation and exit stages';
COMMENT ON COLUMN entry_tracking.validation_status IS 'VALIDATING: Awaiting confirmation, VALID: Confirmed entry, INVALIDATED: Signal failed';
COMMENT ON COLUMN entry_tracking.exit_status IS 'ACTIVE, EXIT-1, EXIT-2, EXIT-3, STOP-LOSS, RECOVERY';
COMMENT ON COLUMN entry_tracking.peak_price IS 'Highest price reached after entry (for trailing stops)';
COMMENT ON COLUMN entry_tracking.trailing_stop_price IS 'Dynamic trailing stop price (triggered after EXIT-1)';

SELECT 'Entry tracking table created successfully!' AS status;