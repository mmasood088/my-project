-- ============================================
-- ADD SUPERTREND COLUMNS TO INDICATORS TABLE
-- ============================================

-- Add SuperTrend 1 (Faster - ATR 5, Factor 1.0)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS supertrend_1 DECIMAL(20, 8);

-- Add SuperTrend 2 (Slower - ATR 8, Factor 2.0)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS supertrend_2 DECIMAL(20, 8);

-- Create indexes for SuperTrend queries
CREATE INDEX IF NOT EXISTS idx_indicators_supertrend_1 
ON indicators(supertrend_1);

CREATE INDEX IF NOT EXISTS idx_indicators_supertrend_2 
ON indicators(supertrend_2);

-- Success message
SELECT 'SuperTrend columns added successfully!' AS status;