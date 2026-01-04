-- ============================================
-- CREATE SUPPORT_RESISTANCE TABLE
-- ============================================
-- Purpose: Store manual and auto-calculated support/resistance levels
-- Used for: Signal scoring bonus, dashboard display

CREATE TABLE IF NOT EXISTS support_resistance (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    
    -- Manual levels (user-entered, 0 = not set)
    manual_support DECIMAL(20, 8) DEFAULT 0,
    manual_resistance DECIMAL(20, 8) DEFAULT 0,
    
    -- Auto-calculated levels (previous month high/low)
    auto_support DECIMAL(20, 8),
    auto_resistance DECIMAL(20, 8),
    
    -- Effective levels (what's actually used based on settings)
    effective_support DECIMAL(20, 8),
    effective_resistance DECIMAL(20, 8),
    
    -- Metadata
    auto_sr_enabled BOOLEAN DEFAULT true,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(symbol, timeframe)
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_sr_symbol_tf ON support_resistance(symbol, timeframe);

-- Comments
COMMENT ON TABLE support_resistance IS 'Support and Resistance levels - manual and auto-calculated';
COMMENT ON COLUMN support_resistance.manual_support IS 'User-entered support level (0 = not set)';
COMMENT ON COLUMN support_resistance.manual_resistance IS 'User-entered resistance level (0 = not set)';
COMMENT ON COLUMN support_resistance.auto_support IS 'Auto-calculated from previous 30-day low';
COMMENT ON COLUMN support_resistance.auto_resistance IS 'Auto-calculated from previous 30-day high';
COMMENT ON COLUMN support_resistance.effective_support IS 'Final support level used (manual if set, else auto)';
COMMENT ON COLUMN support_resistance.effective_resistance IS 'Final resistance level used (manual if set, else auto)';

SELECT 'Support/Resistance table created successfully!' AS status;