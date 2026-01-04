-- ============================================
-- ALTER SIGNALS TABLE - ADD MISSING COLUMNS
-- ============================================

-- Add symbol and timeframe (needed for queries)
ALTER TABLE signals ADD COLUMN IF NOT EXISTS symbol VARCHAR(20);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS timeframe VARCHAR(10);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS datetime TIMESTAMP;

-- Add timeframe type classification
ALTER TABLE signals ADD COLUMN IF NOT EXISTS tf_type VARCHAR(10);

-- Add detailed score breakdown columns
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_total DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_rsi DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_macd DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_bb DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_ema_stack DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_supertrend DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_vwap DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_volume DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_adx DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_di DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_obv DECIMAL(5, 2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS score_price_action_bonus DECIMAL(5, 2);

-- Add price context columns
ALTER TABLE signals ADD COLUMN IF NOT EXISTS current_price DECIMAL(20, 8);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS support_level DECIMAL(20, 8);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS resistance_level DECIMAL(20, 8);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS magic_line_level DECIMAL(20, 8);

-- Rename 'target' to 'target_price' for consistency
ALTER TABLE signals RENAME COLUMN target TO target_price;

-- Create additional indexes
CREATE INDEX IF NOT EXISTS idx_signals_symbol_tf ON signals(symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_signals_datetime ON signals(datetime DESC);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_tf_datetime ON signals(symbol, timeframe, datetime DESC);

-- Update existing max_score column to match tf_type if needed
UPDATE signals 
SET tf_type = CASE 
    WHEN timeframe_type = 'Intraday' THEN 'Intraday'
    WHEN timeframe_type = 'Swing' THEN 'Swing'
    ELSE timeframe_type
END
WHERE tf_type IS NULL AND timeframe_type IS NOT NULL;

-- Comments
COMMENT ON COLUMN signals.tf_type IS 'Intraday (<=4H) or Swing (>4H)';
COMMENT ON COLUMN signals.score_total IS 'Total score used for signal classification';
COMMENT ON COLUMN signals.score_price_action_bonus IS 'Bonus from S/R breakout or Magic Line proximity';
COMMENT ON COLUMN signals.signal IS 'Signal: A-BUY, BUY, EARLY-BUY, WATCH, CAUTION, SELL';

SELECT 'Signals table altered successfully! Added ' || 
       (SELECT count(*) FROM information_schema.columns WHERE table_name = 'signals') || 
       ' total columns.' AS status;