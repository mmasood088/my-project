-- ============================================
-- ADD ATR COLUMN TO INDICATORS TABLE
-- ============================================

-- Add ATR (Average True Range - volatility measure)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS atr DECIMAL(20, 8);

-- Create index for ATR queries (optional but improves performance)
CREATE INDEX IF NOT EXISTS idx_indicators_atr 
ON indicators(atr);

-- Success message
SELECT 'ATR column added successfully!' AS status;